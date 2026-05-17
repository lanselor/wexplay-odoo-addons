# -*- coding: utf-8 -*-
from odoo import fields, models


class WexPrintDevice(models.Model):
    _name = "wex.print.device"
    _description = "Wex Print Device"
    _order = "name"

    name = fields.Char(string="Nombre", required=True)
    active = fields.Boolean(default=True)
    backend = fields.Selection(
        [
            ("qz", "QZ Tray"),
        ],
        string="Backend",
        required=True,
        default="qz",
    )
    qz_printer_name = fields.Char(string="Nombre en QZ", required=True)
    device_kind = fields.Selection(
        [
            ("label", "Etiqueta"),
            ("thermal", "Térmica"),
            ("a4", "A4"),
        ],
        string="Tipo",
        required=True,
        default="label",
    )
    model_hint = fields.Char(
        string="Modelo de impresora",
        help="Solo informativo. Ej: 'Brother QL-710W'. Útil para identificar dispositivos de la misma familia.",
    )
    paperformat_ids = fields.Many2many(
        "report.paperformat",
        "wex_print_device_paperformat_rel",
        "device_id",
        "paperformat_id",
        string="Formatos de papel soportados",
    )
    report_action_ids = fields.Many2many(
        "ir.actions.report",
        "wex_print_device_report_rel",
        "device_id",
        "report_id",
        string="Reportes compatibles",
    )
    company_id = fields.Many2one("res.company", string="Empresa")
    notes = fields.Text(string="Notas")

    profile_ids = fields.One2many("wex.print.profile", "device_id", string="Perfiles")
