from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def write(self, values):
        result = super().write(values)
        if values.get("state") in ("cancel", "sale"):
            self._sync_portal_billing_cancellation()
        return result

    def _sync_portal_billing_cancellation(self):
        # El pedido ya pasó sus permisos nativos. Solo se actualiza seguimiento SAT.
        for order in self:
            repairs = self.env["repair.order"].sudo().search([
                ("sale_order_id", "=", order.id), ("company_id", "=", order.company_id.id),
                ("wex_portal_billing_tracked", "=", True),
            ])
            repairs.write({"wex_billing_cancelled_order": order.state == "cancel"})
