{
    "name": "Wexplay - Vendor Bill OCR",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "OCR ligero de facturas PDF de proveedor desde purchase.order.",
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "account",
        "purchase",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/purchase_order_views.xml",
        "views/vendor_bill_ocr_job_views.xml",
        "views/vendor_bill_ocr_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
