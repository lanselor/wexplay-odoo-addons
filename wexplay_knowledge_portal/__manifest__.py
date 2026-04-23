# -*- coding: utf-8 -*-
{
    "name": "Wexplay Knowledge Portal",
    "version": "18.0.1.0.0",
    "summary": "Publicacion portal y acceso publico por enlace para Knowledge",
    "category": "Wexplay",
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "portal",
        "website",
        "wex_knowledge",
        "wexplay_portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/knowledge_article_views.xml",
        "views/portal_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_knowledge_portal/static/src/js/knowledge_article_sticky_footer.js",
            "wexplay_knowledge_portal/static/src/scss/knowledge_portal_backend.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
