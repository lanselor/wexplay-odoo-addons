from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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