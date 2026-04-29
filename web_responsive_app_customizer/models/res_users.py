# Copyright 2026 Wexplay
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    apps_menu_custom_order = fields.Json(
        string="Apps Menu Custom Order",
        default=list,
    )
    apps_menu_background_image = fields.Image(
        string="Apps Menu Background",
        max_width=2560,
        max_height=2560,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "apps_menu_custom_order",
            "apps_menu_background_image",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            "apps_menu_custom_order",
            "apps_menu_background_image",
        ]

    def action_reset_apps_menu_order(self):
        self.write({"apps_menu_custom_order": []})

    def action_reset_apps_menu_background(self):
        self.write({"apps_menu_background_image": False})
