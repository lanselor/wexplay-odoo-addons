# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    x_portal_shipping_notifications_enabled = fields.Boolean(
        related="company_id.x_portal_shipping_notifications_enabled",
        readonly=False,
    )
