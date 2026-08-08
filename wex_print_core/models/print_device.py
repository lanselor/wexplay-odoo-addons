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
    assignment_ids = fields.One2many(
        "wex.print.assignment",
        "device_id",
        string="Documentos configurados",
        readonly=True,
    )

    def action_open_document_setup_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Añadir documentos a impresora",
            "res_model": "wex.print.device.setup.wizard",
            "view_mode": "form",
            "context": {"default_existing_device_id": self.id},
            "target": "new",
        }

    def _sync_capabilities_from_assignments(self):
        """Mantiene las capacidades físicas alineadas con los documentos enrutados."""
        assignment_model = self.env["wex.print.assignment"]
        for device in self:
            document_types = assignment_model.search(
                [("device_id", "=", device.id)]
            ).mapped("document_type_id")
            device.write({
                "paperformat_ids": [(6, 0, document_types.mapped("paperformat_id").ids)],
                "report_action_ids": [(6, 0, document_types.mapped("report_action_id").ids)],
            })
