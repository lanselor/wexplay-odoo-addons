{
    "name": "Wexplay - Product Print Center",
    "version": "18.0.1.0.0",
    "category": "Wexplay",
    "depends": ["web", "product"],
    "data": [
        "views/assets.xml",
        "views/product_print_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_product_print/static/src/js/product_print_modal.js",
            "wexplay_product_print/static/src/xml/product_print_modal.xml",
        ],
    },
    "installable": True,
    "application": False,
}
