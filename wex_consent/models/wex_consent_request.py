# -*- coding: utf-8 -*-

import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WexConsentRequest(models.Model):
    _name = "wex.consent.request"
    _description = "Solicitud de consentimiento"
    _inherit = ["mail.thread", "mail.activity.mixin", "wex.consent.kiosk.access.mixin"]
    _order = "create_date asc, id asc"

    name = fields.Char(
        default=lambda self: _("Nueva solicitud de firma"),
        required=True,
    )
    token = fields.Char(
        required=True,
        copy=False,
        default=lambda self: str(uuid.uuid4()),
    )
    document_id = fields.Many2one(
        comodel_name="wex.consent.document",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    repair_order_id = fields.Many2one(
        related="document_id.repair_order_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="document_id.company_id",
        store=True,
        readonly=True,
    )
    document_type = fields.Selection(
        related="document_id.document_type",
        store=True,
        readonly=True,
    )
    requested_by_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        readonly=True,
    )
    kiosk_session_id = fields.Many2one(
        comodel_name="wex.consent.kiosk.session",
        string="Sesión de kiosko",
        copy=False,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("queued", "En cola"),
            ("presented", "Mostrada"),
            ("signed", "Firmada"),
            ("cancelled", "Cancelada"),
            ("failed", "Fallida"),
        ],
        default="queued",
        required=True,
        tracking=True,
        copy=False,
    )
    cancel_requested = fields.Boolean(copy=False)
    queued_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    presented_at = fields.Datetime(readonly=True, copy=False)
    completed_at = fields.Datetime(readonly=True, copy=False)
    cancelled_at = fields.Datetime(readonly=True, copy=False)
    status_message = fields.Char(copy=False)
    active_in_kiosk = fields.Boolean(
        compute="_compute_active_in_kiosk",
        store=False,
    )

    _sql_constraints = [
        ("wex_consent_request_token_uniq", "unique(token)", "The request token must be unique."),
    ]

    @api.model
    def _sanitize_signer_name(self, signer_name):
        signer_name = (signer_name or "").strip()
        if not signer_name:
            raise UserError(_("El nombre del firmante es obligatorio."))
        if len(signer_name) > 128:
            raise UserError(_("El nombre del firmante es demasiado largo."))
        return signer_name

    @api.model
    def _sanitize_signer_vat(self, signer_vat):
        signer_vat = (signer_vat or "").strip()
        if not signer_vat:
            raise UserError(_("El DNI/NIF del firmante es obligatorio."))
        if len(signer_vat) > 64:
            raise UserError(_("El DNI/NIF del firmante es demasiado largo."))
        return signer_vat

    @api.model
    def _sanitize_consent_values(self, consent_values):
        allowed_keys = {
            "legal_data_protection",
            "allow_email_non_commercial",
            "allow_email_commercial",
            "allow_whatsapp_non_commercial",
            "allow_whatsapp_commercial",
            "warranty_conditions_accepted",
        }
        sanitized_values = {}
        for key, value in (consent_values or {}).items():
            if key in allowed_keys:
                sanitized_values[key] = bool(value)
        return sanitized_values

    @api.depends("state", "kiosk_session_id.active_request_id")
    def _compute_active_in_kiosk(self):
        for rec in self:
            rec.active_in_kiosk = (
                rec.state == "presented" and rec.kiosk_session_id.active_request_id == rec
            )

    def _assert_cancellable(self):
        self.ensure_one()
        if self.state == "signed":
            raise UserError(_("No se puede cancelar una firma ya completada."))
        if self.state in ("cancelled", "failed"):
            raise UserError(_("La solicitud ya no está activa."))

    def action_cancel_request(self):
        for rec in self:
            rec._assert_cancellable()
            rec.write(
                {
                    "cancel_requested": True,
                    "state": "cancelled",
                    "cancelled_at": fields.Datetime.now(),
                    "status_message": _("Cancelada por el técnico."),
                }
            )
            if rec.kiosk_session_id:
                rec.kiosk_session_id.touch(active_request_id=False)
            rec.document_id._sync_state_from_requests()
            rec.document_id._message_repair_order(
                _(
                    "Solicitud de firma cancelada por el técnico %(user)s. Referencia: %(request)s."
                )
                % {
                    "user": self.env.user.display_name,
                    "request": rec.name,
                }
            )
        return True

    def action_cancel_from_kiosk(self):
        self._check_kiosk_access()
        for rec in self:
            rec._assert_cancellable()
            rec.write(
                {
                    "cancel_requested": True,
                    "state": "cancelled",
                    "cancelled_at": fields.Datetime.now(),
                    "status_message": _("Cancelada desde el kiosko."),
                }
            )
            if rec.kiosk_session_id:
                rec.kiosk_session_id.touch(active_request_id=False)
            rec.document_id._sync_state_from_requests()
            rec.document_id._message_repair_order(
                _(
                    "Solicitud de firma cancelada desde el kiosko. Referencia: %(request)s."
                )
                % {
                    "request": rec.name,
                }
            )
        return True

    def action_mark_presented(self, kiosk_session):
        self.ensure_one()
        self._check_kiosk_access()
        if self.state != "queued":
            return False
        self.write(
            {
                "state": "presented",
                "kiosk_session_id": kiosk_session.id,
                "presented_at": fields.Datetime.now(),
                "status_message": _("Mostrada en kiosko."),
            }
        )
        kiosk_session.touch(active_request_id=self.id)
        self.document_id.write({"state": "pending_signature"})
        self.document_id._message_repair_order(
            _(
                "Solicitud de firma mostrada en el kiosko %(kiosk)s. Referencia: %(request)s."
            )
            % {
                "kiosk": kiosk_session.display_name,
                "request": self.name,
            }
        )
        return True

    def action_mark_failed(self, message):
        self.write(
            {
                "state": "failed",
                "completed_at": fields.Datetime.now(),
                "status_message": message,
            }
        )
        self.document_id._sync_state_from_requests()
        return True

    def action_sign_request(
        self,
        signer_name,
        signature_image,
        confirmation_ok=False,
        signer_vat=False,
        consent_values=None,
    ):
        self.ensure_one()
        self._check_kiosk_access()
        if self.state != "presented":
            raise UserError(_("La solicitud ya no está disponible para firmar."))
        if self.cancel_requested:
            raise UserError(_("La solicitud fue cancelada antes de confirmar la firma."))
        signer_name = self._sanitize_signer_name(signer_name)
        signer_vat = self._sanitize_signer_vat(signer_vat)
        consent_values = self._sanitize_consent_values(consent_values)
        self.document_id.action_register_signature(
            signer_name=signer_name,
            signature_image=signature_image,
            confirmation_ok=confirmation_ok,
            signer_vat=signer_vat,
            consent_values=consent_values,
        )
        self.write(
            {
                "state": "signed",
                "completed_at": fields.Datetime.now(),
                "status_message": _("Firma completada correctamente."),
            }
        )
        if self.kiosk_session_id:
            self.kiosk_session_id.touch(active_request_id=False)
        self.document_id._message_repair_order(
            _(
                "Solicitud %(request)s completada correctamente."
            )
            % {
                "request": self.name,
            }
        )
        return True

    def action_requeue_clean(self):
        self.ensure_one()
        if self.state == "signed":
            raise UserError(_("No se puede reenviar una solicitud ya firmada."))
        self.action_cancel_request()
        new_request = self.document_id.action_request_signature()
        return self.document_id.action_open_request_modal_for_request(new_request)
