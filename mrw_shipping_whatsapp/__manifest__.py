# -*- coding: utf-8 -*-

{
    "name": "MRW Shipping WhatsApp",
    "version": "18.0.1.0.0",
    "summary": "WhatsApp tracking messages for MRW shipments.",
    "category": "Inventory/Delivery",
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "mrw_shipping_connector",
        "wex_whatsapp_chatter",
        "wexplay_repair_delivery",
    ],
    "data": [
        "data/whatsapp_template_data.xml",
        "views/mrw_shipping_shipment_views.xml",
        "views/repair_shipping_operation_views.xml",
        "views/repair_order_views.xml",
        "views/whatsapp_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
