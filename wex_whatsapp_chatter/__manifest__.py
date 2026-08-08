# -*- coding: utf-8 -*-

{
    "name": "Wex WhatsApp Chatter",
    "version": "18.0.1.0.0",
    "category": "Productivity",
    "summary": "WhatsApp click-to-chat + templates + wizard.",
    "license": "LGPL-3",
    "author": "Wexplay",
    "depends": [
        "base",
        "mail",
        "sale",
        "account",
    ],
    "data": [
        "security/whatsapp_security.xml",
        "security/ir.model.access.csv",
        "security/whatsapp_rules.xml",
        "views/whatsapp_template_views.xml",
        "views/whatsapp_compose_wizard_views.xml",
        "views/whatsapp_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wex_whatsapp_chatter/static/src/js/chatter_whatsapp_button.js",
            "wex_whatsapp_chatter/static/src/js/whatsapp_open_and_reload.js",
            "wex_whatsapp_chatter/static/src/js/whatsapp_template_picker.js",
            "wex_whatsapp_chatter/static/src/xml/chatter_whatsapp_button.xml",
            "wex_whatsapp_chatter/static/src/xml/whatsapp_template_picker.xml",
            "wex_whatsapp_chatter/static/src/scss/whatsapp_chatter_log.scss",
        ],
    },
    "installable": True,
    "application": False,
}
