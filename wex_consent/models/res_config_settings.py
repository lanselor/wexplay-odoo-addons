# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    x_wex_consent_dms_storage_id = fields.Many2one(
        related="company_id.x_wex_consent_dms_storage_id",
        readonly=False,
    )

    x_wex_consent_dms_root_directory_id = fields.Many2one(
        related="company_id.x_wex_consent_dms_root_directory_id",
        readonly=False,
    )

    x_wex_consent_reception_legal_text = fields.Text(
        string="Texto legal de recepción",
    )

    def get_values(self):
        res = super().get_values()
        res["x_wex_consent_reception_legal_text"] = (
            self.env["ir.config_parameter"].sudo().get_param(
                "wex_consent.reception_legal_text"
            )
            or ""
        )
        return res

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "wex_consent.reception_legal_text",
            self.x_wex_consent_reception_legal_text or "",
        )
