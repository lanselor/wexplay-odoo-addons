from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Config parameters (OK)
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
        default=False,
    )
    wex_qz_allow_fallback = fields.Boolean(
        string="Permitir fallback a impresora por defecto del sistema",
        config_parameter="wexplay_sat_print.wex_qz_allow_fallback",
        default=True,
    )

    # 🔥 ESTOS 3 FALTAN (aunque sean readonly deben existir si salen en la vista)
    # Lo lógico: vienen de company_id (no config_parameter)
    wex_qz_last_test_ok = fields.Boolean(
        related="company_id.wex_qz_last_test_ok",
        readonly=True,
    )
    wex_qz_last_test_at = fields.Datetime(
        related="company_id.wex_qz_last_test_at",
        readonly=True,
    )
    wex_qz_last_test_user_id = fields.Many2one(
        related="company_id.wex_qz_last_test_user_id",
        readonly=True,
    )

    # Campo dummy para el widget
    wex_qz_ui = fields.Char(string="QZ UI", readonly=True)
