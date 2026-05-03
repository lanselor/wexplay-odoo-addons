# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    x_wex_consent_reception_legal_text = fields.Text(
        string="Texto legal de recepción",
        compute="_compute_x_wex_consent_reception_legal_text",
        inverse="_inverse_x_wex_consent_reception_legal_text",
        help="Texto legal usado en los documentos de recepción firmados por clientes SAT.",
    )

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

    def _get_wex_consent_reception_legal_text_param_key(self):
        self.ensure_one()
        return "wex_consent.reception_legal_text.company_%s" % self.id

    @api.depends()
    def _compute_x_wex_consent_reception_legal_text(self):
        config = self.env["ir.config_parameter"].sudo()
        legacy_text = config.get_param("wex_consent.reception_legal_text") or ""
        for company in self:
            company.x_wex_consent_reception_legal_text = (
                config.get_param(company._get_wex_consent_reception_legal_text_param_key())
                or legacy_text
            )

    def _inverse_x_wex_consent_reception_legal_text(self):
        config = self.env["ir.config_parameter"].sudo()
        for company in self:
            config.set_param(
                company._get_wex_consent_reception_legal_text_param_key(),
                company.x_wex_consent_reception_legal_text or "",
            )
