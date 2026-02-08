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
