# -*- coding: utf-8 -*-
from odoo import fields, models


class WexPrintDeviceSnapshot(models.Model):
    _name = "wex.print.device.snapshot"
    _description = "Wex Print Device Snapshot"
    _order = "snapshot_at desc, id desc"

    name = fields.Char(required=True)
    snapshot_at = fields.Datetime(required=True, default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, readonly=True)

    printer_name = fields.Char(required=True, readonly=True)
    driver = fields.Char(readonly=True)
    density = fields.Char(readonly=True)
    trays_text = fields.Text(readonly=True)
    is_default = fields.Boolean(readonly=True)
    is_physical = fields.Boolean(readonly=True)
    printer_type = fields.Char(readonly=True)
    raw_details_json = fields.Text(readonly=True)
