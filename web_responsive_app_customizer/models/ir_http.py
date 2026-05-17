# Copyright 2026 Wexplay
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import fields, models


BACKGROUND_PRESET_URLS = {
    "wexplay_circuit": "/web_responsive_app_customizer/static/src/img/backgrounds/wexplay-circuit.png",
    "wexplay_flow": "/web_responsive_app_customizer/static/src/img/backgrounds/wexplay-flow.png",
    "wexplay_architecture": "/web_responsive_app_customizer/static/src/img/backgrounds/wexplay-architecture.png",
}


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        session = super().session_info()
        user = self.env.user
        apps_menu = dict(session.get("apps_menu", {}))
        background_url = False
        if user.apps_menu_background_preset == "custom" and user.apps_menu_background_image:
            background_url = (
                f"/web/image/res.users/{user.id}/apps_menu_background_image"
                f"?unique={user.write_date}"
            )
        elif user.apps_menu_background_preset in BACKGROUND_PRESET_URLS:
            background_url = BACKGROUND_PRESET_URLS[user.apps_menu_background_preset]
        patch_note = self._get_apps_menu_patch_note()
        apps_menu.update(
            {
                "custom_order": user.apps_menu_custom_order or [],
                "background_preset": user.apps_menu_background_preset,
                "favorite_keys": user.apps_menu_favorite_keys or [],
                "hidden_keys": user.apps_menu_hidden_keys or [],
                "icon_size": user.apps_menu_icon_size or "medium",
                "background_url": background_url,
                "patch_note": patch_note,
            }
        )
        session["apps_menu"] = apps_menu
        return session

    def _get_apps_menu_patch_note(self):
        params = self.env["ir.config_parameter"].sudo()
        note_text = params.get_param("web_responsive_app_customizer.patch_note_text")
        note_date_string = params.get_param("web_responsive_app_customizer.patch_note_date")
        note_text = note_text.strip() if note_text else ""
        if not note_text or not note_date_string:
            return False
        note_datetime = fields.Datetime.to_datetime(note_date_string)
        note_date = note_datetime.date() if note_datetime else False
        today = fields.Date.context_today(self.env.user)
        if not note_date or note_date > today or today > note_date + timedelta(days=1):
            return False
        return {
            "date": fields.Date.to_string(note_date),
            "html": note_text,
        }
