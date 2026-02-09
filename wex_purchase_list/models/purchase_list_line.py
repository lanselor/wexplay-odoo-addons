from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class WexPurchaseListLine(models.Model):
    _name = "wex_purchase_list.line"
    _description = "Wexplay Purchase List Line"
    _order = "create_date desc, id desc"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    requested_by = fields.Many2one(
        "res.users",
        string="Requested by",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        index=True,
        ondelete="restrict",
    )

    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        required=True,
    )

    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        domain=[("supplier_rank", ">", 0)],
        required=True,
        index=True,
    )

    vendor_url = fields.Char(
        string="Vendor URL"
    )

    customer_price_note = fields.Monetary(
        currency_field="currency_id",
        help="Precio informado al cliente (referencia).",
    )

    is_reservation = fields.Boolean()
    customer_notified = fields.Boolean()

    notes = fields.Text()

    state = fields.Selection(
        [
            ("draft_wait_customer", "Espera de Confirmación"),
            ("to_purchase", "Pendiente de compra"),
            ("ordered", "Pedido"),
            ("received", "Recibido"),
            ("cancelled", "Cancelado"),
        ],
        default="draft_wait_customer",
        required=True,
        index=True,
    )

    purchase_order_id = fields.Many2one(
        "purchase.order",
        readonly=True,
        copy=False,
        index=True,
    )

    purchase_order_line_id = fields.Many2one(
        "purchase.order.line",
        readonly=True,
        copy=False,
        index=True,
    )

    # ORÍGENES
    repair_id = fields.Many2one(
        "repair.order",
        ondelete="set null",
        index=True,
    )

    repair_part_move_id = fields.Many2one(
        "stock.move",
        ondelete="set null",
        index=True,
    )

    sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Línea de venta",
        ondelete="set null",
        index=True,
    )

    @api.onchange("product_id")
    def _onchange_product_id_autofill_vendor(self):
        """
        Al crear/editar líneas manualmente desde la lista:
        - Autocompleta proveedor (primer seller válido) si no está puesto
        - Autocompleta URL desde el producto si existe y no está puesta
        """
        for rec in self:
            if not rec.product_id:
                continue

            # URL desde producto (plantilla). Requiere campo wex_vendor_url en product.template.
            tmpl = rec.product_id.product_tmpl_id
            if tmpl and getattr(tmpl, "wex_vendor_url", False) and not rec.vendor_url:
                rec.vendor_url = tmpl.wex_vendor_url

            # proveedor: primer seller válido
            if not rec.vendor_id:
                sellers = rec.product_id.seller_ids
                if sellers:
                    vendor = sellers[0].partner_id
                    if vendor and vendor.supplier_rank > 0:
                        rec.vendor_id = vendor

    # ------------------------------------------------------------
    # Centralized creation logic (single source of truth)
    # ------------------------------------------------------------
    @api.model
    def add_from_origin(
        self,
        *,
        origin_model: str,
        origin_id: int,
        product_id: int,
        qty: float,
        state: str = "to_purchase",
    ):
        """
        Centraliza la creación/merge de líneas en wex_purchase_list.line.
        - origin_model/origin_id identifican el origen (sale.order.line, stock.move, etc.)
        - product_id/qty: producto y cantidad solicitada
        - state: estado inicial (por defecto to_purchase)
        Devuelve: dict {line, mode, message}
        """

        if not product_id:
            raise UserError(_("No se puede añadir a la lista de compra: falta Producto."))
        if not qty or qty <= 0:
            raise UserError(_("No se puede añadir a la lista de compra: la Cantidad debe ser mayor que cero."))

        product = self.env["product.product"].browse(product_id).exists()
        if not product:
            raise UserError(_("No se puede añadir a la lista de compra: el producto no existe."))

        # Seguridad lógica: no servicios (coherente con tu botón de venta)
        if product.type == "service":
            raise UserError(_("No se pueden añadir servicios a la lista de compra."))

        # Vendor: primer seller válido (como confirmaste)
        sellers = product.seller_ids
        if not sellers:
            raise UserError(_("El producto no tiene proveedores configurados."))

        vendor = sellers[0].partner_id
        if not vendor or vendor.supplier_rank <= 0:
            raise UserError(_("El proveedor no es válido."))

        # URL desde producto (plantilla), si existe el campo
        tmpl = product.product_tmpl_id
        vendor_url = getattr(tmpl, "wex_vendor_url", False) if tmpl else False

        # Resolver origen
        origin = self.env[origin_model].browse(origin_id).exists()
        if not origin:
            raise UserError(_("No se ha podido determinar el origen para añadir a la lista de compra."))

        # ------------------------------------------------------------
        # Origen: sale.order.line (no merge, si existe => error)
        # ------------------------------------------------------------
        if origin_model == "sale.order.line":
            sale_line = origin

            # Idempotencia: si ya está vinculada, error (regla confirmada)
            if sale_line.purchase_list_line_id:
                raise UserError(_("Esta línea ya está en la lista de compra."))

            # compañía desde el pedido
            order = sale_line.order_id
            company = order.company_id or self.env.company

            vals = {
                "company_id": company.id,
                "requested_by": self.env.user.id,
                "product_id": product.id,
                "quantity": qty,
                "vendor_id": vendor.id,
                "vendor_url": vendor_url or False,
                "state": state,
                "sale_line_id": sale_line.id,
            }

            line = self.create(vals)
            sale_line.purchase_list_line_id = line.id

            return {
                "line": line,
                "mode": "created",
                "message": _("Producto añadido a la lista de compra."),
            }

        # ------------------------------------------------------------
        # Origen: stock.move (merge por repair_id + product_id si activa)
        # ------------------------------------------------------------
        if origin_model == "stock.move":
            move = origin

            # Evitar doble click que sume qty por accidente.
            # Si ya está vinculada a una línea activa, error.
            if move.purchase_list_line_id and move.purchase_list_line_id.state not in ("cancelled", "received"):
                raise UserError(_("Esta pieza ya está en la lista de compra."))

            repair = move.repair_id
            if not repair:
                raise UserError(_("No se ha podido determinar la reparación asociada."))

            company = repair.company_id or self.env.company

            # Buscar línea existente activa (merge key confirmada)
            existing_line = self.search(
                [
                    ("repair_id", "=", repair.id),
                    ("product_id", "=", product.id),
                    ("state", "not in", ("cancelled", "received")),
                ],
                limit=1,
            )

            if existing_line:
                existing_line.quantity += qty

                # Completar URL si faltaba
                if vendor_url and not existing_line.vendor_url:
                    existing_line.vendor_url = vendor_url

                move.purchase_list_line_id = existing_line.id

                return {
                    "line": existing_line,
                    "mode": "merged",
                    "message": _("La cantidad se ha sumado a una línea existente de la lista de compra."),
                }

            vals = {
                "company_id": company.id,
                "requested_by": self.env.user.id,
                "product_id": product.id,
                "quantity": qty,
                "vendor_id": vendor.id,
                "vendor_url": vendor_url or False,
                "state": state,
                "repair_id": repair.id,
                "repair_part_move_id": move.id,
            }

            line = self.create(vals)
            move.purchase_list_line_id = line.id

            return {
                "line": line,
                "mode": "created",
                "message": _("Producto añadido a la lista de la compra correctamente."),
            }
        # ------------------------------------------------------------
        # Origen: product.template (crear línea directa con qty por defecto)
        # ------------------------------------------------------------
        if origin_model == "product.template":
            tmpl_rec = origin  # product.template

            # Elegir variante: si hay varias, no podemos adivinar
            variants = tmpl_rec.product_variant_ids
            if not variants:
                raise UserError(_("La plantilla no tiene variantes de producto."))
            if len(variants) != 1:
                raise UserError(_(
                    "Este producto tiene varias variantes. "
                    "Abre una variante concreta y añádela desde ahí."
                ))

            variant = variants[0]

            # Idempotencia simple: no hay campo purchase_list_line_id en product.template,
            # así que siempre crea una nueva línea (comportamiento esperado para compra interna).
            company = self.env.company

            vals = {
                "company_id": company.id,
                "requested_by": self.env.user.id,
                "product_id": variant.id,
                "quantity": qty,
                "vendor_id": vendor.id,
                "vendor_url": vendor_url or False,
                "state": state,
            }
            line = self.create(vals)

            return {
                "line": line,
                "mode": "created",
                "message": _("Producto añadido a la lista de compra."),
            }
        # ------------------------------------------------------------
        # Otros orígenes (futuro)
        # ------------------------------------------------------------
        raise UserError(_("Origen no soportado: %s") % origin_model)
    
    def action_create_rfqs(self):
        """
        Crea RFQ(s) agrupadas por proveedor (y compañía) a partir de líneas 'to_purchase'.
        - Requiere vendor_id (required=True)
        - Solo procesa líneas en estado 'to_purchase'
        - Evita duplicados: si ya tiene purchase_order_line_id, no lo procesa
        """
        lines = self
        if not lines:
            raise UserError(_("No hay líneas seleccionadas."))

        not_ready = lines.filtered(lambda l: l.state != "to_purchase")
        if not_ready:
            raise UserError(_("Solo se pueden crear RFQ desde líneas en estado 'Pendiente de compra'."))

        already_linked = lines.filtered(lambda l: l.purchase_order_line_id)
        if already_linked:
            raise UserError(_(
                "Hay líneas ya vinculadas a una RFQ/PO. "
                "Quita esas líneas de la selección o duplica la línea si necesitas pedir de nuevo."
            ))

        missing_vendor = lines.filtered(lambda l: not l.vendor_id)
        if missing_vendor:
            raise UserError(_("El proveedor es obligatorio en todas las líneas."))

        # Agrupar por (company_id, vendor_id)
        groups = {}
        for line in lines:
            company = line.company_id or self.env.company
            key = (company.id, line.vendor_id.id)
            groups.setdefault(key, self.env["wex_purchase_list.line"])
            groups[key] |= line

        created_orders = self.env["purchase.order"]
        now = fields.Datetime.now()

        for (company_id, vendor_id), group_lines in groups.items():
            company = self.env["res.company"].browse(company_id)
            vendor = self.env["res.partner"].browse(vendor_id)

            po_vals = {
                "partner_id": vendor.id,
                "company_id": company.id,
                "origin": _("Wexplay - Lista de compra"),
            }
            po = self.env["purchase.order"].with_company(company).create(po_vals)

            pol_model = self.env["purchase.order.line"].with_company(company)

            for line in group_lines:
                # Multi-company safe: leer costes y UoM en contexto de compañía
                product = line.product_id.with_company(company)
                uom = product.uom_po_id or product.uom_id

                # ✅ Precio por defecto: coste del producto
                price_unit = product.standard_price or 0.0

                pol_vals = {
                    "order_id": po.id,
                    "product_id": product.id,
                    "name": product.display_name,
                    "product_qty": line.quantity or 1.0,
                    "product_uom": uom.id,
                    "price_unit": price_unit,
                    "date_planned": now,
                }
                pol = pol_model.create(pol_vals)
                if price_unit:
                    pol.write({"price_unit": price_unit})

                line.write({
                    "purchase_order_id": po.id,
                    "purchase_order_line_id": pol.id,
                    "state": "ordered",
                })

            created_orders |= po

        action = self.env.ref("purchase.purchase_rfq").read()[0]
        action["domain"] = [("id", "in", created_orders.ids)]
        action["context"] = {"create": False}
        return action

    @api.constrains("vendor_id")
    def _check_vendor_required(self):
        for rec in self:
            if not rec.vendor_id:
                raise ValidationError(_("El proveedor es obligatorio."))
