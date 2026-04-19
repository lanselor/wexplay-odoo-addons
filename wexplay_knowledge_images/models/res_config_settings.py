# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    x_wex_knowledge_images_dms_storage_id = fields.Many2one(
        related="company_id.x_wex_knowledge_images_dms_storage_id",
        comodel_name="dms.storage",
        string="Almacenamiento DMS Knowledge",
        readonly=False,
    )

    x_wex_knowledge_images_dms_root_directory_id = fields.Many2one(
        related="company_id.x_wex_knowledge_images_dms_root_directory_id",
        comodel_name="dms.directory",
        string="Directorio raiz DMS Knowledge",
        readonly=False,
    )
