class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Cambia config_parameter por related para apuntar a res.company
    wex_qz_label_printer = fields.Char(related="company_id.wex_qz_label_printer", readonly=False)
    wex_qz_thermal_printer = fields.Char(related="company_id.wex_qz_thermal_printer", readonly=False)
    wex_qz_a4_printer = fields.Char(related="company_id.wex_qz_a4_printer", readonly=False)
    wex_qz_debug = fields.Boolean(related="company_id.wex_qz_debug", readonly=False)
    wex_qz_allow_fallback = fields.Boolean(related="company_id.wex_qz_allow_fallback", readonly=False)
    
    # Estos campos de diagnóstico también deben ser related para mostrar los datos de la empresa
    wex_qz_last_test_ok = fields.Boolean(related="company_id.wex_qz_last_test_ok", readonly=True)
    wex_qz_last_test_at = fields.Datetime(related="company_id.wex_qz_last_test_at", readonly=True)
    wex_qz_last_test_user_id = fields.Many2one(related="company_id.wex_qz_last_test_user_id", readonly=True)

    wex_qz_ui = fields.Char(string="QZ UI", readonly=True)