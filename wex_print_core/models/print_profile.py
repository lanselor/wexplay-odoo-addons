# -*- coding: utf-8 -*-
from odoo import fields, models


class WexPrintProfile(models.Model):
    _name = "wex.print.profile"
    _description = "Wex Print Profile"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)

    legacy_kind = fields.Selection(
        [
            ("label", "Label"),
            ("thermal", "Thermal"),
            ("a4", "A4"),
        ],
        required=True,
        default="label",
    )
    printer_name = fields.Char(required=True)
    allow_fallback = fields.Boolean(default=True)
    copies_override = fields.Integer(default=0)
    company_id = fields.Many2one("res.company")
    notes = fields.Text()

    _sql_constraints = [
        ("wex_print_profile_code_unique", "unique(code)", "Print profile code must be unique."),
    ]
