{
    "name": "Wex Accounting Portal",
    "version": "18.0.1.0.0",
    "summary": "Read-only accounting portal for Wexplay external advisors",
    "description": """
Portal financiero de solo lectura para consulta de facturas de venta y ventas POS.
No expone backend contable ni funcionalidades de compra.
""",
    "category": "Website/Portal",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "depends": [
        "portal",
        "website",
        "account",
        "point_of_sale",
        "spreadsheet_dashboard",
    ],
    "data": [
        "security/wex_accounting_portal_security.xml",
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/portal_templates.xml",
        "views/accounting_dashboard_report_views.xml",
        "data/spreadsheet_dashboard.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
