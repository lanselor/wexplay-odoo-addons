# -*- coding: utf-8 -*-
from odoo import fields, models


class WexPrintTrace(models.Model):
    _name = "wex.print.trace"
    _description = "Wex Print Trace"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, default="Print Trace")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, readonly=True)

    document_type_id = fields.Many2one("wex.print.document.type", readonly=True)
    document_code = fields.Char(readonly=True)
    report_name = fields.Char(readonly=True)
    report_url = fields.Char(readonly=True)

    requested_mode = fields.Selection(
        [
            ("legacy", "Legacy"),
            ("hybrid", "Hybrid"),
            ("new_only", "New Only"),
        ],
        readonly=True,
    )
    execution_mode = fields.Selection(
        [
            ("legacy", "Legacy"),
            ("hybrid", "Hybrid"),
            ("new_only", "New Only"),
        ],
        readonly=True,
    )
    resolution_source = fields.Selection(
        [
            ("legacy", "Legacy"),
            ("new", "New"),
            ("fallback_legacy", "Fallback Legacy"),
        ],
        readonly=True,
    )
    legacy_kind = fields.Selection(
        [
            ("label", "Label"),
            ("thermal", "Thermal"),
            ("a4", "A4"),
        ],
        readonly=True,
    )
    printer_name = fields.Char(readonly=True)
    allow_fallback = fields.Boolean(readonly=True)
    copies = fields.Integer(readonly=True, default=1)
    success = fields.Boolean(readonly=True)
    message = fields.Text(readonly=True)
