# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    wex_qz_label_device_id = fields.Many2one("wex.print.device", string="Label device (QZ)")
    wex_qz_thermal_device_id = fields.Many2one("wex.print.device", string="Thermal device (QZ)")
    wex_qz_a4_device_id = fields.Many2one("wex.print.device", string="A4 device (QZ)")

    wex_qz_label_printer = fields.Char(string="Impresora etiquetas (QZ)")
    wex_qz_thermal_printer = fields.Char(string="Impresora térmica (QZ)")
    wex_qz_a4_printer = fields.Char(string="Impresora A4 (QZ)")

    wex_qz_debug = fields.Boolean(string="Debug QZ", default=False)
    wex_qz_allow_fallback = fields.Boolean(
        string="Permitir fallback a impresora por defecto del sistema",
        default=True,
    )

    wex_qz_last_test_ok = fields.Boolean(string="Último test QZ OK", default=False)
    wex_qz_last_test_at = fields.Datetime(string="Último test QZ (fecha)")
    wex_qz_last_test_user_id = fields.Many2one("res.users", string="Último test QZ (usuario)")
