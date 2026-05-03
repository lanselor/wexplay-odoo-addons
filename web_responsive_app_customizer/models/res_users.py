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
    apps_menu_background_preset = fields.Selection(
        [
            ("custom", "Uploaded Image"),
            ("wexplay_circuit", "Wexplay Circuit"),
            ("wexplay_flow", "Wexplay Flow"),
            ("wexplay_architecture", "Wexplay Architecture"),
        ],
        string="Apps Menu Background Preset",
        default="custom",
        required=True,
    )
    apps_menu_favorite_keys = fields.Json(
        string="Favorite Apps",
        default=list,
    )
    apps_menu_hidden_keys = fields.Json(
        string="Hidden Apps",
        default=list,
    )
    apps_menu_icon_size = fields.Selection(
        [
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ],
        string="Apps Menu Icon Size",
        default="medium",
        required=True,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "apps_menu_custom_order",
            "apps_menu_background_image",
            "apps_menu_background_preset",
            "apps_menu_favorite_keys",
            "apps_menu_hidden_keys",
            "apps_menu_icon_size",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            "apps_menu_custom_order",
            "apps_menu_background_image",
            "apps_menu_background_preset",
            "apps_menu_favorite_keys",
            "apps_menu_hidden_keys",
            "apps_menu_icon_size",
        ]

    def action_reset_apps_menu_order(self):
        self.write({"apps_menu_custom_order": []})

    def action_reset_apps_menu_background(self):
        self.write(
            {
                "apps_menu_background_image": False,
                "apps_menu_background_preset": "custom",
            }
        )

    def action_reset_apps_menu_favorites(self):
        self.write({"apps_menu_favorite_keys": []})

    def action_reset_apps_menu_hidden(self):
        self.write({"apps_menu_hidden_keys": []})
