{
    "name": "MRW Shipping Connector",
    "version": "18.0.1.0.0",
    "summary": "Generic MRW shipping connector for Odoo",
    "description": """
MRW Shipping Connector
======================

Generic MRW shipping connector for Odoo 18 Community.

Architecture reset on 2026-05-06:

The target connector must follow Odoo's native delivery flow based on
delivery.carrier and stock.picking through stock_delivery.

MRW Shipments remains available for manual shipments and TEST validation while
the native Odoo delivery carrier integration is added progressively.
    """,
    "category": "Inventory/Delivery",
    "author": "MRW Shipping Connector Contributors",
    "website": "",
    "license": "LGPL-3",
    "depends": ["delivery", "stock_delivery", "mail"],
    "images": ["static/description/icon.png"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/mrw_shipping_service_data.xml",
        "data/mrw_shipping_mail_template_data.xml",
        "views/delivery_carrier_views.xml",
        "views/stock_picking_views.xml",
        "views/mrw_shipping_config_views.xml",
        "views/mrw_shipping_service_views.xml",
        "views/mrw_shipping_shipment_views.xml",
        "views/mrw_shipping_notification_views.xml",
        "views/mrw_shipping_log_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
