from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    purchase_list_line_count = fields.Integer(
        string="Líneas de compra",
        compute="_compute_purchase_list_line_count",
    )

    def _compute_purchase_list_line_count(self):
        Line = self.env["wex_purchase_list.line"]
        for order in self:
            order.purchase_list_line_count = Line.search_count([
                ("sale_line_id.order_id", "=", order.id),
            ])

    def action_view_purchase_list_lines(self):
        self.ensure_one()
        action = self.env.ref("wex_purchase_list.action_wex_purchase_list_line").read()[0]
        action["domain"] = [("sale_line_id.order_id", "=", self.id)]
        return action


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Campo estable para attrs en tree (store=True)
    # Valores: 'product', 'consu', 'service'
    wex_product_type = fields.Selection(
        related="product_id.type",
        store=True,
        readonly=True,
    )

    purchase_list_line_id = fields.Many2one(
        "wex_purchase_list.line",
        string="Línea lista de compra",
        readonly=True,
        copy=False,
        index=True,
    )

    def action_add_to_purchase_list(self):
        self.ensure_one()

        result = self.env["wex_purchase_list.line"].add_from_origin(
            origin_model="sale.order.line",
            origin_id=self.id,
            product_id=self.product_id.id,
            qty=self.product_uom_qty or 0.0,
            state="to_purchase",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OK"),
                "message": result.get("message") or _("Operación completada."),
                "type": "success",
                "sticky": False,
            }
        }

