# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_amount, format_date, format_datetime, html2plaintext


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_portal_conversation_id = fields.Many2one(
        "wex.portal.repair.conversation",
        string="Conversación portal",
        compute="_compute_portal_conversation_fields",
    )
    x_portal_conversation_state = fields.Selection(
        related="x_portal_conversation_id.state",
        readonly=True,
    )
    x_portal_conversation_message_count = fields.Integer(
        string="Mensajes portal",
        compute="_compute_portal_conversation_fields",
    )
    def _compute_portal_conversation_fields(self):
        conversation_model = self.env["wex.portal.repair.conversation"]
        mapping = {
            conversation.repair_id.id: conversation
            for conversation in conversation_model.search([("repair_id", "in", self.ids)])
        }
        for repair in self:
            conversation = mapping.get(repair.id)
            repair.x_portal_conversation_id = conversation
            repair.x_portal_conversation_message_count = conversation.message_count if conversation else 0

    def _get_portal_conversation(self):
        self.ensure_one()
        return self.env["wex.portal.repair.conversation"].sudo().search(
            [("repair_id", "=", self.id)],
            limit=1,
        )

    def _get_or_create_portal_conversation(self):
        self.ensure_one()
        conversation = self._get_portal_conversation()
        if conversation:
            if conversation.responsible_user_id != self._resolve_portal_conversation_responsible_user():
                conversation.write(
                    {"responsible_user_id": self._resolve_portal_conversation_responsible_user().id}
                )
            return conversation
        return self.env["wex.portal.repair.conversation"].sudo().create(
            {
                "repair_id": self.id,
                "partner_id": self.partner_id.commercial_partner_id.id,
                "responsible_user_id": self._resolve_portal_conversation_responsible_user().id,
            }
        )

    def _resolve_portal_conversation_responsible_user(self):
        self.ensure_one()
        if self.user_id:
            return self.user_id

        reception_manager_user = self._get_portal_conversation_reception_manager_user()
        if reception_manager_user:
            return reception_manager_user

        return self.env.ref("base.user_admin")

    def _get_portal_conversation_reception_manager_user(self):
        self.ensure_one()
        reception_employee = getattr(self, "x_reception_employee_id", False)
        if reception_employee and reception_employee.parent_id and reception_employee.parent_id.user_id:
            return reception_employee.parent_id.user_id
        return self.env["res.users"]

    def _sync_portal_conversation_responsible_user(self):
        for repair in self:
            conversation = repair._get_portal_conversation()
            if conversation:
                previous_user = conversation.responsible_user_id
                new_user = repair._resolve_portal_conversation_responsible_user()
                conversation.write(
                    {
                        "responsible_user_id": new_user.id,
                    }
                )
                conversation._handle_responsible_user_reassignment(previous_user, new_user)

    def _can_portal_customer_write_conversation(self):
        self.ensure_one()
        is_active_sat = False
        if hasattr(self, "_is_portal_repair_active"):
            is_active_sat = bool(self._is_portal_repair_active())

        has_valid_warranty = False
        if "x_is_any_warranty_valid" in self._fields:
            has_valid_warranty = bool(self.x_is_any_warranty_valid)

        return is_active_sat or has_valid_warranty

    def _portal_post_customer_conversation_message(self, body):
        self.ensure_one()
        if not self._can_portal_user_access(self.env.user):
            raise UserError(_("No tienes acceso a esta reparación."))
        if not self._can_portal_customer_write_conversation():
            raise UserError(_("Esta conversación ya no admite respuestas del cliente."))

        conversation = self.sudo()._get_or_create_portal_conversation()
        portal_user = self.env.user
        portal_partner = portal_user.partner_id.commercial_partner_id
        self.env["wex.portal.repair.message"].sudo().create(
            {
                "conversation_id": conversation.id,
                "body": body,
                "source": "portal_customer",
                "visible_to_customer": True,
                "author_user_id": portal_user.id,
                "author_partner_id": portal_partner.id,
                "author_name": portal_partner.display_name,
            }
        )
        return conversation

    def _notify_responsible_about_portal_message(self, message):
        self.ensure_one()
        responsible_user = message.conversation_id.responsible_user_id
        if not responsible_user:
            return

        if hasattr(self, "message_notify") and responsible_user.partner_id:
            self.sudo().message_notify(
                partner_ids=[responsible_user.partner_id.id],
                subject=_("Nuevo mensaje portal en %s") % (self.name or _("SAT")),
                body=_(
                    "El cliente ha escrito desde el portal sobre la reparación %s."
                )
                % (self.name or ""),
            )

    def _get_portal_conversation_message_values(self, customer_view=False):
        self.ensure_one()
        conversation = self._get_portal_conversation()
        if not conversation:
            return []

        messages = conversation.message_ids
        if customer_view:
            messages = messages.filtered(lambda msg: msg.visible_to_customer)

        values = []
        last_date = False
        for message in messages:
            local_dt = fields.Datetime.context_timestamp(self, message.create_date)
            message_date = local_dt.date()
            if message_date != last_date:
                last_date = message_date
                values.append(
                    {
                        "type": "date_separator",
                        "label": self._get_portal_conversation_date_label(message_date),
                    }
                )
            values.append(
                {
                    "type": "message",
                    "id": message.id,
                    "author_name": message.author_name or _("Usuario"),
                    "body": message.body or "",
                    "created_at": message.create_date,
                    "created_at_label": local_dt.strftime("%d/%m/%Y %H:%M"),
                    "source": message.source,
                    "is_customer": message.source == "portal_customer",
                    "is_technician": message.source == "technician",
                }
            )
        return values

    def _get_portal_conversation_date_label(self, message_date):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if message_date == today:
            return _("Hoy")
        return format_date(self.env, message_date)

    def _get_portal_conversation_responsible_employee(self, user):
        self.ensure_one()
        if not user:
            return self.env["hr.employee"]
        employee = getattr(user, "employee_id", False)
        if employee:
            return employee
        return self.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)

    def _get_portal_conversation_responsible_avatar_values(self, conversation):
        self.ensure_one()
        user = conversation.responsible_user_id if conversation else self.env["res.users"]
        if not user:
            return {
                "responsible_avatar_url": "",
                "responsible_initial": "",
            }
        employee = self._get_portal_conversation_responsible_employee(user)
        if employee:
            avatar_url = "/web/image/hr.employee/%s/avatar_128" % employee.id
        else:
            avatar_url = "/web/image/res.users/%s/avatar_128" % user.id
        return {
            "responsible_avatar_url": avatar_url,
            "responsible_initial": (user.display_name or "?")[:1].upper(),
        }

    def _get_portal_repair_conversation_values(self, customer_view=True):
        self.ensure_one()
        conversation = self._get_portal_conversation()
        last_message = conversation.message_ids[-1] if conversation and conversation.message_ids else self.env[
            "wex.portal.repair.message"
        ]
        responsible_avatar_values = self._get_portal_conversation_responsible_avatar_values(
            conversation
        )
        is_active_sat = bool(
            hasattr(self, "_is_portal_repair_active") and self._is_portal_repair_active()
        )
        has_valid_warranty = bool(
            "x_is_any_warranty_valid" in self._fields and self.x_is_any_warranty_valid
        )
        can_customer_write = self._can_portal_customer_write_conversation()
        return {
            "exists": bool(conversation),
            "conversation_id": conversation.id if conversation else False,
            "state": conversation.state if conversation else "answered",
            "state_label": dict(conversation._fields["state"].selection).get(
                conversation.state, conversation.state
            )
            if conversation
            else _("Sin mensajes"),
            "message_count": conversation.message_count if conversation else 0,
            "can_customer_write": can_customer_write,
            "messages": self._get_portal_conversation_message_values(customer_view=customer_view),
            "last_message_id": last_message.id if last_message else False,
            "last_message_date": last_message.create_date.isoformat() if last_message else "",
            "responsible_name": conversation.responsible_user_id.display_name if conversation and conversation.responsible_user_id else "",
            "responsible_avatar_url": responsible_avatar_values["responsible_avatar_url"],
            "responsible_initial": responsible_avatar_values["responsible_initial"],
            "status_badge_class": self._get_portal_conversation_status_badge_class(
                conversation.state if conversation else "answered"
            ),
            "entry_message": self._get_portal_conversation_entry_message(
                can_customer_write=can_customer_write,
                is_active_sat=is_active_sat,
                has_valid_warranty=has_valid_warranty,
            ),
            "availability_message": self._get_portal_conversation_availability_message(
                can_customer_write=can_customer_write,
                is_active_sat=is_active_sat,
                has_valid_warranty=has_valid_warranty,
            ),
            "technician_read_label": self._get_portal_conversation_technician_read_label(conversation),
        }

    def _get_portal_conversation_status_badge_class(self, state):
        self.ensure_one()
        mapping = {
            "pending_customer_reply": "is-pending",
            "answered": "is-answered",
            "no_response_needed": "is-muted",
        }
        return mapping.get(state, "is-muted")

    def _get_portal_conversation_technician_read_label(self, conversation):
        self.ensure_one()
        if not conversation or not conversation.technician_last_read_at:
            return ""
        last_customer_msg_at = conversation.last_customer_message_at
        if not last_customer_msg_at:
            return ""
        if conversation.technician_last_read_at < last_customer_msg_at:
            return ""
        return format_datetime(self.env, conversation.technician_last_read_at, dt_format="d MMM, HH:mm")

    def _get_portal_conversation_entry_message(
        self, can_customer_write=False, is_active_sat=False, has_valid_warranty=False
    ):
        self.ensure_one()
        if can_customer_write and is_active_sat:
            return _("Tu SAT sigue en curso. Puedes escribir directamente a tu técnico.")
        if can_customer_write and has_valid_warranty:
            return _(
                "El SAT ya está cerrado, pero la garantía sigue vigente y puedes escribirnos desde aquí."
            )
        return _(
            "Este canal queda vinculado a esta reparación para que el seguimiento sea claro y ordenado."
        )

    def _get_portal_conversation_availability_message(
        self, can_customer_write=False, is_active_sat=False, has_valid_warranty=False
    ):
        self.ensure_one()
        if can_customer_write:
            return _(
                "Tu mensaje quedará asociado a este SAT y llegará al técnico responsable."
            )
        if not is_active_sat and not has_valid_warranty:
            return _(
                "La conversación ya no admite mensajes del cliente porque el SAT está finalizado y fuera de garantía."
            )
        return _("La conversación no admite mensajes del cliente en este momento.")

    def get_portal_repair_conversation_values(self):
        self.ensure_one()
        return self._get_portal_repair_conversation_values(customer_view=False)

    def action_open_portal_operator_chat(self):
        self.ensure_one()
        conversation = self._get_or_create_portal_conversation()
        return conversation.get_operator_chat_thread_data()

    def _get_portal_chat_device_label(self):
        self.ensure_one()
        values = []
        if hasattr(self, "_get_portal_brand_label"):
            values.append(self._get_portal_brand_label())
        if hasattr(self, "_get_portal_model_label"):
            values.append(self._get_portal_model_label())
        device_label = " / ".join(value for value in values if value)
        if device_label:
            return device_label
        if hasattr(self, "_get_portal_product_label"):
            device_label = self._get_portal_product_label()
            if device_label:
                return device_label
        if hasattr(self, "_get_portal_device_type_label"):
            device_label = self._get_portal_device_type_label()
            if device_label:
                return device_label
        return getattr(self, "x_device_description", False) or ""

    def _get_portal_chat_budget_summary(self):
        self.ensure_one()
        repair = self.sudo()
        budget_stage = getattr(repair, "x_budget_stage", False) or ""
        if not budget_stage and not repair.sale_order_id:
            return {}

        status_label = ""
        status_message = ""
        if hasattr(repair, "_get_portal_budget_status_values"):
            status_values = repair._get_portal_budget_status_values()
            status_label = status_values.get("label", "")
            status_message = status_values.get("message", "")
        elif hasattr(repair, "_get_budget_stage_label") and budget_stage:
            status_label = repair._get_budget_stage_label(budget_stage)

        sale_order = repair.sale_order_id.sudo()
        currency = (
            sale_order.currency_id
            or getattr(repair, "x_sat_currency_id", False)
            or repair.company_id.currency_id
        )
        amount_total = sale_order.amount_total if sale_order else getattr(
            repair, "x_sat_total_amount", 0.0
        )
        return {
            "label": status_label,
            "message": status_message,
            "amount_total_label": (
                format_amount(self.env, amount_total, currency) if currency else ""
            ),
        }

    def _get_portal_chat_warranty_summary(self):
        self.ensure_one()
        if "x_warranty_status" not in self._fields:
            return {}

        repair = self.sudo()
        is_active_sat = bool(
            hasattr(repair, "_is_portal_repair_active") and repair._is_portal_repair_active()
        )
        if is_active_sat:
            return {
                "label": _("No aplicable"),
                "is_valid": False,
            }

        label = dict(repair._fields["x_warranty_status"].selection).get(
            repair.x_warranty_status,
            repair.x_warranty_status or "",
        )
        if not label:
            return {}
        return {
            "label": label,
            "is_valid": bool(getattr(repair, "x_is_any_warranty_valid", False)),
        }

    def _get_portal_chat_repair_notes(self):
        self.ensure_one()
        repair = self.sudo()
        raw_notes = repair.internal_notes or getattr(repair, "x_internal_notes", False) or ""
        return html2plaintext(raw_notes).strip() if raw_notes else ""

    def action_open_portal_chat_schedule_activity(self):
        self.ensure_one()
        return {
            "name": _("Programar actividad"),
            "type": "ir.actions.act_window",
            "res_model": "mail.activity.schedule",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "active_id": self.id,
                "active_ids": [self.id],
                "active_model": "repair.order",
                "default_res_model": "repair.order",
                "default_res_ids": str([self.id]),
                "default_activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "default_summary": _("Seguimiento SAT portal"),
            },
        }

    def _get_portal_chat_sidebar_values(self):
        self.ensure_one()
        repair = self.sudo()
        responsible_name = repair.user_id.display_name if repair.user_id else ""
        return {
            "enabled": True,
            "repair_id": repair.id,
            "repair_name": repair.name or _("SAT"),
            "partner_id": repair.partner_id.id,
            "customer_name": repair.partner_id.display_name or "",
            "customer_reference": getattr(repair, "x_customer_reference", False) or "",
            "responsible_name": responsible_name,
            "status_label": repair._get_portal_status_label() if hasattr(repair, "_get_portal_status_label") else "",
            "device_label": repair._get_portal_chat_device_label(),
            "serial_number": getattr(repair, "x_imei", False) or "",
            "device_description": getattr(repair, "x_device_description", False) or "",
            "reported_issue": getattr(repair, "x_reported_issue", False) or "",
            "repair_notes": repair._get_portal_chat_repair_notes(),
            "budget_summary": repair._get_portal_chat_budget_summary(),
            "warranty_summary": repair._get_portal_chat_warranty_summary(),
        }

    def action_open_or_create_portal_conversation(self):
        self.ensure_one()
        conversation = self._get_or_create_portal_conversation()
        return {
            "type": "ir.actions.act_window",
            "name": _("Conversación SAT"),
            "res_model": "wex.portal.repair.conversation",
            "res_id": conversation.id,
            "view_mode": "form",
            "target": "current",
        }

    def write(self, vals):
        result = super().write(vals)
        if "user_id" in vals:
            self._sync_portal_conversation_responsible_user()
        return result
