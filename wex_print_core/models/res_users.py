# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    wex_qz_label_printer = fields.Char(string="User label printer (QZ)")
    wex_qz_thermal_printer = fields.Char(string="User thermal printer (QZ)")
    wex_qz_a4_printer = fields.Char(string="User A4 printer (QZ)")

    @api.model
    def get_wex_qz_printer_overrides(self):
        user = self.env.user
        return {
            "label": user.wex_qz_label_printer or "",
            "thermal": user.wex_qz_thermal_printer or "",
            "a4": user.wex_qz_a4_printer or "",
        }
