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
    "installable": True,
    "application": False,
    "depends": [
        "base",
        "product",
        "purchase",
        "repair",
        "sale",   # necesario si heredamos vistas/modelos de ventas
    ],
    "data": [
        # Seguridad siempre primero
        "security/security.xml",
        "security/ir.model.access.csv",

        # Vistas
        "views/purchase_list_line_views.xml",
        "views/repair_order_views.xml",

        # Si has creado la vista de ventas, debe ir aquí
        # "views/sale_order_views.xml",
    ],
}
