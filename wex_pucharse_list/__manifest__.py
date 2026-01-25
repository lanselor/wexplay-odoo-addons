{
    "name": "Wexplay - Purchase List (SAT)",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "Lista interna de compra tipo hoja para repuestos (Wexplay SAT).",
    "description": """
Lista de compra mínima para SAT (taller de reparaciones).
Fase 1: líneas sueltas, sin RFQ/PO automáticos.
""",
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "purchase",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/purchase_list_line_views.xml",
    ],
    "installable": True,
    "application": False,
}
