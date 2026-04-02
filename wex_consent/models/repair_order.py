# -*- coding: utf-8 -*-

from odoo import _, fields, models


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_device_description = fields.Text(string="Descripción del dispositivo")
    x_consent_document_ids = fields.One2many(
        comodel_name="wex.consent.document",
        inverse_name="repair_order_id",
        string="Documentos de consentimiento",
    )
    x_consent_document_count = fields.Integer(
        compute="_compute_x_consent_document_metrics",
        store=False,
    )
    x_reception_consent_signed = fields.Boolean(
        compute="_compute_x_consent_document_metrics",
        store=False,
    )
    x_delivery_consent_signed = fields.Boolean(
        compute="_compute_x_consent_document_metrics",
        store=False,
    )
    x_reception_consent_status = fields.Char(
        compute="_compute_x_consent_document_metrics",
        string="Estado recepción",
        store=False,
    )
    x_delivery_consent_status = fields.Char(
        compute="_compute_x_consent_document_metrics",
        string="Estado entrega",
        store=False,
    )

    def _get_consent_status_label(self, document_type):
        self.ensure_one()
        document = self.x_consent_document_ids.filtered(
            lambda doc: doc.document_type == document_type
        )[:1]
        if not document:
            return _("Sin solicitar")
        status_labels = {
            "draft": _("Borrador"),
            "pending_signature": _("Pendiente de firma"),
            "signed": _("Firmado"),
            "cancelled": _("Cancelado"),
        }
        return status_labels.get(document.state, document.state)

    def _compute_x_consent_document_metrics(self):
        for rec in self:
            rec.x_consent_document_count = len(rec.x_consent_document_ids)
            rec.x_reception_consent_signed = any(
                doc.document_type == "reception" and doc.state == "signed"
                for doc in rec.x_consent_document_ids
            )
            rec.x_delivery_consent_signed = any(
                doc.document_type == "delivery" and doc.state == "signed"
                for doc in rec.x_consent_document_ids
            )
            rec.x_reception_consent_status = rec._get_consent_status_label("reception")
            rec.x_delivery_consent_status = rec._get_consent_status_label("delivery")

    def action_open_consent_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Consentimientos"),
            "res_model": "wex.consent.document",
            "view_mode": "list,form",
            "domain": [("repair_order_id", "=", self.id)],
            "context": {
                "default_repair_order_id": self.id,
            },
        }

    def _open_signature_request(self, document_type):
        self.ensure_one()
        document = self.env["wex.consent.document"].get_or_create_from_repair(
            self, document_type
        )
        return document.action_open_request_modal()

    def action_request_reception_signature(self):
        return self._open_signature_request("reception")

    def action_request_delivery_signature(self):
        return self._open_signature_request("delivery")
