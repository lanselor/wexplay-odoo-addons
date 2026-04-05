# -*- coding: utf-8 -*-

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_repairs_to_refresh_warranty(self):
        sale_orders = self.invoice_line_ids.sale_line_ids.order_id.filtered(lambda so: so)
        if not sale_orders:
            return self.env["repair.order"]

        return self.env["repair.order"].search(
            [
                ("sale_order_id", "in", sale_orders.ids),
                ("x_is_warranty_case", "=", False),
            ]
        )

    def action_post(self):
        res = super().action_post()

        posted_customer_invoices = self.filtered(
            lambda move: move.state == "posted" and move.move_type == "out_invoice"
        )
        repairs = self.env["repair.order"]
        for invoice in posted_customer_invoices:
            repairs |= invoice._get_repairs_to_refresh_warranty()
        if repairs:
            repairs._refresh_warranty_snapshot()

        return res
