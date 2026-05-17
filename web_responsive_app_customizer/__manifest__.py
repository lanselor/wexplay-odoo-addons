# Copyright 2026 Wexplay
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Web Responsive App Customizer",
    "summary": "Let users reorder the apps menu and choose a personal background",
    "version": "18.0.1.0.0",
    "category": "web",
    "website": "https://github.com/OCA/web",
    "author": "Wexplay, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["base_setup", "web_responsive"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/web_responsive_app_customizer/static/lib/sortable/Sortable.min.js",
            "/web_responsive_app_customizer/static/src/js/background_preset_field.esm.js",
            "/web_responsive_app_customizer/static/src/js/apps_menu_customizer.esm.js",
            "/web_responsive_app_customizer/static/src/scss/apps_menu_customizer.scss",
            "/web_responsive_app_customizer/static/src/xml/background_preset_field.xml",
        ],
    },
    "installable": True,
}
