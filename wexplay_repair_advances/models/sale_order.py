from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    wex_advance_notice = fields.Char(compute="_compute_advance_notice", groups="account.group_account_invoice")
    wex_advance_notice_detail = fields.Text(compute="_compute_advance_notice", groups="account.group_account_invoice")

    @api.depends("state", "partner_id", "company_id", "repair_order_ids.wex_advance_notice",
                 "repair_order_ids.wex_advance_notice_detail")
    @api.depends_context("lang")
    def _compute_advance_notice(self):
        for order in self:
            repairs = order.repair_order_ids.filtered(
                lambda r: r.company_id == order.company_id
                and r.partner_id.commercial_partner_id == order.partner_id.commercial_partner_id
            ) if order.state != "cancel" else self.env["repair.order"]
            order.wex_advance_notice, order.wex_advance_notice_detail = repairs._get_advance_notice_values()
