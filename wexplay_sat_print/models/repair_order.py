# -*- coding: utf-8 -*-
from odoo import models


class RepairOrder(models.Model):
    _inherit = "repair.order"

    def action_wex_open_print_center(self):
        """Open SAT Print Center modal (JS client action)."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "wexplay_sat_print.open_print_center",
            "params": {
                "resModel": self._name,
                "resId": self.id,
            },
        }