# -*- coding: utf-8 -*-
from odoo import fields, models


class WexPrintDocumentType(models.Model):
    _name = "wex.print.document.type"
    _description = "Wex Print Document Type"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)

    # Fase 2.1: mantenemos la salida legacy como fuente de verdad.
    legacy_kind = fields.Selection(
        [
            ("label", "Label"),
            ("thermal", "Thermal"),
            ("a4", "A4"),
        ],
        required=True,
        default="label",
    )
    report_name = fields.Char()
    description = fields.Text()

    _sql_constraints = [
        ("wex_print_document_type_code_unique", "unique(code)", "Document type code must be unique."),
    ]
