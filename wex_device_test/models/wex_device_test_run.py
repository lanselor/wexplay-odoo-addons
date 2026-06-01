import secrets
import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WexDeviceTestRun(models.Model):
    _name = "wex.device.test.run"
    _description = "Wex Device Test Run"
    _order = "started_at desc, id desc"

    ACTIVE_STATES = ("pending_pairing", "paired", "in_progress")

    name = fields.Char(required=True, readonly=True)
    repair_order_id = fields.Many2one(
        "repair.order",
        required=True,
        ondelete="cascade",
        index=True,
    )
    session_id = fields.Many2one(
        "wex.device.test.session",
        readonly=True,
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Technician",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("pending_pairing", "Pending Pairing"),
            ("paired", "Paired"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="pending_pairing",
        readonly=True,
    )
    pairing_token = fields.Char(required=True, readonly=True, copy=False, index=True)
    pairing_code = fields.Char(required=True, readonly=True, copy=False, index=True)
    started_at = fields.Datetime(required=True, readonly=True)
    paired_at = fields.Datetime(readonly=True)
    completed_at = fields.Datetime(readonly=True)
    cancelled_at = fields.Datetime(readonly=True)
    last_message = fields.Char(readonly=True)
    show_pairing_token = fields.Boolean(default=False)
    result_ids = fields.One2many("wex.device.test.result", "run_id", readonly=True)
    log_ids = fields.One2many("wex.device.test.log", "run_id", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        readonly=True,
    )

    @api.model
    def _prepare_run_name(self, repair_order):
        return "Test Run - %s" % (repair_order.display_name or repair_order.name)

    @api.model
    def _generate_pairing_token(self):
        return secrets.token_urlsafe(24)

    @api.model
    def _generate_pairing_code(self):
        return secrets.token_hex(3).upper()

    @api.model
    def _get_active_states(self):
        return self.ACTIVE_STATES

    def _can_start_pairing(self):
        self.ensure_one()
        return True

    def _can_receive_results(self):
        self.ensure_one()
        return self.state in ("paired", "in_progress")

    def _is_pairable(self):
        self.ensure_one()
        return self.state == "pending_pairing"

    def _check_pairing_token(self, pairing_token):
        self.ensure_one()
        return bool(pairing_token and pairing_token.strip() == self.pairing_token)

    def _check_pairing_code(self, pairing_code):
        self.ensure_one()
        return bool(pairing_code and pairing_code.strip().upper() == self.pairing_code)

    def _check_can_create_run(self):
        self.ensure_one()
        active_run = self.search(
            [
                ("repair_order_id", "=", self.repair_order_id.id),
                ("state", "in", self._get_active_states()),
                ("id", "!=", self.id),
            ],
            limit=1,
        )
        return not active_run

    def _mark_as_paired(self, session, message=None):
        self.ensure_one()
        values = {
            "session_id": session.id,
            "state": "paired",
            "paired_at": fields.Datetime.now(),
        }
        if message:
            values["last_message"] = message
        self.write(values)
        return self

    def _mark_as_in_progress(self, message=None):
        self.ensure_one()
        values = {"state": "in_progress"}
        if message:
            values["last_message"] = message
        self.write(values)
        return self

    def _mark_as_completed(self, message=None):
        self.ensure_one()
        values = {
            "state": "completed",
            "completed_at": fields.Datetime.now(),
        }
        if message:
            values["last_message"] = message
        self.write(values)
        return self

    def _prepare_run_response_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "pairing_code": self.pairing_code,
            "repair_order_id": self.repair_order_id.id,
            "repair_order_name": self.repair_order_id.display_name,
        }

    def _prepare_pairing_qr_payload(self, base_url):
        self.ensure_one()
        return json.dumps(
            {
                "type": "wex_device_test_pairing",
                "version": 1,
                "base_url": base_url,
                "pairing_token": self.pairing_token,
                "pairing_code": self.pairing_code,
                "repair_order_ref": self.repair_order_id.display_name,
                "run_id": self.id,
            },
            separators=(",", ":"),
        )

    @api.model
    def _get_pairing_domain(self, pairing_token=None, pairing_code=None, run_id=None, company=None):
        domain = []
        if company:
            domain.append(("company_id", "=", company.id))
        if run_id:
            domain.append(("id", "=", run_id))
        if pairing_token:
            domain.append(("pairing_token", "=", pairing_token.strip()))
            return domain
        if pairing_code:
            domain.append(("pairing_code", "=", pairing_code.strip().upper()))
        return domain

    @api.model
    def find_pairable_run(self, pairing_token=None, pairing_code=None, run_id=None, company=None):
        domain = self._get_pairing_domain(
            pairing_token=pairing_token,
            pairing_code=pairing_code,
            run_id=run_id,
            company=company,
        )
        if not domain:
            return self.browse()
        return self.search(domain, limit=1)

    def pair_with_session(self, session, message=None):
        self.ensure_one()
        if not self._is_pairable():
            raise ValidationError("This run is no longer available for pairing.")
        if self.company_id != session.company_id:
            raise ValidationError("Run and session company mismatch.")
        return self._mark_as_paired(
            session,
            message=message or "Run paired successfully.",
        )

    def _get_open_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Device Test Run",
            "res_model": "wex.device.test.run",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            repair_order = self.env["repair.order"].browse(vals["repair_order_id"])
            vals.setdefault("name", self._prepare_run_name(repair_order))
            vals.setdefault("pairing_token", self._generate_pairing_token())
            vals.setdefault("pairing_code", self._generate_pairing_code())
            vals.setdefault("started_at", now)
            vals.setdefault("company_id", repair_order.company_id.id or self.env.company.id)
        runs = super().create(vals_list)
        for run in runs:
            if not run._check_can_create_run():
                raise ValidationError(
                    "There is already an active device test run for this repair order."
                )
        return runs

    def action_start_pairing(self):
        for run in self:
            if not run._can_start_pairing():
                continue
            run.write(
                {
                    "state": "pending_pairing",
                    "pairing_token": run._generate_pairing_token(),
                    "pairing_code": run._generate_pairing_code(),
                    "started_at": fields.Datetime.now(),
                    "paired_at": False,
                    "completed_at": False,
                    "cancelled_at": False,
                    "last_message": "Waiting for the Android app to pair with this run.",
                    "session_id": False,
                }
            )

    def action_cancel_pairing(self):
        self.write(
            {
                "state": "cancelled",
                "cancelled_at": fields.Datetime.now(),
                "last_message": "Pairing cancelled from Odoo.",
            }
        )

    def action_mark_completed(self):
        for run in self:
            run._mark_as_completed(message="Run completed from Odoo.")

    def action_show_pairing_token(self):
        self.write({"show_pairing_token": True})

    def action_hide_pairing_token(self):
        self.write({"show_pairing_token": False})
