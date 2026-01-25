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
    vendor_url = fields.Char(string="Vendor URL")

    customer_price_note = fields.Monetary(
        string="Customer price (note)",
        currency_field="currency_id",
        help="Precio informado al cliente (referencia), no es el coste de compra.",
    )

    is_reservation = fields.Boolean(string="Reservation")
    customer_notified = fields.Boolean(string="Customer notified")

    notes = fields.Text(string="Notes")

    state = fields.Selection(
        selection=[
            ("draft_wait_customer", "Espera de Confirmación"),
            ("to_purchase", "Pendiente de compra"),
            ("ordered", "Pedido"),
            ("received", "Recibido"),
            ("cancelled", "Cancelado"),
        ],
        string="State",
        default="draft_wait_customer",
        required=True,
        index=True,
    )
    
    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="RFQ/PO",
        readonly=True,
        copy=False,
        index=True,
    )
    purchase_order_line_id = fields.Many2one(
        "purchase.order.line",
        string="Línea RFQ/PO",
        readonly=True,
        copy=False,
        index=True,
    )

    def action_create_rfqs(self):
        """Crea RFQ(s) agrupadas por proveedor (y compañía) a partir de líneas to_purchase.
        - Requiere vendor_id (ya obligatorio en tu fase 1.5)
        - Solo procesa líneas en estado to_purchase
        - Evita duplicados: si ya tiene purchase_order_line_id, no lo procesa
        """
        #self.ensure_one() if isinstance(self.id, int) else None  # no-op, permite multi

        lines = self
        if not lines:
            raise UserError(_("No hay líneas seleccionadas."))

        # Validaciones
        not_ready = lines.filtered(lambda l: l.state != "to_purchase")
        if not_ready:
            raise UserError(_(
                "Solo se pueden crear RFQ desde líneas en estado 'Pendiente de compra'."
            ))

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

        for (company_id, vendor_id), group_lines in groups.items():
            company = self.env["res.company"].browse(company_id)
            vendor = self.env["res.partner"].browse(vendor_id)

            # Crear RFQ (purchase.order)
            po_vals = {
                "partner_id": vendor.id,
                "company_id": company.id,
                "origin": _("Wexplay - Lista de compra"),
            }
            po = self.env["purchase.order"].with_company(company).create(po_vals)

            # Crear líneas RFQ
            now = fields.Datetime.now()
            pol_model = self.env["purchase.order.line"].with_company(company)

            for line in group_lines:
                product = line.product_id
                uom = product.uom_po_id or product.uom_id

                pol_vals = {
                    "order_id": po.id,
                    "product_id": product.id,
                    "name": product.display_name,
                    "product_qty": line.quantity or 1.0,
                    "product_uom": uom.id,
                    "price_unit": 0.0,          # mínimo estable: el comprador rellena
                    "date_planned": now,        # requerido
                }
                pol = pol_model.create(pol_vals)

                # Vincular y marcar estado
                line.write({
                    "purchase_order_id": po.id,
                    "purchase_order_line_id": pol.id,
                    "state": "ordered",
                })

            created_orders |= po

        # Devolver acción para abrir las RFQ creadas
        action = self.env.ref("purchase.purchase_rfq").read()[0]
        action["domain"] = [("id", "in", created_orders.ids)]
        action["context"] = {"create": False}
        return action

    @api.onchange("is_reservation")
    def _onchange_is_reservation(self):
        # Mantenerlo simple en fase 1: si deja de ser reserva, desmarcamos avisado.
        # (El usuario puede volver a marcarlo manualmente si lo desea.)
        for rec in self:
            if not rec.is_reservation:
                rec.customer_notified = False

    @api.constrains("vendor_id")
    def _check_vendor_required(self):
        for rec in self:
            if not rec.vendor_id:
                raise ValidationError(_("El proveedor es obligatorio."))