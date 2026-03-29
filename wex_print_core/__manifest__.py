{
    "name": "Wex Print Core",
    "version": "18.0.1.0.0",
    "category": "Wexplay",
    "summary": "Core técnico compartido para impresión local con QZ Tray",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/print_document_type_data.xml",
        "views/res_config_settings_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wex_print_core/static/lib/qz-tray.js",
            "wex_print_core/static/src/js/print_router.js",
            "wex_print_core/static/src/js/qz_print.js",
            "wex_print_core/static/src/js/qz_settings_widget.js",
            "wex_print_core/static/src/xml/qz_settings_widget.xml",
        ],
    },
    "installable": True,
    "application": False,
}
