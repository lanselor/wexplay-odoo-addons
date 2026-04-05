# -*- coding: utf-8 -*-
{
    "name": "Wexplay Image Core",
    "version": "18.0.1.0.0",
    "summary": "Core reutilizable para gestión de imágenes con DMS",
    "description": """
Core reutilizable de imágenes para el ecosistema Wexplay.
    """,
    "category": "Tools",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "web",
        "dms",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "views/wex_image_tag_views.xml",
        "views/wex_image_record_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
