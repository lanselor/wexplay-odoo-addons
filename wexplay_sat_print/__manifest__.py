# wexplay_sat_print/__manifest__.py
{
    "name": "Wexplay - SAT Print (QZ)",
    "version": "18.0.1.0.0",
    "category": "Wexplay",
    "summary": "Centro de impresión SAT para órdenes de reparación (QZ Tray + QWeb)",
    "description": """
Wexplay - SAT Print (QZ)
=======================

Añade un centro de impresión específico para SAT en órdenes de reparación (repair.order):
- Botón "Impresiones" en la orden de reparación
- Modal SAT con 3 opciones de impresión (2 etiquetas Brother QL + ticket térmico)
- Reportes QWeb + paperformats
- Placeholder en Ajustes (res.config.settings) para configuración futura

Reutiliza la integración QZ existente en wexplay_product_print (sin modificarla).
""",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "depends": [
        "web",
        "repair",
        "base",
        "wexplay_product_print",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",

        "views/repair_print_actions.xml",
        "views/repair_order_form_inherit_print.xml",
        "views/res_config_settings_sat_print.xml",

        "reports/paperformat_sat.xml",
        "reports/reports_sat.xml",
        "reports/repair_label_29x90.xml",
        "reports/repair_label_29x42.xml",
        "reports/repair_ticket_80x170.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_sat_print/static/src/js/repair_print_center_action.js",
            "wexplay_sat_print/static/src/js/repair_print_center_modal.js",
            "wexplay_sat_print/static/src/xml/repair_print_center_modal.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
