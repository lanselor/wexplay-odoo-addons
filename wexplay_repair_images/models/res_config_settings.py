# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    x_sat_image_compress_enabled = fields.Boolean(
        related="company_id.x_sat_image_compress_enabled",
        string="Comprimir imágenes SAT",
        readonly=False,
    )
    x_sat_image_max_px = fields.Integer(
        related="company_id.x_sat_image_max_px",
        string="Resolución máxima (px)",
        readonly=False,
    )
    x_sat_image_quality = fields.Integer(
        related="company_id.x_sat_image_quality",
        string="Calidad JPEG/WebP",
        readonly=False,
    )
