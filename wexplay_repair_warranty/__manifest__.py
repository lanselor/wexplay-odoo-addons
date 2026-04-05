# -*- coding: utf-8 -*-
{
    "name": "Wexplay - Repair Warranty",
    "version": "18.0.1.0.0",
    "category": "Repair",
    "summary": "Garantías SAT y RMAs sobre repair.order",
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "repair",
        "account",
        "product",
        "sale",
        "wexplay_repair",
        "wexplay_repair_workflow",
        "wexplay_repair_delivery",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/product_template_views.xml",
        "views/repair_order_views.xml",
        "views/repair_order_workflow_views.xml",
        "views/res_partner_views.xml",
        "wizard/repair_warranty_claim_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_repair_warranty/static/src/scss/repair_warranty.scss",
        ],
    },
    "installable": True,
    "application": False,
}
