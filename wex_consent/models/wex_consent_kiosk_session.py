# -*- coding: utf-8 -*-

import uuid
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class WexConsentKioskSession(models.Model):
    _name = "wex.consent.kiosk.session"
    _description = "Sesión de kiosko de consentimientos"
    _inherit = ["wex.consent.kiosk.access.mixin"]
    _order = "company_id, name"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        [
            ("online", "En línea"),
            ("offline", "Sin conexión"),
        ],
        default="offline",
        required=True,
    )
    access_token = fields.Char(
        default=lambda self: str(uuid.uuid4()),
        required=True,
        copy=False,
    )
    is_active = fields.Boolean(default=True)
    last_seen_at = fields.Datetime(readonly=True)
    active_request_id = fields.Many2one(
        comodel_name="wex.consent.request",
        string="Solicitud activa",
        readonly=True,
        copy=False,
    )
    reception_legal_text = fields.Text(
        compute="_compute_reception_legal_text",
        readonly=True,
    )

    _sql_constraints = [
        ("wex_consent_kiosk_session_token_uniq", "unique(access_token)", "The kiosk token must be unique."),
    ]

    _TOUCH_THROTTLE_SECONDS = 10

    @api.model
    def _check_company_access(self, company):
        if company not in self.env.companies:
            raise AccessError(_("No tienes acceso a la compañía solicitada."))

    @api.depends("company_id", "company_id.x_wex_consent_reception_legal_text")
    def _compute_reception_legal_text(self):
        for rec in self:
            rec.reception_legal_text = rec.company_id.x_wex_consent_reception_legal_text

    @api.model
    def get_default_session(self, company_id=None):
        self._check_kiosk_access()
        company = self.env["res.company"].browse(company_id) if company_id else self.env.company
        if company_id:
            self._check_company_access(company)
        session = self.search(
            [("company_id", "=", company.id), ("is_active", "=", True)],
            order="id asc",
            limit=1,
        )
        if not session:
            session = self.create(
                {
                    "name": "Kiosko SAT principal",
                    "company_id": company.id,
                }
            )
        return session

    def action_open_kiosk(self):
        self.ensure_one()
        self._check_kiosk_access()
        return {
            "type": "ir.actions.act_url",
            "url": "/wex_consent/kiosk",
            "target": "self",
        }

    @api.model
    def action_open_default_kiosk(self):
        session = self.get_default_session()
        return session.action_open_kiosk()

    @api.model
    def get_default_session_id(self):
        self._check_kiosk_access()
        return self.get_default_session().id

    @api.model
    def action_open_default_kiosk_configuration(self):
        self._check_kiosk_access()
        session = self.get_default_session()
        return {
            "type": "ir.actions.act_window",
            "name": "Configuración kiosko",
            "res_model": "wex.consent.kiosk.session",
            "res_id": session.id,
            "view_mode": "form",
            "target": "current",
        }

    def touch(self, active_request_id=False):
        self._check_kiosk_access()
        now = fields.Datetime.now()
        for session in self:
            values = {}
            if session.state != "online":
                values["state"] = "online"
            if (
                not session.last_seen_at
                or now - session.last_seen_at >= timedelta(seconds=self._TOUCH_THROTTLE_SECONDS)
            ):
                values["last_seen_at"] = now
            if active_request_id is not False and session.active_request_id.id != active_request_id:
                values["active_request_id"] = active_request_id
            if values:
                session.write(values)
        return True
