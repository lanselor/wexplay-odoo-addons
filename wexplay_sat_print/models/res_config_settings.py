from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wex_sat_print_enabled = fields.Boolean(
        string="Activar impresión SAT (Wexplay)",
        config_parameter="wexplay_sat_print.enabled",
        default=True,
    )

    wex_sat_default_printer = fields.Char(
        string="Impresora por defecto (QZ/Nombre)",
        config_parameter="wexplay_sat_print.default_printer",
        help="Nombre exacto de la impresora tal como la expone QZ Tray.",
    )

    wex_sat_print_debug = fields.Boolean(
        string="Modo debug de impresión",
        config_parameter="wexplay_sat_print.debug",
        default=False,
        help="Activa trazas adicionales en consola y logs del módulo.",
    )
