# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import _, api, fields, models


class WexPortalDashboard(models.AbstractModel):
    _name = "wex.portal.dashboard"
    _description = "Dashboard interno del portal Wexplay"

    @api.model
    def get_dashboard_data(self, period_days=7):
        period_days = self._sanitize_period_days(period_days)
        period = self._get_dashboard_period_values(period_days)
        return {
            "title": _("Portal clientes"),
            "subtitle": _(
                "Seguimiento interno de actividad, presupuestos y señales operativas del portal."
            ),
            "period_days": period_days,
            "period_options": self._get_period_options(period_days),
            "generated_at": fields.Datetime.now(),
            "attention_cards": self._get_attention_cards(period),
            "summary_cards": self._get_summary_cards(period),
            "conversation_cards": self._get_conversation_cards(period),
            "activity_preview": self._get_activity_preview(),
            "quick_actions": self._get_quick_actions(period),
        }

    @api.model
    def _sanitize_period_days(self, period_days):
        try:
            period_days = int(period_days)
        except (TypeError, ValueError):
            period_days = 7
        return period_days if period_days in (1, 7, 30, 90) else 7

    @api.model
    def _get_period_options(self, selected_days):
        options = []
        for days, label in ((1, _("Hoy")), (7, _("7 días")), (30, _("30 días")), (90, _("90 días"))):
            options.append(
                {
                    "days": days,
                    "label": label,
                    "is_selected": days == selected_days,
                }
            )
        return options

    @api.model
    def _get_dashboard_period_values(self, period_days):
        now = fields.Datetime.now()
        period_start = now - timedelta(days=period_days)
        today_start = fields.Datetime.to_datetime(
            fields.Date.to_string(fields.Date.context_today(self))
        )
        return {
            "now": now,
            "period_days": period_days,
            "period_start": period_start,
            "today_start": today_start,
        }

    @api.model
    def _get_action_dict(
        self,
        name,
        res_model,
        domain=None,
        view_mode="list,form",
        target="current",
        context=None,
    ):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": res_model,
            "view_mode": view_mode,
            "views": self._get_action_views(view_mode),
            "target": target,
            "domain": domain or [],
            "context": context or {},
        }

    @api.model
    def _get_action_views(self, view_mode):
        return [(False, mode.strip()) for mode in (view_mode or "list,form").split(",") if mode.strip()]

    @api.model
    def _make_metric_card(self, title, value, helper, action=None, tone="neutral", icon="fa fa-info-circle"):
        return {
            "title": title,
            "value": value,
            "helper": helper,
            "action": action,
            "tone": tone,
            "icon": icon,
        }

    @api.model
    def _get_event_icon(self, event_type):
        return {
            "budget_viewed": "fa fa-eye",
            "budget_accepted": "fa fa-check",
            "budget_rejected": "fa fa-times",
            "report_downloaded": "fa fa-download",
        }.get(event_type, "fa fa-bell")

    @api.model
    def _get_portal_enabled_commercial_partner_ids(self):
        portal_users = self.env["res.users"].search(
            [
                ("active", "=", True),
                ("groups_id", "in", self.env.ref("base.group_portal").ids),
            ]
        )
        return portal_users.mapped("partner_id.commercial_partner_id").ids

    @api.model
    def _get_portal_enabled_active_repair_domain(self):
        repair_model = self.env["repair.order"]
        commercial_partner_ids = self._get_portal_enabled_commercial_partner_ids()
        if not commercial_partner_ids:
            return [("id", "=", False)]
        return [
            ("partner_id", "child_of", commercial_partner_ids),
            ("state", "not in", repair_model._get_portal_done_states()),
        ]

    @api.model
    def _get_attention_cards(self, period):
        event_model = self.env["wex.portal.repair.event"]
        repair_model = self.env["repair.order"]
        waiting_domain = [("x_budget_stage", "=", "waiting_customer")]
        pending_events_domain = [("handled_state", "=", "pending")]
        accepted_pending_domain = [
            ("event_type", "=", "budget_accepted"),
            ("handled_state", "=", "pending"),
        ]
        rejected_pending_domain = [
            ("event_type", "=", "budget_rejected"),
            ("handled_state", "=", "pending"),
        ]
        oldest_pending = event_model.search(pending_events_domain, order="event_date asc, id asc", limit=1)
        oldest_label = (
            _("Más antiguo: %s")
            % fields.Datetime.to_string(oldest_pending.event_date)
            if oldest_pending
            else _("Sin actividad pendiente")
        )
        return [
            self._make_metric_card(
                _("Eventos pendientes"),
                event_model.search_count(pending_events_domain),
                oldest_label,
                action=self._get_action_dict(
                    _("Actividad portal pendiente"),
                    "wex.portal.repair.event",
                    domain=pending_events_domain,
                ),
                tone="danger",
                icon="fa fa-bell",
            ),
            self._make_metric_card(
                _("Aceptaciones por revisar"),
                event_model.search_count(accepted_pending_domain),
                _("Clientes que aceptaron y requieren seguimiento interno"),
                action=self._get_action_dict(
                    _("Aceptaciones portal"),
                    "wex.portal.repair.event",
                    domain=accepted_pending_domain,
                ),
                tone="success",
                icon="fa fa-check-circle",
            ),
            self._make_metric_card(
                _("Rechazos por revisar"),
                event_model.search_count(rejected_pending_domain),
                _("Presupuestos rechazados pendientes de gestión"),
                action=self._get_action_dict(
                    _("Rechazos portal"),
                    "wex.portal.repair.event",
                    domain=rejected_pending_domain,
                ),
                tone="warning",
                icon="fa fa-times-circle",
            ),
            self._make_metric_card(
                _("SAT esperando cliente"),
                repair_model.search_count(waiting_domain),
                _("Presupuestos en espera de aceptación o rechazo"),
                action=self._get_action_dict(
                    _("SAT esperando cliente"),
                    "repair.order",
                    domain=waiting_domain,
                    view_mode="list,form",
                ),
                tone="info",
                icon="fa fa-clock-o",
            ),
        ]

    @api.model
    def _get_summary_cards(self, period):
        event_model = self.env["wex.portal.repair.event"]
        repair_model = self.env["repair.order"]
        period_domain = [("event_date", ">=", period["period_start"])]
        active_repairs_domain = self._get_portal_enabled_active_repair_domain()
        waiting_customer_domain = [("x_budget_stage", "=", "waiting_customer")]
        return [
            self._make_metric_card(
                _("SAT activos en portal"),
                repair_model.search_count(active_repairs_domain),
                _("SAT activos de clientes con usuario portal activo"),
                action=self._get_action_dict(
                    _("SAT activos portal"),
                    "repair.order",
                    domain=active_repairs_domain,
                    view_mode="list,form",
                ),
                tone="neutral",
                icon="fa fa-wrench",
            ),
            self._make_metric_card(
                _("Presupuestos vistos"),
                event_model.search_count(period_domain + [("event_type", "=", "budget_viewed")]),
                _("Vistos por clientes en los últimos %s días") % period["period_days"],
                action=self._get_action_dict(
                    _("Presupuestos vistos"),
                    "wex.portal.repair.event",
                    domain=period_domain + [("event_type", "=", "budget_viewed")],
                ),
                tone="info",
                icon="fa fa-eye",
            ),
            self._make_metric_card(
                _("Presupuestos aceptados"),
                event_model.search_count(period_domain + [("event_type", "=", "budget_accepted")]),
                _("Aceptados desde portal en los últimos %s días") % period["period_days"],
                action=self._get_action_dict(
                    _("Presupuestos aceptados"),
                    "wex.portal.repair.event",
                    domain=period_domain + [("event_type", "=", "budget_accepted")],
                ),
                tone="success",
                icon="fa fa-thumbs-up",
            ),
            self._make_metric_card(
                _("Presupuestos rechazados"),
                event_model.search_count(period_domain + [("event_type", "=", "budget_rejected")]),
                _("Rechazados desde portal en los últimos %s días") % period["period_days"],
                action=self._get_action_dict(
                    _("Presupuestos rechazados"),
                    "wex.portal.repair.event",
                    domain=period_domain + [("event_type", "=", "budget_rejected")],
                ),
                tone="warning",
                icon="fa fa-thumbs-down",
            ),
            self._make_metric_card(
                _("Informes descargados"),
                event_model.search_count(period_domain + [("event_type", "=", "report_downloaded")]),
                _("Generados desde el portal en los últimos %s días") % period["period_days"],
                action=self._get_action_dict(
                    _("Informes descargados"),
                    "wex.portal.repair.event",
                    domain=period_domain + [("event_type", "=", "report_downloaded")],
                ),
                tone="info",
                icon="fa fa-download",
            ),
            self._make_metric_card(
                _("Esperando decisión del cliente"),
                repair_model.search_count(waiting_customer_domain),
                _("SAT con presupuesto todavía en espera"),
                action=self._get_action_dict(
                    _("SAT esperando decisión"),
                    "repair.order",
                    domain=waiting_customer_domain,
                    view_mode="list,form",
                ),
                tone="danger",
                icon="fa fa-hourglass-half",
            ),
        ]

    @api.model
    def _get_conversation_cards(self, period):
        if not self.env.registry.get("wex.portal.repair.conversation"):
            return []
        conversation_model = self.env["wex.portal.repair.conversation"]
        period_domain = [("last_message_at", ">=", period["period_start"])]
        pending_domain = [("state", "=", "pending_customer_reply")]
        sla_domain = [("sla_breached", "=", True), ("state", "=", "pending_customer_reply")]
        oldest_pending = conversation_model.search(
            pending_domain,
            order="last_customer_message_at asc, id asc",
            limit=1,
        )
        oldest_pending_label = (
            _("Último cliente: %s")
            % fields.Datetime.to_string(oldest_pending.last_customer_message_at)
            if oldest_pending and oldest_pending.last_customer_message_at
            else _("Sin conversaciones pendientes")
        )
        return [
            self._make_metric_card(
                _("Conversaciones activas"),
                conversation_model.search_count(period_domain),
                _("Con movimiento reciente en el portal"),
                action=self._get_action_dict(
                    _("Conversaciones portal"),
                    "wex.portal.repair.conversation",
                    domain=period_domain,
                ),
                tone="neutral",
                icon="fa fa-comments",
            ),
            self._make_metric_card(
                _("Pendientes de respuesta"),
                conversation_model.search_count(pending_domain),
                oldest_pending_label,
                action=self._get_action_dict(
                    _("Conversaciones pendientes"),
                    "wex.portal.repair.conversation",
                    domain=pending_domain,
                ),
                tone="warning",
                icon="fa fa-reply",
            ),
            self._make_metric_card(
                _("SLA vencido"),
                conversation_model.search_count(sla_domain),
                _("Conversaciones fuera de tiempo objetivo"),
                action=self._get_action_dict(
                    _("Conversaciones con SLA vencido"),
                    "wex.portal.repair.conversation",
                    domain=sla_domain,
                ),
                tone="danger",
                icon="fa fa-exclamation-triangle",
            ),
        ]

    @api.model
    def _get_activity_preview(self, limit=12):
        events = self.env["wex.portal.repair.event"].search([], order="event_date desc, id desc", limit=limit)
        rows = []
        for event in events:
            rows.append(
                {
                    "id": event.id,
                    "event_date": event.event_date,
                    "event_type_label": event._get_event_type_label(),
                    "event_icon": self._get_event_icon(event.event_type),
                    "handled_state_label": dict(event._fields["handled_state"].selection).get(
                        event.handled_state, event.handled_state or ""
                    ),
                    "handled_state": event.handled_state,
                    "repair_name": event.repair_id.display_name or "",
                    "customer_reference": event.repair_id.x_customer_reference or "",
                    "sale_order_name": event.sale_order_id.display_name or "",
                    "partner_name": event.commercial_partner_id.display_name
                    or event.partner_id.display_name
                    or "",
                    "responsible_name": event.responsible_user_id.display_name or "",
                    "amount_total": event.amount_total,
                    "currency_id": (
                        [event.currency_id.id, event.currency_id.display_name]
                        if event.currency_id
                        else False
                    ),
                    "open_action": {
                        "type": "ir.actions.act_window",
                        "name": event.display_name,
                        "res_model": "wex.portal.repair.event",
                        "res_id": event.id,
                        "view_mode": "form",
                        "views": self._get_action_views("form"),
                        "target": "current",
                    },
                }
            )
        return {
            "title": _("Actividad reciente"),
            "rows": rows,
            "empty_message": _("Todavía no hay actividad portal registrada."),
            "open_all_action": self._get_action_dict(
                _("Actividad portal SAT"),
                "wex.portal.repair.event",
                domain=[],
            ),
        }

    @api.model
    def _get_quick_actions(self, period):
        actions = [
            {
                "label": _("Actividad pendiente"),
                "description": _("Pendientes de gestionar"),
                "icon": "fa fa-bell",
                "action": self._get_action_dict(
                    _("Actividad portal pendiente"),
                    "wex.portal.repair.event",
                    domain=[("handled_state", "=", "pending")],
                ),
            },
            {
                "label": _("Aceptaciones"),
                "description": _("Aceptadas en el periodo"),
                "icon": "fa fa-check-circle",
                "action": self._get_action_dict(
                    _("Aceptaciones portal"),
                    "wex.portal.repair.event",
                    domain=[
                        ("event_type", "=", "budget_accepted"),
                        ("event_date", ">=", period["period_start"]),
                    ],
                ),
            },
            {
                "label": _("Rechazos"),
                "description": _("Rechazadas en el periodo"),
                "icon": "fa fa-times-circle",
                "action": self._get_action_dict(
                    _("Rechazos portal"),
                    "wex.portal.repair.event",
                    domain=[
                        ("event_type", "=", "budget_rejected"),
                        ("event_date", ">=", period["period_start"]),
                    ],
                ),
            },
            {
                "label": _("Informes"),
                "description": _("Descargados en el periodo"),
                "icon": "fa fa-download",
                "action": self._get_action_dict(
                    _("Informes descargados"),
                    "wex.portal.repair.event",
                    domain=[
                        ("event_type", "=", "report_downloaded"),
                        ("event_date", ">=", period["period_start"]),
                    ],
                ),
            },
            {
                "label": _("SAT en espera"),
                "description": _("Pendientes de decisión B2B"),
                "icon": "fa fa-clock-o",
                "action": self._get_action_dict(
                    _("SAT esperando cliente"),
                    "repair.order",
                    domain=[("x_budget_stage", "=", "waiting_customer")],
                    view_mode="list,form",
                ),
            },
        ]
        if self.env.registry.get("wex.portal.repair.conversation"):
            actions.append(
                {
                    "label": _("Conversaciones"),
                    "description": _("Mensajes de cliente sin responder"),
                    "icon": "fa fa-comments",
                    "action": self._get_action_dict(
                        _("Conversaciones pendientes"),
                        "wex.portal.repair.conversation",
                        domain=[("state", "=", "pending_customer_reply")],
                    ),
                }
            )
        return actions
