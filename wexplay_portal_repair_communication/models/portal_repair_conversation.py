# -*- coding: utf-8 -*-

import logging
from datetime import date, datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.tools import plaintext2html

_logger = logging.getLogger(__name__)

_SLA_MINUTES = 60
_SLA_TZ = "Europe/Madrid"
_SLA_WINDOWS = [(time(10, 0), time(14, 0)), (time(16, 0), time(20, 0))]
_SLA_DAYS = {0, 1, 2, 3, 4}  # lunes–viernes


def _add_business_minutes(start_utc_naive, minutes):
    """Suma minutos de tiempo laborable a un datetime UTC naive.

    Horario: L-V, 10:00-14:00 y 16:00-20:00 (Europe/Madrid).
    Devuelve UTC naive.
    """
    tz = pytz.timezone(_SLA_TZ)
    dt = pytz.utc.localize(start_utc_naive).astimezone(tz)
    remaining = minutes
    safety = 0
    while remaining > 0 and safety < 200:
        safety += 1
        # Avanzar a día laborable
        while dt.weekday() not in _SLA_DAYS:
            dt = tz.localize(datetime.combine(dt.date() + timedelta(days=1), _SLA_WINDOWS[0][0]))

        # Buscar ventana actual o siguiente
        current_window = None
        for w_start, w_end in _SLA_WINDOWS:
            if dt.time() < w_start:
                dt = tz.localize(datetime.combine(dt.date(), w_start))
                current_window = (w_start, w_end)
                break
            if w_start <= dt.time() < w_end:
                current_window = (w_start, w_end)
                break

        if current_window is None:
            # Pasadas todas las ventanas de hoy → primer tramo del siguiente día laborable
            next_day = dt.date() + timedelta(days=1)
            dt = tz.localize(datetime.combine(next_day, _SLA_WINDOWS[0][0]))
            continue

        w_end_dt = tz.localize(datetime.combine(dt.date(), current_window[1]))
        minutes_in_window = int((w_end_dt - dt).total_seconds() / 60)

        if remaining <= minutes_in_window:
            dt += timedelta(minutes=remaining)
            remaining = 0
        else:
            remaining -= minutes_in_window
            # Avanzar a siguiente ventana
            next_window = next(
                (w for w in _SLA_WINDOWS if w[0] > current_window[1]), None
            )
            if next_window:
                dt = tz.localize(datetime.combine(dt.date(), next_window[0]))
            else:
                next_day = dt.date() + timedelta(days=1)
                dt = tz.localize(datetime.combine(next_day, _SLA_WINDOWS[0][0]))

    return dt.astimezone(pytz.utc).replace(tzinfo=None)


