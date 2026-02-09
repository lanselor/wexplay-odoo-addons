from odoo import _, fields, models
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    purchase_list_line_count = fields.Integer(
        string="Líneas de compra",
        compute="_compute_purchase_list_line_count",
    )

    def _compute_purchase_list_line_count(self):
        line_model = self.env["wex_purchase_list.line"]
        for rec in self:
            rec.purchase_list_line_count = line_model.search_count([
                ("repair_id", "=", rec.id)
            ])

    def action_view_purchase_list_lines(self):
        self.ensure_one()
        action = self.env.ref(
            "wex_purchase_list.action_wex_purchase_list_line"
        ).read()[0]
        action["domain"] = [("repair_id", "=", self.id)]
        action["context"] = {"default_repair_id": self.id}
        return action


class StockMove(models.Model):
    _inherit = "stock.move"

    purchase_list_line_id = fields.Many2one(
        "wex_purchase_list.line",
        string="Línea lista de compra",
        readonly=True,
        copy=False,
        index=True,
        help="Si se creó una línea de lista de compra desde esta pieza, queda vinculada aquí.",
    )

    def action_add_to_purchase_list(self):
        self.ensure_one()

        result = self.env["wex_purchase_list.line"].add_from_origin(
            origin_model="stock.move",
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
