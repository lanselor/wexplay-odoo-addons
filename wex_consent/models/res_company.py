# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    x_wex_consent_dms_storage_id = fields.Many2one(
        comodel_name="dms.storage",
        string="Almacenamiento DMS de consentimientos",
        domain="[('save_type', '!=', 'attachment')]",
        help="Almacenamiento DMS donde se crearán los documentos firmados SAT.",
    )

    x_wex_consent_dms_root_directory_id = fields.Many2one(
        comodel_name="dms.directory",
        string="Directorio raíz DMS de consentimientos",
        domain="[('is_root_directory', '=', True)]",
        help="Directorio raíz DMS para SAT. Si no existe se podrá crear automáticamente.",
    )
