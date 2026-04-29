# -*- coding: utf-8 -*-
{
    "name": "Wexplay - Repair Delivery Flow",
    "version": "18.0.1.0.0",
    "category": "Repair",
    "summary": "Flujo de entrega SAT al cobrar factura",
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "repair",
        "account",
        "stock",
        "mail",
        "wexplay_repair",
        "wexplay_repair_workflow",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/repair_order_views.xml",
        "views/repair_order_search_views.xml",
        "views/repair_order_actions.xml",
        "views/res_config_settings_views.xml",
        "views/repair_channel_templates.xml",
        "views/repair_delivery_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
