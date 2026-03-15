{
    "name": "Wexplay Repair Management",
    "version": "18.0.1.0.0",
    "summary": "Personalizaciones del módulo de reparaciones para Wexplay",
    "description": """
Wexplay Repair Management
=========================

Personalizaciones y ampliaciones del módulo estándar de reparaciones (mrp_repair)
para adaptarlo al flujo real de SAT de Wexplay (móviles, portátiles, tablets,
consolas y otros dispositivos electrónicos).
""",
    "category": "Services/Repair",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "depends": [
        "repair",
        "stock",
        "mail",
        'hr',
        "account",
        "sale",
        "stock",
         "base",

    ],
    "data": [
        'security/ir.model.access.csv',
        "views/res_config_settings_views.xml",
        "views/repair_order_views.xml",
        "views/repair_order_list.xml",
        "views/repair_order_search.xml",
        "views/account_move_view_inherit.xml",
        "reports/report_invoice_sat.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_repair/static/src/js/repair_order_expand_button.js",
            "wexplay_repair/static/src/js/repair_notes_badge.js",
            "wexplay_repair/static/src/scss/repair_notes_badge.scss",
            #"wexplay_repair/static/src/xml/repair_order_expand_button.xml",
        ],
    },

    "post_init_hook": "post_init_hook",  
    "installable": True,
    "application": True,
    "auto_install": False,
}
