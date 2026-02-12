# -*- coding: utf-8 -*-
{
    "name": "Wex WhatsApp Chatter (Base)",
    "version": "18.0.1.0.0",
    "category": "Productivity",
    "summary": "WhatsApp click-to-chat base + templates (no wizard yet).",
    "license": "LGPL-3",
    "author": "Wexplay",
    "depends": [
        "base",
        "mail",
        "sale",
        "account"
    ],
    "data": [
        "security/whatsapp_security.xml",
        "security/ir.model.access.csv",
        "security/whatsapp_rules.xml",
        "views/whatsapp_template_views.xml",
        "views/whatsapp_compose_wizard_views.xml",
        "views/whatsapp_menus.xml",
    ],
    "application": False,
    "installable": True,
}
