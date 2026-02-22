{
    "name": "Wexplay - Product Code Rules",
    "version": "18.0.1.0.0",
    "category": "Inventory",
    "summary": "Auto-generate product internal references by category with independent sequences",
    "depends": [
        "product",
        'stock',
        ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/product_code_rule_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
