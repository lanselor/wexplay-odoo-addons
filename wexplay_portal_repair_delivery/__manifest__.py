# -*- coding: utf-8 -*-
{
    "name": "Wexplay Portal - Repair Delivery",
    "version": "18.0.1.0.0",
    "category": "Website/Portal",
    "summary": "Consulta de envios SAT desde el portal cliente",
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "wexplay_portal",
        "wexplay_repair_delivery",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/portal_repair_delivery_mail_template_data.xml",
        "views/res_config_settings_views.xml",
        "views/portal_repair_delivery_templates.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
