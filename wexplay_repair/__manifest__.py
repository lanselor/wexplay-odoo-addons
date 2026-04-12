{
    "name": "Wexplay Repair Management",
    "version": "18.0.1.0.1",
    "summary": "Personalizaciones del mÃƒÂ³dulo de reparaciones para Wexplay",
    "description": """
Wexplay Repair Management
=========================

Personalizaciones y ampliaciones del mÃƒÂ³dulo estÃƒÂ¡ndar de reparaciones (mrp_repair)
para adaptarlo al flujo real de SAT de Wexplay (mÃƒÂ³viles, portÃƒÂ¡tiles, tablets,
consolas y otros dispositivos electrÃƒÂ³nicos).
""",
    "category": "Wexplay",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "images": ["static/description/icon.png"],
    "depends": [
        "repair",
        "repair_scheduled_date_calendar_view",
        "dms",
        "web",
        "stock",
        "mail",
        "hr",
        "account",
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template_data.xml",
        "views/res_config_settings_views.xml",
        "views/repair_order_views.xml",
        "views/repair_order_list.xml",
        "views/repair_order_card_view.xml",
        "views/repair_order_search.xml",
        "views/account_move_view_inherit.xml",
        "reports/report_invoice_sat.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_repair/static/src/js/repair_device_type_picker_field.js",
            "wexplay_repair/static/src/js/repair_sat_priority_field.js",
            "wexplay_repair/static/src/js/repair_unlock_pattern_field.js",
            "wexplay_repair/static/src/js/repair_order_card_view.js",
            "wexplay_repair/static/src/js/repair_notes_badge.js",
            "wexplay_repair/static/src/xml/repair_device_type_picker_field.xml",
            "wexplay_repair/static/src/xml/repair_sat_priority_field.xml",
            "wexplay_repair/static/src/xml/repair_unlock_pattern_field.xml",
            "wexplay_repair/static/src/xml/repair_order_card_view.xml",
            "wexplay_repair/static/src/scss/repair_notes_badge.scss",
            "wexplay_repair/static/src/scss/repair_order_form.scss",
            "wexplay_repair/static/src/scss/repair_order_card_view.scss",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
}
