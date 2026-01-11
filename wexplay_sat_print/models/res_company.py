# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Campos "puente" como config_parameter para NO depender de columnas mientras arreglas el upgrade.
    # (Luego los podemos volver a related si quieres.)
    wex_qz_label_printer = fields.Char(
        string="Impresora etiquetas (QZ)",
        config_parameter="wexplay_sat_print.wex_qz_label_printer",
    )
    wex_qz_thermal_printer = fields.Char(
        string="Impresora térmica (QZ)",
        config_parameter="wexplay_sat_print.wex_qz_thermal_printer",
    )
    wex_qz_a4_printer = fields.Char(
        string="Impresora A4 (QZ)",
        config_parameter="wexplay_sat_print.wex_qz_a4_printer",
    )

    wex_qz_debug = fields.Boolean(
        string="Debug QZ",
        config_parameter="wexplay_sat_print.wex_qz_debug",
    )
    wex_qz_allow_fallback = fields.Boolean(
        string="Permitir fallback a impresora por defecto del sistema",
        config_parameter="wexplay_sat_print.wex_qz_allow_fallback",
        default=True,
    )

    # Estado diagnóstico (se mantiene no persistente aquí; lo guardaremos luego en company cuando DB esté bien)
    wex_qz_last_test_ok = fields.Boolean(string="Último test QZ OK", readonly=True)
    wex_qz_last_test_at = fields.Datetime(string="Último test QZ (fecha)", readonly=True)
    wex_qz_last_test_user_id = fields.Many2one("res.users", string="Último test QZ (usuario)", readonly=True)

    # Campo “dummy” para enganchar el widget
    wex_qz_ui = fields.Char(string="QZ UI", readonly=True)
