# Copyright 2026 Wexplay
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        session = super().session_info()
        user = self.env.user
        apps_menu = dict(session.get("apps_menu", {}))
        background_url = False
        if user.apps_menu_background_image:
            background_url = (
                f"/web/image/res.users/{user.id}/apps_menu_background_image"
                f"?unique={user.write_date}"
            )
        apps_menu.update(
            {
                "custom_order": user.apps_menu_custom_order or [],
                "background_url": background_url,
            }
        )
        session["apps_menu"] = apps_menu
        return session
