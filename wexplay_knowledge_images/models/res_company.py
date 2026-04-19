# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    x_wex_knowledge_images_dms_storage_id = fields.Many2one(
        comodel_name="dms.storage",
        string="Almacenamiento DMS Knowledge",
        domain="[('save_type', '!=', 'attachment')]",
        help="Almacenamiento DMS usado para imagenes embebidas de knowledge.",
    )

    x_wex_knowledge_images_dms_root_directory_id = fields.Many2one(
        comodel_name="dms.directory",
        string="Directorio raiz DMS Knowledge",
        domain="[('is_root_directory', '=', True)]",
        help="Directorio raiz DMS para los recursos embebidos de knowledge.",
    )
