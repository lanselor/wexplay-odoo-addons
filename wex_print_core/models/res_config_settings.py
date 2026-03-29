from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wex_print_mode = fields.Selection(
        [
            ("legacy", "Legacy"),
            ("hybrid", "Hybrid"),
            ("new_only", "New Only"),
        ],
        string="Modo de resolución de impresión",
        config_parameter="wex_print_core.print_mode",
        default="legacy",
    )

    # Conservamos las claves actuales para no alterar configuración existente.
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

    # Campo técnico para montar el widget en ajustes.
    wex_qz_ui = fields.Char(string="QZ UI", readonly=True)
