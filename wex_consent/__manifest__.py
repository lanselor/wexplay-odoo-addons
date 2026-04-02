# -*- coding: utf-8 -*-
{
    "name": "Wex Consent",
    "version": "18.0.1.0.0",
    "summary": "Consentimientos y firmas SAT para Wexplay",
    "description": """
Sistema propio de consentimientos y firma para el flujo SAT de Wexplay.
    """,
    "category": "Services/Repair",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "depends": [
        "repair",
        "mail",
        "web",
        "dms",
        "wexplay_repair",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "views/res_config_settings_views.xml",
        "views/repair_order_views.xml",
        "views/wex_consent_document_views.xml",
        "views/wex_consent_kiosk_views.xml",
        "views/wex_consent_templates.xml",
        "reports/wex_consent_reports.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wex_consent/static/src/js/consent_request_modal.js",
            "wex_consent/static/src/js/consent_kiosk_action.js",
            "wex_consent/static/src/xml/consent_request_modal.xml",
            "wex_consent/static/src/xml/consent_kiosk_action.xml",
            "wex_consent/static/src/scss/wex_consent.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