class WexPortalRepairConversation(models.Model):
    _name = "wex.portal.repair.conversation"
    _description = "SAT portal conversation"
    _order = "last_message_at desc, id desc"

    _sql_constraints = [
        (
            "wex_portal_repair_conversation_unique_repair",
            "unique(repair_id)",
            "Only one portal conversation can exist per SAT repair.",
        ),
    ]

    name = fields.Char(
        string="Conversation",
        compute="_compute_name",
        store=True,
    )
    repair_id = fields.Many2one(
        "repair.order",
        string="SAT",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="repair_id.company_id",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        ondelete="restrict",
        index=True,
    )
    commercial_partner_id = fields.Many2one(
        "res.partner",
        string="Empresa",
        compute="_compute_commercial_partner_id",
        store=True,
        readonly=True,
    )
    responsible_user_id = fields.Many2one(
        "res.users",
        string="Responsable actual",
        index=True,
    )
    operator_channel_id = fields.Many2one(
        "discuss.channel",
        string="Canal interno SAT",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    state = fields.Selection(
        [
            ("pending_customer_reply", "Pendiente respuesta"),
            ("answered", "Respondida"),
            ("no_response_needed", "No requiere contestación"),
        ],
        string="Estado conversación",
        default="answered",
        required=True,
        index=True,
    )
    last_customer_message_at = fields.Datetime(string="Último mensaje cliente")
    last_technician_message_at = fields.Datetime(string="Último mensaje técnico")
    last_message_at = fields.Datetime(string="Último movimiento", index=True)
    last_message_preview = fields.Char(string="Último mensaje")
    no_response_needed_at = fields.Datetime(string="Sin respuesta desde")
    no_response_needed_by_id = fields.Many2one(
        "res.users",
        string="Marcado por",
        readonly=True,
    )
    technician_last_read_at = fields.Datetime(
        string="Visto por técnico",
        readonly=True,
    )
    sla_deadline = fields.Datetime(
        string="Límite SLA",
        readonly=True,
        index=True,
    )
    sla_notified_at = fields.Datetime(
        string="SLA notificado",
        readonly=True,
    )
    sla_breached = fields.Boolean(
        string="SLA incumplido",
        compute="_compute_sla_breached",
        store=True,
    )
    message_ids = fields.One2many(
        "wex.portal.repair.message",
        "conversation_id",
        string="Mensajes",
    )
    message_count = fields.Integer(
        string="Mensajes",
        compute="_compute_message_count",
    )
    needs_response = fields.Boolean(
        string="Pendiente",
        compute="_compute_needs_response",
        search="_search_needs_response",
    )

    @api.depends("repair_id.name", "partner_id.name")
    def _compute_name(self):
        for conversation in self:
            repair_name = conversation.repair_id.name or _("SAT")
            partner_name = conversation.partner_id.display_name or _("Cliente")
            conversation.name = "%s · %s" % (repair_name, partner_name)

    @api.depends("partner_id")
    def _compute_commercial_partner_id(self):
        for conversation in self:
            conversation.commercial_partner_id = conversation.partner_id.commercial_partner_id

    @api.depends("message_ids")
    def _compute_message_count(self):
        for conversation in self:
            conversation.message_count = len(conversation.message_ids)

    @api.depends("state")
    def _compute_needs_response(self):
        for conversation in self:
            conversation.needs_response = conversation.state == "pending_customer_reply"

    @api.depends("sla_deadline", "sla_notified_at")
    def _compute_sla_breached(self):
        now = fields.Datetime.now()
        for conversation in self:
            conversation.sla_breached = bool(
                conversation.sla_deadline and conversation.sla_deadline <= now
            )

    def _search_needs_response(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            return []
        expected_state = "pending_customer_reply"
        if (operator == "=" and value) or (operator == "!=" and not value):
            return [("state", "=", expected_state)]
        return [("state", "!=", expected_state)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("repair_id") and not vals.get("responsible_user_id"):
                repair = self.env["repair.order"].browse(vals["repair_id"])
                vals["responsible_user_id"] = repair._resolve_portal_conversation_responsible_user().id
            if vals.get("partner_id") and not vals.get("commercial_partner_id"):
                partner = self.env["res.partner"].browse(vals["partner_id"])
                vals["commercial_partner_id"] = partner.commercial_partner_id.id
        return super().create(vals_list)

    def _prepare_message_vals(self, body, source, visible_to_customer=True):
        self.ensure_one()
        return {
            "conversation_id": self.id,
            "body": body,
            "source": source,
            "visible_to_customer": visible_to_customer,
        }

    def _post_operator_channel_note(self, body):
        self.ensure_one()
        if not (body or "").strip():
            return False
        channel = self._get_or_create_operator_channel()
        self._sync_operator_channel_members()
        channel.with_context(
            wex_portal_repair_skip_discuss_sync=True,
        ).sudo().message_post(
            author_id=self.env.user.partner_id.id if self.env.user.partner_id else False,
            body=plaintext2html(body, with_paragraph=False),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        return True

    def _get_expected_operator_partners(self):
        self.ensure_one()
        partners = self.env["res.partner"]
        if self.responsible_user_id.partner_id:
            partners |= self.responsible_user_id.partner_id
        return partners.filtered("active")

    def _prepare_operator_channel_name(self):
        self.ensure_one()
        repair_name = self.repair_id.name or _("SAT")
        partner_name = self.partner_id.display_name or _("Cliente")
        return _("%(repair)s · %(partner)s") % {
            "repair": repair_name,
            "partner": partner_name,
        }

    def _sync_operator_channel_members(self):
        for conversation in self:
            channel = conversation.operator_channel_id
            if not channel:
                continue
            expected_partners = conversation._get_expected_operator_partners()
            channel = channel.sudo()
            current_members = channel.channel_member_ids
            _logger.info(
                "SAT portal conversation %s syncing operator channel %s. Expected partners=%s, current partners=%s, acting user=%s.",
                conversation.id,
                channel.id,
                expected_partners.ids,
                current_members.partner_id.ids,
                self.env.user.partner_id.id if self.env.user.partner_id else False,
            )
            members_to_remove = current_members.filtered(
                lambda member: member.partner_id not in expected_partners
            )
            if members_to_remove:
                for member in members_to_remove:
                    member.write(
                        {
                            "custom_notifications": "no_notif",
                            "fold_state": "closed",
                            "unpin_dt": fields.Datetime.now(),
                        }
                    )
                    _logger.info(
                        "SAT portal conversation %s archived partner %s in operator channel %s instead of unlinking to avoid discuss UI race conditions.",
                        conversation.id,
                        member.partner_id.id if member.partner_id else False,
                        channel.id,
                    )
            members_to_activate = current_members.filtered(
                lambda member: member.partner_id in expected_partners
            )
            if members_to_activate:
                members_to_activate.write(
                    {
                        "custom_notifications": False,
                        "fold_state": "open",
                        "unpin_dt": False,
                        "last_interest_dt": fields.Datetime.now(),
                    }
                )
            existing_partner_ids = current_members.filtered(
                lambda member: member.partner_id in expected_partners
            ).partner_id.ids
            missing_partners = expected_partners.filtered(
                lambda partner: partner.id not in existing_partner_ids
            )
            if missing_partners:
                _logger.info(
                    "SAT portal conversation %s adding missing partners %s to operator channel %s.",
                    conversation.id,
                    missing_partners.ids,
                    channel.id,
                )
                channel.add_members(
                    partner_ids=missing_partners.ids,
                    open_chat_window=False,
                    post_joined_message=False,
                )
            channel.write(
                {
                    "name": conversation._prepare_operator_channel_name(),
                }
            )
            _logger.info(
                "SAT portal conversation %s finished sync for operator channel %s. Final partners=%s.",
                conversation.id,
                channel.id,
                channel.channel_member_ids.partner_id.ids,
            )

    def _handle_responsible_user_reassignment(self, previous_user, new_user):
        for conversation in self:
            if previous_user == new_user:
                continue
            _logger.info(
                "SAT portal conversation %s responsible reassignment on repair %s. Previous user=%s, new user=%s, acting user=%s.",
                conversation.id,
                conversation.repair_id.id,
                previous_user.id if previous_user else False,
                new_user.id if new_user else False,
                self.env.user.id,
            )
            conversation._sync_operator_channel_members()
            if new_user:
                conversation._post_operator_channel_note(
                    _(
                        "Responsable SAT actualizado a %(user)s."
                    )
                    % {"user": new_user.display_name},
                )
                if conversation.state == "pending_customer_reply":
                    conversation._open_operator_channel_for_user(new_user)

    def _get_or_create_operator_channel(self):
        self.ensure_one()
        expected_partners = self._get_expected_operator_partners()
        channel = self.operator_channel_id
        if channel:
            self._sync_operator_channel_members()
            return channel

        create_vals = {
            "name": self._prepare_operator_channel_name(),
            "channel_type": "group",
            "channel_member_ids": [
                (0, 0, {"partner_id": partner.id})
                for partner in expected_partners
            ],
            "x_wex_portal_repair_conversation_id": self.id,
        }
        channel = (
            self.env["discuss.channel"]
            .with_context(install_mode=True)
            .sudo()
            .create(create_vals)
        )
        self.sudo().write({"operator_channel_id": channel.id})
        return channel

    def _ensure_operator_channel_for_user(self, user):
        self.ensure_one()
        if not user or not user.partner_id:
            return self.env["discuss.channel"]
        channel = self._get_or_create_operator_channel()
        self._sync_operator_channel_members()
        if not channel.channel_member_ids.filtered(lambda member: member.partner_id == user.partner_id):
            channel.sudo().add_members(
                partner_ids=user.partner_id.ids,
                open_chat_window=False,
                post_joined_message=False,
            )
        member = self.env["discuss.channel.member"].sudo().search(
            [
                ("channel_id", "=", channel.id),
                ("partner_id", "=", user.partner_id.id),
            ],
            limit=1,
        )
        if member:
            member.write(
                {
                    "fold_state": "open",
                    "unpin_dt": False,
                    "last_interest_dt": fields.Datetime.now(),
                }
            )
        return channel

    def _open_operator_channel_for_user(self, user):
        self.ensure_one()
        channel = self._ensure_operator_channel_for_user(user)
        if not channel:
            return
        user._bus_send(
            "wex.portal_repair/operator_chat",
            {
                "channel_id": channel.id,
                "repair_id": self.repair_id.id,
                "conversation_id": self.id,
            },
        )

    def _prepare_operator_channel_post_values(self, message):
        self.ensure_one()
        author_partner = message.author_partner_id or self.partner_id
        return {
            "author_id": author_partner.id if author_partner else False,
            "body": plaintext2html(message.body or "", with_paragraph=False),
            "message_type": "comment",
            "subtype_xmlid": "mail.mt_comment",
        }

    def _post_message_to_operator_channel(self, message, skip_open=False):
        for conversation in self:
            channel = conversation._get_or_create_operator_channel()
            channel.with_context(
                wex_portal_repair_skip_discuss_sync=True,
            ).sudo().message_post(
                **conversation._prepare_operator_channel_post_values(message)
            )
            if message.source == "portal_customer" and not skip_open:
                conversation._open_operator_channel_for_user(conversation.responsible_user_id)

    def action_open_repair(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("SAT"),
            "res_model": "repair.order",
            "res_id": self.repair_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_reply_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Responder al cliente"),
            "res_model": "wex.portal.repair.reply.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_conversation_id": self.id,
            },
        }

    def action_mark_no_response_needed(self):
        self.ensure_one()
        self.write(
            {
                "state": "no_response_needed",
                "no_response_needed_at": fields.Datetime.now(),
                "no_response_needed_by_id": self.env.user.id,
            }
        )
        return True

    def action_open_operator_chat(self):
        self.ensure_one()
        self.sudo().write({"technician_last_read_at": fields.Datetime.now()})
        self._open_operator_channel_for_user(self.env.user)
        return False

    def get_operator_chat_thread_data(self):
        self.ensure_one()
        self.sudo().write({"technician_last_read_at": fields.Datetime.now()})
        channel = self._ensure_operator_channel_for_user(self.env.user)
        return {
            "id": channel.id,
            "model": "discuss.channel",
        }

    def get_operator_chat_sidebar_values(self):
        self.ensure_one()
        return self.repair_id._get_portal_chat_sidebar_values()

    def _set_sla_deadline(self):
        for conversation in self:
            deadline = _add_business_minutes(fields.Datetime.now(), _SLA_MINUTES)
            conversation.sudo().write({
                "sla_deadline": deadline,
                "sla_notified_at": False,
            })

    def _clear_sla(self):
        for conversation in self:
            conversation.sudo().write({
                "sla_deadline": False,
                "sla_notified_at": False,
            })

    @api.model
    def _cron_check_sla(self):
        now = fields.Datetime.now()
        pending = self.search([
            ("state", "=", "pending_customer_reply"),
            ("sla_deadline", "<=", now),
            ("sla_notified_at", "=", False),
            ("responsible_user_id", "!=", False),
        ])
        for conversation in pending:
            try:
                conversation._notify_sla_breach()
            except Exception:
                _logger.exception(
                    "SLA check failed for conversation %s (repair %s).",
                    conversation.id,
                    conversation.repair_id.id,
                )

    def _notify_sla_breach(self):
        self.ensure_one()
        responsible = self.responsible_user_id
        if not responsible:
            return
        self.sudo().write({"sla_notified_at": fields.Datetime.now()})

        repair = self.repair_id
        repair.sudo().message_notify(
            partner_ids=[responsible.partner_id.id],
            subject=_("SLA vencido — %s") % (repair.name or _("SAT")),
            body=_(
                "El cliente lleva más de 1 hora de horario laboral sin recibir respuesta "
                "en la reparación %s. Por favor atiende la conversación."
            ) % (repair.name or ""),
        )

        self._open_operator_channel_for_user(responsible)

        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if activity_type and repair:
            self.env["mail.activity"].sudo().create({
                "res_model_id": self.env["ir.model"]._get_id("repair.order"),
                "res_id": repair.id,
                "activity_type_id": activity_type.id,
                "summary": _("SLA vencido — cliente sin respuesta"),
                "user_id": responsible.id,
                "note": _(
                    "Han pasado más de 1 hora de horario laboral sin respuesta al cliente "
                    "en la conversación portal de este SAT."
                ),
            })
