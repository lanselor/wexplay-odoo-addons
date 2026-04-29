# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    x_sat_budget_accepted_channel_id = fields.Many2one(
        comodel_name="discuss.channel",
        string="Canal SAT para presupuestos aceptados",
        config_parameter="wexplay_repair_delivery.sat_budget_accepted_channel_id",
    )
