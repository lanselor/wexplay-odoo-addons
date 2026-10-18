{
    "name": "Wex Redsys Payments",
    "version": "18.0.1.0.0",
    "category": "Accounting/Payment Providers",
    "summary": "Native quotation and invoice payments through Redsys redirect",
    "author": "Wexplay, Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["account_payment"],
    "external_dependencies": {"python": ["cryptography"]},
    "data": [
        "views/payment_templates.xml",
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
