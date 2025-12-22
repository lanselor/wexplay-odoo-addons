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
        "security/ir.model.access.csv",
        "views/repair_order_views.xml",
        "views/device_brand_views.xml",
        "views/device_model_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
