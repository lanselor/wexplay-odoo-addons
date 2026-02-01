from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WexPurchaseListLine(models.Model):
    _name = "wex_purchase_list.line"
    _description = "Wexplay Purchase List Line"
    _order = "create_date desc, id desc"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    requested_by = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )

    product_id = fields.Many2one(
        "product.product",
        required=True,
        index=True,
        ondelete="restrict",
    )

    quantity = fields.Float(
        default=1.0,
        required=True,
    )

    vendor_id = fields.Many2one(
        "res.partner",
        domain=[("supplier_rank", ">", 0)],
        required=True,
        index=True,
    )

    vendor_url = fields.Char()

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

    @api.constrains("vendor_id")
    def _check_vendor_required(self):
        for rec in self:
            if not rec.vendor_id:
                raise ValidationError(_("El proveedor es obligatorio."))
