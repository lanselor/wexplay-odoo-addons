# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    x_sat_image_compress_enabled = fields.Boolean(
        string="Comprimir imágenes SAT",
        default=True,
        help="Redimensiona y comprime las imágenes al subirlas al expediente SAT.",
    )
    x_sat_image_max_px = fields.Integer(
        string="Resolución máxima (px)",
        default=1920,
        help="Lado más largo al que se redimensionará la imagen. "
             "Las imágenes más pequeñas no se amplían.",
    )
    x_sat_image_quality = fields.Integer(
        string="Calidad JPEG/WebP",
        default=85,
        help="Calidad de recompresión para JPEG y WebP (1-95). "
             "85 es un equilibrio óptimo entre tamaño y calidad visual.",
    )
