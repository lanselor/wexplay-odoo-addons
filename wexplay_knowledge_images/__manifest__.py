# -*- coding: utf-8 -*-
{
    "name": "Wexplay Knowledge Images",
    "version": "18.0.1.0.0",
    "summary": "Imagenes embebidas en Knowledge con almacenamiento DMS",
    "description": """
Integracion opcional de imagenes embebidas para articulos de knowledge
con OCA DMS como almacenamiento principal.
    """,
    "category": "Tools",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "depends": [
        "web",
        "web_editor",
        "wex_knowledge",
        "dms",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/knowledge_article_image_views.xml",
        "views/knowledge_article_image_upload_wizard_views.xml",
        "views/knowledge_article_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_knowledge_images/static/src/js/knowledge_article_image_insert.js",
            "wexplay_knowledge_images/static/src/scss/knowledge_article_images.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
