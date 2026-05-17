# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WexPrintProfile(models.Model):
    _name = "wex.print.profile"
    _description = "Wex Print Profile"
    _order = "name"

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código", required=True, index=True)
    active = fields.Boolean(default=True)

    legacy_kind = fields.Selection(
        [
            ("label", "Etiqueta"),
            ("thermal", "Térmica"),
            ("a4", "A4"),
        ],
        string="Tipo legacy",
        required=True,
        default="label",
    )
    device_id = fields.Many2one("wex.print.device", string="Dispositivo", ondelete="restrict")
    printer_name = fields.Char(string="Nombre directo de impresora")
    allow_fallback = fields.Boolean(string="Permitir fallback", default=True)
    copies_override = fields.Integer(string="Copias", default=0)
    duplex_mode = fields.Selection(
        [
            ("default", "Por defecto"),
            ("long-edge", "Doble cara (borde largo)"),
            ("short-edge", "Doble cara (borde corto)"),
            ("one-sided", "Una cara"),
        ],
        string="Modo dúplex",
        default="default",
        required=True,
    )
    company_id = fields.Many2one("res.company", string="Empresa")
    notes = fields.Text(string="Notas")

    _sql_constraints = [
        ("wex_print_profile_code_unique", "unique(code)", "Print profile code must be unique."),
    ]

    @api.constrains("device_id", "printer_name")
    def _check_printer_target(self):
        for record in self:
            if not record.device_id and not record.printer_name:
                raise ValidationError("A print profile requires either a saved device or a direct printer name.")

    def get_resolved_printer_name(self):
        self.ensure_one()
        return self.device_id.qz_printer_name or self.printer_name or ""
