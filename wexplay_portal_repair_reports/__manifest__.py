# -*- coding: utf-8 -*-
{
    "name": "Wexplay Portal Repair Reports",
    "version": "18.0.1.0.0",
    "summary": "Informes SAT bajo demanda para clientes B2B",
    "category": "Website/Portal",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "depends": [
        "wexplay_portal",
        "wexplay_repair_images",
        "wexplay_portal_repair_workflow",
    ],
    "data": [
        "data/mail_message_subtype_data.xml",
        "views/portal_repair_report_templates.xml",
        "reports/portal_sat_service_report.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "wexplay_portal_repair_reports/static/src/js/portal_repair_reports.js",
            "wexplay_portal_repair_reports/static/src/scss/portal_repair_reports.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
