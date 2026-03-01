# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    has_sat_related = fields.Boolean(
        compute="_compute_has_sat_related",
        store=False,
    )

    @api.depends("invoice_line_ids.sale_line_ids.order_id")
    def _compute_has_sat_related(self):
        Repair = self.env["repair.order"]
        for move in self:
            sale_orders = move.invoice_line_ids.sale_line_ids.order_id
            sale_orders = sale_orders.filtered(lambda so: so)
            if not sale_orders:
                move.has_sat_related = False
                continue
            # Ajusta este dominio si tu enlace no es sale_order_id
            move.has_sat_related = bool(Repair.search_count([("sale_order_id", "in", sale_orders.ids)]))

    def action_print_sat_pdf(self):
        self.ensure_one()
        return self.env.ref("wexplay_repair.action_report_invoice_sat").report_action(self)