{
    "name": "Wexplay - Purchase List (SAT)",
    "version": "18.0.1.0.0",
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
        "repair",
        "sale",
        "stock",
        "web",
        "wex_whatsapp_chatter",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",

        "views/purchase_list_line_views.xml",
        "views/repair_order_views.xml",
        "views/sale_order_views.xml",
        "views/product_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wex_purchase_list/static/src/js/purchase_list_operational_action.js",
            "wex_purchase_list/static/src/xml/purchase_list_operational_action.xml",
            "wex_purchase_list/static/src/css/purchase_list.css",
        ],
    },
    "installable": True,
    "application": False,
}
