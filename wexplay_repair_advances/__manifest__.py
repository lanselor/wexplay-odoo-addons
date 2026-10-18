{
    "name": "Wexplay SAT Advances",
    "version": "18.0.1.0.4",
    "license": "LGPL-3",
    "author": "Wexplay",
    "depends": ["wexplay_repair", "web_responsive_app_customizer"],
    "data": [
        "security/advance_security.xml",
        "security/ir.model.access.csv",
        "views/advance_views.xml",
        "views/advance_notice_views.xml",
        "wizard/advance_register_views.xml",
        "reports/advance_receipt.xml",
    ],
    "assets": {"web.assets_backend": [
        "wexplay_repair_advances/static/src/js/advance_footer.js",
        "wexplay_repair_advances/static/src/xml/advance_footer.xml",
        "wexplay_repair_advances/static/src/scss/advance_footer.scss",
        "wexplay_repair_advances/static/src/scss/advance_notice.scss",
        "wexplay_repair_advances/static/src/js/advance_notice.js",
        "wexplay_repair_advances/static/src/xml/advance_notice.xml",
    ]},
    "installable": True,
}
