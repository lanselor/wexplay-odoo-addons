# -*- coding: utf-8 -*-

import uuid

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class WexConsentKioskSession(models.Model):
    _name = "wex.consent.kiosk.session"
    _description = "Sesión de kiosko de consentimientos"
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
        inverse="_inverse_reception_legal_text",
    )

    _sql_constraints = [
        ("wex_consent_kiosk_session_token_uniq", "unique(access_token)", "The kiosk token must be unique."),
    ]

    @api.model
    def _check_kiosk_access(self):
        if not (
            self.env.user.has_group("wex_consent.group_wex_consent_kiosk")
            or self.env.user.has_group("wex_consent.group_wex_consent_manager")
        ):
            raise AccessError(_("No tienes permisos para operar el modo kiosko."))

    @api.model
    def _check_company_access(self, company):
        if company not in self.env.companies:
            raise AccessError(_("No tienes acceso a la compañía solicitada."))

    @api.depends_context("uid")
    def _compute_reception_legal_text(self):
        legal_text = (
            self.env["ir.config_parameter"].sudo().get_param(
                "wex_consent.reception_legal_text"
            )
            or self._get_default_reception_legal_text()
        )
        for rec in self:
            rec.reception_legal_text = legal_text

    def _inverse_reception_legal_text(self):
        for rec in self:
            self.env["ir.config_parameter"].sudo().set_param(
                "wex_consent.reception_legal_text",
                rec.reception_legal_text or self._get_default_reception_legal_text(),
            )

    @api.model
    def _get_default_reception_legal_text(self):
        return (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
            "nisi ut aliquip ex ea commodo consequat."
        )

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
        values = {
            "state": "online",
            "last_seen_at": fields.Datetime.now(),
        }
        if active_request_id is not False:
            values["active_request_id"] = active_request_id
        self.write(values)
        return True
