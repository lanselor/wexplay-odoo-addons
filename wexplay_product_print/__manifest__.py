{
    "name": "Wexplay - Product Print Center",
    "version": "18.0.1.0.0",
    "category": "Wexplay",
    "depends": ["web", "product", "wex_print_core"],
    "data": [
        "reports/paperformat_product.xml",
        "reports/report_actions.xml",
        "reports/report_product_label_ql700.xml",
        "data/document_type_update.xml",
        "views/product_print_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_product_print/static/src/js/product_print_modal.js",
            # Workaround: forzar carga del template en el bundle backend (evita Missing template)
            "wexplay_product_print/static/src/xml/product_print_modal.xml",
        ],
    },
    "installable": True,
    "application": False,
}
