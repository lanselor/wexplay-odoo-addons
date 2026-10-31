{
    "name": "Wexplay - Purchase List (SAT)",
    "version": "18.0.1.5.0",
    "category": "Purchases",
    "summary": "Lista interna de compra tipo hoja (Wexplay SAT).",
    "description": """
Lista de compra mínima para taller de reparaciones.

- SAT: añadir piezas desde repair (stock.move) a lista interna
- Compras: generar RFQ agrupadas por proveedor desde la lista
""",
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "product",
        "purchase",
        "purchase_stock",
        "repair",
        "sale",
        "stock",
        "web",
        "wex_whatsapp_chatter",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/return_location.xml",
        "views/res_config_settings_views.xml",

        "views/purchase_list_line_views.xml",
        "views/repair_order_views.xml",
        "views/sale_order_views.xml",
        "views/product_views.xml",
        "views/return_settings_menu.xml",
        "wizard/return_prepare_views.xml",
        "views/return_staging_views.xml",
        "wizard/return_dispatch_views.xml",
        "views/purchase_return_views.xml",
        "wizard/return_resolve_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wex_purchase_list/static/src/js/purchase_list_operational_action.js",
            "wex_purchase_list/static/src/xml/purchase_list_operational_action.xml",
            "wex_purchase_list/static/src/css/purchase_list.css",
            "wex_purchase_list/static/src/css/return_prepare.css",
        ],
    },
    "installable": True,
    "application": False,
}
