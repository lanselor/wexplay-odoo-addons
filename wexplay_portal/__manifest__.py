{
    "name": "Wexplay Portal",
    "version": "18.0.1.0.2",
    "summary": "Portal B2B para clientes empresa de Wexplay",
    "description": """
Bridge module between the native Odoo portal and Wexplay business modules.

Current MVP:
- reuse standard invoice portal access
- expose SAT repair orders to authenticated B2B portal users
- prepare an IT maintenance entry point for future phases
""",
    "category": "Website/Portal",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "depends": [
        "portal",
        "website",
        "account",
        "wexplay_repair",
    ],
    "data": [
        "security/wexplay_portal_security.xml",
        "security/ir.model.access.csv",
        "views/portal_templates.xml",
        "views/res_partner_views.xml",
        "views/repair_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": ["wexplay_portal/static/src/scss/repair_portal.scss"],
        "web.assets_frontend": [
            "wexplay_portal/static/src/scss/portal.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
