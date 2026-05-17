# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WexPrintDocumentType(models.Model):
    _name = "wex.print.document.type"
    _description = "Wex Print Document Type"
    _order = "name"

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código", required=True, index=True)
    active = fields.Boolean(default=True)

    # Fase 2.1: mantenemos la salida legacy como fuente de verdad.
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
    domain_area = fields.Selection(
        [
            ("sat", "SAT"),
            ("product", "Producto"),
            ("sales", "Ventas"),
            ("purchase", "Compras"),
            ("stock", "Almacén"),
            ("project", "Proyecto"),
            ("account", "Contabilidad"),
            ("other", "Otro"),
        ],
        string="Área",
        default="other",
    )
    model_name = fields.Char(string="Modelo Odoo")
    report_action_id = fields.Many2one("ir.actions.report", string="Reporte", ondelete="restrict")
    paperformat_id = fields.Many2one("report.paperformat", string="Formato de papel", ondelete="restrict")
    report_name = fields.Char(string="Nombre técnico del reporte")
    description = fields.Text(string="Descripción")

    _sql_constraints = [
        ("wex_print_document_type_code_unique", "unique(code)", "Document type code must be unique."),
    ]

    def get_report_name(self):
        self.ensure_one()
        return self.report_name or self.report_action_id.report_name or ""

    @api.model
    def get_document_payload(self, document_code):
        document = self.search([("code", "=", document_code)], limit=1)
        if not document:
            return False

        pf = document.paperformat_id
        return {
            "id": document.id,
            "name": document.name,
            "code": document.code,
            "legacy_kind": document.legacy_kind,
            "domain_area": document.domain_area,
            "model_name": document.model_name or "",
            "report_name": document.get_report_name(),
            "report_action_id": document.report_action_id.id if document.report_action_id else False,
            "paperformat_id": pf.id if pf else False,
            "paperformat_page_width": pf.page_width if pf else 0,
            "paperformat_page_height": pf.page_height if pf else 0,
            # Longitud de corte = dimensión mayor, independientemente de cómo
            # estén almacenadas page_width/page_height en el paperformat.
            "paperformat_label_length": max(pf.page_width, pf.page_height) if pf else 0,
        }
