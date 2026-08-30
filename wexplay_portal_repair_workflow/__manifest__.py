# -*- coding: utf-8 -*-
{
    "name": "Wexplay Portal - Repair Workflow",
    "version": "18.0.1.0.0",
    "category": "Website/Portal",
    "summary": "Aceptacion de presupuestos SAT desde el portal cliente",
    "description": """
Bridge module between Wexplay Portal and Wexplay Repair Workflow.

Current MVP:
- add a contextual sticky bar to portal repair pages
- expose a focused portal budget summary
- allow B2B portal customers to accept or reject linked SAT quotations
""",
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "wex_knowledge",
        "wexplay_portal",
        "wexplay_repair_workflow",
    ],
    "data": [
        "security/wex_portal_repair_event_security.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/portal_dashboard_views.xml",
        "views/portal_repair_event_views.xml",
        "views/portal_repair_workflow_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_portal_repair_workflow/static/src/js/portal_dashboard.js",
            "wexplay_portal_repair_workflow/static/src/xml/portal_dashboard.xml",
            "wexplay_portal_repair_workflow/static/src/scss/portal_dashboard.scss",
        ],
        "web.assets_frontend": [
            "wexplay_portal_repair_workflow/static/src/js/portal_pending_budget_alert.js",
            "wexplay_portal_repair_workflow/static/src/scss/portal_repair_workflow.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
