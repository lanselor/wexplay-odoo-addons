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
        "mrp_repair",
        "stock",
        "mail",
    ],
    "data": [
        "views/repair_order_views.xml",
        "reports/reports.xml",
        "reports/repair_receipt.xml",
        "reports/repair_label.xml",
        "views/repair_order_list.xml",
        "views/repair_order_search.xml",
    ],
    "assets": {
    "web.assets_backend": [
        "wexplay_repair/static/src/js/repair_order_expand_groups.js",
    ],
},
    "post_init_hook": "post_init_hook",  
    "installable": True,
    "application": True,
    "auto_install": False,
}
