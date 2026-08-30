# -*- coding: utf-8 -*-

from odoo import fields, models

from .repair_order import PORTAL_BUDGET_DEBUG_PARAMETER


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    x_portal_budget_debug_enabled = fields.Boolean(
        string="Registrar diagnóstico técnico de presupuestos portal",
        config_parameter=PORTAL_BUDGET_DEBUG_PARAMETER,
    )
