# -*- coding: utf-8 -*-
{
    "name": "Wexplay Repair Images",
    "version": "18.0.1.1.3",
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
        "web_responsive_app_customizer",
        "queue_job",
        "wexplay_repair",
        "wexplay_image_core",
        "wex_consent",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/wex_image_tag_data.xml",
        "data/queue_job_data.xml",
        "data/ir_cron.xml",
        "views/wex_repair_image_upload_wizard_views.xml",
        "views/repair_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wexplay_repair_images/static/src/js/chatter_repair_images_patch.js",
            "wexplay_repair_images/static/src/scss/repair_images.scss",
            "wexplay_repair_images/static/src/xml/chatter_repair_images.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
