# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    wex_qz_label_device_id = fields.Many2one("wex.print.device", string="Dispositivo etiquetas (usuario)")
    wex_qz_thermal_device_id = fields.Many2one("wex.print.device", string="Dispositivo térmico (usuario)")
    wex_qz_a4_device_id = fields.Many2one("wex.print.device", string="Dispositivo A4 (usuario)")

    wex_qz_label_printer = fields.Char(string="Impresora etiquetas (usuario)")
    wex_qz_thermal_printer = fields.Char(string="Impresora térmica (usuario)")
    wex_qz_a4_printer = fields.Char(string="Impresora A4 (usuario)")

    @api.model
    def get_wex_qz_printer_overrides(self):
        user = self.env.user
        return {
            "label": {
                "device_id": user.wex_qz_label_device_id.id or False,
                "printer_name": user.wex_qz_label_device_id.qz_printer_name or user.wex_qz_label_printer or "",
            },
            "thermal": {
                "device_id": user.wex_qz_thermal_device_id.id or False,
                "printer_name": user.wex_qz_thermal_device_id.qz_printer_name or user.wex_qz_thermal_printer or "",
            },
            "a4": {
                "device_id": user.wex_qz_a4_device_id.id or False,
                "printer_name": user.wex_qz_a4_device_id.qz_printer_name or user.wex_qz_a4_printer or "",
            },
        }

    @api.model
    def get_wex_qz_company_printer_defaults(self):
        company = self.env.company
        return {
            "label": {
                "device_id": company.wex_qz_label_device_id.id or False,
                "printer_name": company.wex_qz_label_device_id.qz_printer_name or company.wex_qz_label_printer or "",
            },
            "thermal": {
                "device_id": company.wex_qz_thermal_device_id.id or False,
                "printer_name": company.wex_qz_thermal_device_id.qz_printer_name or company.wex_qz_thermal_printer or "",
            },
            "a4": {
                "device_id": company.wex_qz_a4_device_id.id or False,
                "printer_name": company.wex_qz_a4_device_id.qz_printer_name or company.wex_qz_a4_printer or "",
            },
        }
