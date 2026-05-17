# -*- coding: utf-8 -*-
from odoo import fields, models


class WexPrintTrace(models.Model):
    _name = "wex.print.trace"
    _description = "Wex Print Trace"
    _order = "create_date desc, id desc"

    name = fields.Char(string="Nombre", required=True, default="Traza de impresión")
    user_id = fields.Many2one("res.users", string="Usuario", default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one("res.company", string="Empresa", default=lambda self: self.env.company, readonly=True)

    document_type_id = fields.Many2one("wex.print.document.type", string="Tipo de documento", readonly=True)
    document_code = fields.Char(string="Código de documento", readonly=True)
    report_name = fields.Char(string="Nombre de reporte", readonly=True)
    report_url = fields.Char(string="URL del reporte", readonly=True)

    requested_mode = fields.Selection(
        [
            ("legacy", "Legacy"),
            ("hybrid", "Híbrido"),
            ("new_only", "Solo nuevo"),
        ],
        string="Modo solicitado",
        readonly=True,
    )
    execution_mode = fields.Selection(
        [
            ("legacy", "Legacy"),
            ("hybrid", "Híbrido"),
            ("new_only", "Solo nuevo"),
        ],
        string="Modo ejecutado",
        readonly=True,
    )
    resolution_source = fields.Selection(
        [
            ("legacy", "Legacy"),
            ("new", "Nuevo"),
            ("fallback_legacy", "Fallback a legacy"),
        ],
        string="Fuente de resolución",
        readonly=True,
    )
    legacy_kind = fields.Selection(
        [
            ("label", "Etiqueta"),
            ("thermal", "Térmica"),
            ("a4", "A4"),
        ],
        string="Tipo legacy",
        readonly=True,
    )
    printer_name = fields.Char(string="Impresora (legacy)", readonly=True)
    allow_fallback = fields.Boolean(string="Fallback permitido", readonly=True)
    copies = fields.Integer(string="Copias", readonly=True, default=1)
    next_resolution_found = fields.Boolean(string="Resolución nueva encontrada", readonly=True)
    next_profile_id = fields.Many2one("wex.print.profile", string="Perfil nuevo", readonly=True)
    next_printer_name = fields.Char(string="Impresora (nueva)", readonly=True)
    next_allow_fallback = fields.Boolean(string="Fallback permitido (nuevo)", readonly=True)
    next_duplex_mode = fields.Selection(
        [
            ("default", "Por defecto"),
            ("long-edge", "Doble cara (borde largo)"),
            ("short-edge", "Doble cara (borde corto)"),
            ("one-sided", "Una cara"),
        ],
        string="Dúplex (nuevo)",
        readonly=True,
    )
    shadow_matches_legacy = fields.Boolean(string="Coincide con legacy", readonly=True)
    pilot_use_new_resolution = fields.Boolean(string="Piloto resolución nueva", readonly=True)
    next_message = fields.Text(string="Mensaje resolución nueva", readonly=True)
    success = fields.Boolean(string="Éxito", readonly=True)
    message = fields.Text(string="Mensaje", readonly=True)
