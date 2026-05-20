# -*- coding: utf-8 -*-
{
    "name": "Wexplay Repair Images",
    "version": "18.0.1.0.0",
    "summary": "Integración SAT de imágenes sobre repair.order",
    "description": """
Integración SAT del core de imágenes para repair.order.
    """,
    "category": "Services/Repair",
    "author": "Wexplay",
    "website": "https://www.wexplay.com",
    "license": "LGPL-3",
    "depends": [
        "repair",
        "wexplay_repair",
        "wexplay_image_core",
        "wex_consent",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/wex_image_tag_data.xml",
        "views/wex_repair_image_upload_wizard_views.xml",
        "views/repair_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_repair_images/static/src/js/repair_images_dropzone.js",
            "wexplay_repair_images/static/src/scss/repair_images.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
