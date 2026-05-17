# Copyright 2026 Wexplay
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    apps_menu_patch_note_date = fields.Datetime(
        string="Fecha de la ultima actualizacion",
        config_parameter="web_responsive_app_customizer.patch_note_date",
    )
    apps_menu_patch_note_text = fields.Html(
        string="Notas de actualizacion",
        sanitize=True,
    )

    def get_values(self):
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()
        res.update(
            apps_menu_patch_note_text=params.get_param(
                "web_responsive_app_customizer.patch_note_text", ""
            )
        )
        return res

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "web_responsive_app_customizer.patch_note_text",
            self.apps_menu_patch_note_text or "",
        )
