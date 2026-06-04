# -*- coding: utf-8 -*-

import re
from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

from .device_constants import DEVICE_TYPE_SELECTION


class RepairOrder(models.Model):
    _inherit = "repair.order"

    _SAT_PRIORITY_DEADLINE_FIELD_BY_VALUE = {
        "normal": "x_sat_priority_normal_hours",
        "urgent": "x_sat_priority_urgent_hours",
        "company": "x_sat_priority_company_hours",
        "warranty": "x_sat_priority_warranty_hours",
        "budget": "x_sat_priority_budget_hours",
        "budget_extended": "x_sat_priority_budget_extended_hours",
        "express": "x_sat_priority_express_hours",
    }

    state = fields.Selection(
        selection_add=[("done", "Finalizado")],
        ondelete={"done": "set default"},
    )

    x_device_type = fields.Selection(
        DEVICE_TYPE_SELECTION,
        string="Tipo de dispositivo",
    )

    x_sat_priority = fields.Selection(
        [
            ("normal", "Normal"),
            ("urgent", "Urgente"),
            ("company", "Empresa"),
            ("warranty", "Garantía"),
            ("budget", "Presupuesto"),
            ("budget_extended", "Presupuesto 2"),
            ("express", "Express"),
        ],
        string="Prioridad SAT",
        default="normal",
        tracking=True,
        index=True,
    )

    x_reception_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Recepciona",
        help="Empleado que recepciona el equipo en mostrador.",
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
    )

    x_customer_reference = fields.Char(
        string="Referencia del cliente",
        help="Referencia de la orden de reparación del cliente empresa para vincularla con nuestra orden SAT.",
    )

    x_partner_mobile = fields.Char(
        string="Móvil",
        related="partner_id.mobile",
        readonly=True,
        store=False,
    )

    x_partner_phone = fields.Char(
        string="Teléfono",
        related="partner_id.phone",
        readonly=True,
        store=False,
    )

    x_partner_email = fields.Char(
        string="Correo electrónico",
        related="partner_id.email",
        readonly=True,
        store=False,
    )

    x_partner_phone_mobile_search = fields.Char(
        string="Teléfono/Celular",
        search="_search_x_partner_phone_mobile_search",
        readonly=True,
        store=False,
    )

    x_partner_address_summary = fields.Char(
        string="Dirección",
        compute="_compute_x_partner_address_summary",
        store=False,
        readonly=True,
    )

    x_brand_id = fields.Many2one(
        "wex.repair.brand",
        string="Marca",
        related="x_model_id.brand_id",
        store=True,
        readonly=True,
    )

    x_model_id = fields.Many2one(
        "wex.repair.device_model",
        string="Modelo",
        ondelete="restrict",
        domain="[('device_type', '=', x_device_type)]",
    )

    x_reception_employee_avatar = fields.Image(
        string="Avatar recepción",
        related="x_reception_employee_id.image_128",
        readonly=True,
        store=False,
    )

    x_responsible_avatar = fields.Image(
        string="Avatar responsable",
        compute="_compute_x_responsible_avatar",
        readonly=True,
        store=False,
    )

    x_unlock_type = fields.Selection(
        [
            ("pin", "PIN"),
            ("pattern", "Patrón"),
            ("password", "Contraseña"),
            ("none", "Sin bloqueo"),
            ("unknown", "No indicado"),
        ],
        string="Tipo de desbloqueo",
    )

    x_unlock_code = fields.Char(string="Código / Contraseña")
    x_unlock_pattern = fields.Char(string="Patrón (descripción)")
    x_unlock_notes = fields.Text(string="Notas de desbloqueo")

    x_brand = fields.Char(string="Marca (texto)")
    x_model = fields.Char(string="Modelo (texto)")
    x_imei = fields.Char(string="IMEI / Nº de serie")
    x_accessories = fields.Text(string="Accesorios entregados")
    x_reported_issue = fields.Text(string="Avería descrita por el cliente")
    x_internal_notes = fields.Text(string="Observaciones internas (técnico)")

    x_sat_total_amount = fields.Monetary(
        string="Total SAT",
        currency_field="x_sat_currency_id",
        compute="_compute_x_sat_total_amount",
        store=False,
        readonly=True,
    )

    x_sat_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_x_sat_total_amount",
        store=False,
        readonly=True,
    )

    def _get_partner_address_parts(self):
        self.ensure_one()
        partner = self.partner_id
        return [
            partner.street,
            partner.street2,
            " ".join(filter(None, [partner.zip, partner.city])) or False,
            partner.state_id.name,
            partner.country_id.name,
        ]

    @api.depends(
        "partner_id",
        "partner_id.street",
        "partner_id.street2",
        "partner_id.zip",
        "partner_id.city",
        "partner_id.state_id",
        "partner_id.country_id",
    )
    def _compute_x_partner_address_summary(self):
        for rec in self:
            rec.x_partner_address_summary = ", ".join(
                filter(None, rec._get_partner_address_parts())
            )

    def _get_sale_order_currency(self):
        self.ensure_one()
        return self.sale_order_id.currency_id or self.company_id.currency_id

    @api.depends(
        "sale_order_id",
        "sale_order_id.amount_total",
        "sale_order_id.currency_id",
        "company_id",
    )
    def _compute_x_sat_total_amount(self):
        for rec in self:
            if rec.sale_order_id:
                rec.x_sat_total_amount = rec.sale_order_id.amount_total or 0.0
                rec.x_sat_currency_id = rec._get_sale_order_currency()
            else:
                rec.x_sat_total_amount = 0.0
                rec.x_sat_currency_id = rec.company_id.currency_id

    @api.depends("user_id", "user_id.partner_id.image_128", "user_id.employee_id.image_128")
    def _compute_x_responsible_avatar(self):
        for rec in self:
            user = rec.user_id
            employee = user.employee_id
            rec.x_responsible_avatar = employee.image_128 or user.partner_id.image_128

    @api.model
    def _get_partners_matching_normalized_phone(self, normalized_value):
        if not normalized_value:
            return self.env["res.partner"]

        like_value = f"%{normalized_value}%"
        self.env.cr.execute(
            r"""
            SELECT id
              FROM res_partner
             WHERE regexp_replace(COALESCE(phone, ''), '\D', '', 'g') LIKE %s
                OR regexp_replace(COALESCE(mobile, ''), '\D', '', 'g') LIKE %s
            """,
            [like_value, like_value],
        )
        partner_ids = [row[0] for row in self.env.cr.fetchall()]
        if not partner_ids:
            return self.env["res.partner"]
        return self.env["res.partner"].search([("id", "in", partner_ids)])

    @api.model
    def _get_partners_matching_phone_search(self, operator, value):
        normalized_value = re.sub(r"\D+", "", value)
        partner_domain = ["|", ("phone", operator, value), ("mobile", operator, value)]
        partners = self.env["res.partner"].search(partner_domain)
        if normalized_value:
            partners |= self._get_partners_matching_normalized_phone(normalized_value)
        return partners

    @api.model
    def _search_x_partner_phone_mobile_search(self, operator, value):
        if operator not in ("ilike", "like", "=", "=like", "=ilike"):
            return [("id", "=", 0)]

        value = (value or "").strip()
        if not value:
            return [("id", "=", 0)]

        partners = self._get_partners_matching_phone_search(operator, value)
        return [("partner_id", "in", partners.ids or [0])]

    @api.onchange("x_device_type")
    def _onchange_x_device_type_reset_model_brand(self):
        """Si cambia el tipo, limpiamos modelo para evitar inconsistencias."""
        for rec in self:
            if rec.x_model_id and rec.x_model_id.device_type != rec.x_device_type:
                rec.x_model_id = False

    @api.onchange("x_model_id")
    def _onchange_x_model_id_sync_device_type(self):
        for rec in self:
            if rec.x_model_id and rec.x_device_type != rec.x_model_id.device_type:
                rec.x_device_type = rec.x_model_id.device_type

    def action_view_device_history(self):
        self.ensure_one()
        serial = (self.x_imei or "").strip()
        if not serial:
            raise UserError(_("No hay IMEI / Nº de serie informado en esta orden."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Historial del dispositivo"),
            "res_model": "repair.order",
            "view_mode": "list,form",
            "domain": [("x_imei", "=", serial)],
            "context": {
                "search_default_group_by_partner_id": 0,
                "default_x_imei": serial,
            },
        }

    def _get_sat_priority_deadline_hours_map(self):
        params = self.env["ir.config_parameter"].sudo()
        hours_map = {}
        for priority, field_name in self._SAT_PRIORITY_DEADLINE_FIELD_BY_VALUE.items():
            default = self._get_sat_priority_deadline_default(priority)
            hours_map[priority] = float(
                params.get_param(f"wexplay_repair.{field_name}", default)
            )
        return hours_map

    def _get_sat_priority_deadline_hours(self):
        self.ensure_one()
        priority = self.x_sat_priority or "normal"
        return self._get_sat_priority_deadline_hours_map().get(priority) or 0.0

    @api.model
    def _get_sat_priority_deadline_default(self, priority):
        defaults = {
            "normal": 72.0,
            "urgent": 24.0,
            "company": 48.0,
            "warranty": 72.0,
            "budget": 72.0,
            "budget_extended": 120.0,
            "express": 1.0,
        }
        return defaults.get(priority, 0.0)

    @api.model
    def _get_repair_card_alert_thresholds(self):
        return {
            "waiting_spare_days": 3,
            "confirmed_stale_days": 2,
            "express_risk_hours": 2,
            "section_limit": 6,
        }

    @api.model
    def _get_repair_card_state_labels(self):
        return dict(self._fields["state"].selection)

    @api.model
    def _get_repair_card_sidebar_companies(self):
        companies = self.env.companies
        return companies if companies else self.env.company

    @api.model
    def _get_repair_card_waiting_spare_location_ids(self, companies):
        return companies.mapped("x_repair_state_location_waiting_spare_id").ids

    @api.model
    def _get_repair_card_base_domain(self, companies):
        return [
            ("company_id", "in", companies.ids),
            ("state", "not in", ["done", "cancel", "delivered"]),
        ]

    @api.model
    def _get_repair_card_effective_domain(self, companies, active_domain=None, extra_domain=None):
        domain = list(self._get_repair_card_base_domain(companies))
        if active_domain:
            domain += active_domain
        if extra_domain:
            domain += extra_domain
        return domain

    @api.model
    def _get_repair_card_priority_deadline_domain(
        self, now_dt, priorities=None, extra_hours=0.0
    ):
        hours_map = self._get_sat_priority_deadline_hours_map()
        priority_values = priorities or list(self._SAT_PRIORITY_DEADLINE_FIELD_BY_VALUE)
        priority_domains = []
        for priority in priority_values:
            deadline_hours = hours_map.get(priority) or 0.0
            cutoff = now_dt + timedelta(hours=extra_hours - deadline_hours)
            date_domain = [("create_date", "<=", fields.Datetime.to_string(cutoff))]
            priority_domain = [("x_sat_priority", "=", priority)]
            if priority == "normal":
                priority_domain = expression.OR(
                    [[("x_sat_priority", "=", False)], priority_domain]
                )
            priority_domains.append(expression.AND([priority_domain, date_domain]))
        return expression.OR(priority_domains) if priority_domains else [("id", "=", 0)]

    @api.model
    def _get_repair_card_waiting_spare_alert_domain(
        self, waiting_spare_location_ids, thresholds, now_dt
    ):
        cutoff = fields.Datetime.to_string(
            now_dt - timedelta(days=thresholds["waiting_spare_days"])
        )
        location_domain = [("product_location_src_id", "in", waiting_spare_location_ids)]
        if not self._has_repair_card_field("x_waiting_spare_started_at"):
            return expression.AND([location_domain, [("write_date", "<=", cutoff)]])

        age_domain = expression.OR(
            [
                [
                    ("x_waiting_spare_started_at", "!=", False),
                    ("x_waiting_spare_started_at", "<=", cutoff),
                ],
                [
                    ("x_waiting_spare_started_at", "=", False),
                    ("write_date", "<=", cutoff),
                ],
            ]
        )
        return expression.AND([location_domain, age_domain])

    @api.model
    def _prepare_repair_card_alert_item(self, repair, now_dt, state_labels):
        age_days = max((now_dt - (repair.write_date or repair.create_date)).days, 0)
        return {
            "id": repair.id,
            "name": repair.name,
            "customer": repair.partner_id.display_name or "",
            "device": repair.x_model_id.display_name or repair.product_id.display_name or "",
            "state_label": state_labels.get(repair.state, repair.state or ""),
            "workflow": repair.product_location_src_id.complete_name or "",
            "age_days": age_days,
            "alert_label": "",
        }

    def _get_sat_priority_deadline_at(self):
        self.ensure_one()
        create_dt = fields.Datetime.to_datetime(self.create_date)
        if not create_dt:
            return False
        return create_dt + timedelta(hours=self._get_sat_priority_deadline_hours())

    def _get_sat_priority_overdue_delta(self, now_dt):
        self.ensure_one()
        deadline_dt = self._get_sat_priority_deadline_at()
        if not deadline_dt:
            return timedelta(0)
        return now_dt - deadline_dt

    def _is_sat_priority_overdue(self, now_dt):
        self.ensure_one()
        overdue_delta = self._get_sat_priority_overdue_delta(now_dt)
        return overdue_delta.total_seconds() > 0

    @api.model
    def _format_repair_card_overdue_label(self, overdue_delta):
        overdue_hours = max(int(overdue_delta.total_seconds() // 3600), 0)
        overdue_days = overdue_hours // 24
        if overdue_days >= 1:
            if overdue_days == 1:
                return _("1 dia de retraso")
            return _("%s dias de retraso") % overdue_days
        if overdue_hours <= 1:
            return _("Menos de 1h de retraso")
        return _("%s horas de retraso") % overdue_hours

    @api.model
    def _prepare_overdue_alert_item(self, repair, now_dt, state_labels):
        item = self._prepare_repair_card_alert_item(repair, now_dt, state_labels)
        item["alert_label"] = self._format_repair_card_overdue_label(
            repair._get_sat_priority_overdue_delta(now_dt)
        )
        return item

    @api.model
    def _prepare_express_alert_item(self, repair, now_dt, state_labels):
        item = self._prepare_repair_card_alert_item(repair, now_dt, state_labels)
        deadline_dt = repair._get_sat_priority_deadline_at()
        if deadline_dt:
            remaining_delta = deadline_dt - now_dt
            remaining_hours = max(int(remaining_delta.total_seconds() // 3600), 0)
            if repair._is_sat_priority_overdue(now_dt):
                item["alert_label"] = self._format_repair_card_overdue_label(
                    repair._get_sat_priority_overdue_delta(now_dt)
                )
            elif remaining_hours <= 1:
                item["alert_label"] = _("Vence en menos de 1h")
            else:
                item["alert_label"] = _("Vence en %s horas") % remaining_hours
        return item

    @api.model
    def _prepare_without_responsible_alert_item(self, repair, now_dt, state_labels):
        item = self._prepare_repair_card_alert_item(repair, now_dt, state_labels)
        item["alert_label"] = _("Sin responsable")
        return item

    @api.model
    def _build_repair_card_alert_section(
        self,
        *,
        key,
        title,
        empty_message,
        domain,
        companies,
        now_dt,
        limit,
        state_labels,
        prepare_item_method=None,
        order="write_date asc, create_date asc, id asc",
    ):
        base_domain = self._get_repair_card_base_domain(companies)
        full_domain = base_domain + domain
        repairs = self.search(full_domain, order=order, limit=limit)
        count = self.search_count(full_domain)
        shown_count = len(repairs)
        prepare_item_method = prepare_item_method or self._prepare_repair_card_alert_item
        return {
            "key": key,
            "title": title,
            "empty_message": empty_message,
            "count": count,
            "shown_count": shown_count,
            "hidden_count": max(count - shown_count, 0),
            "items": [
                prepare_item_method(repair, now_dt, state_labels)
                for repair in repairs
            ],
            "domain": full_domain,
        }

    @api.model
    def _get_waiting_spare_alert_section(
        self, companies, thresholds, now_dt, state_labels, active_domain=None
    ):
        waiting_spare_location_ids = self._get_repair_card_waiting_spare_location_ids(companies)
        if not waiting_spare_location_ids:
            return {
                "key": "waiting_spare",
                "title": _("Pendiente de repuesto"),
                "empty_message": _(
                    "No hay ubicacion de pendiente de repuesto configurada en las companias activas."
                ),
                "count": 0,
                "shown_count": 0,
                "hidden_count": 0,
                "items": [],
                "domain": [],
            }

        domain = self._get_repair_card_waiting_spare_alert_domain(
            waiting_spare_location_ids, thresholds, now_dt
        )
        return self._build_repair_card_alert_section(
            key="waiting_spare",
            title=_("Pendiente de repuesto"),
            empty_message=_("No hay ordenes envejecidas en pendiente de repuesto ahora mismo."),
            domain=(active_domain or []) + domain,
            companies=companies,
            now_dt=now_dt,
            limit=thresholds["section_limit"],
            state_labels=state_labels,
        )

    @api.model
    def _get_confirmed_stale_alert_section(
        self, companies, thresholds, now_dt, state_labels, active_domain=None
    ):
        waiting_spare_location_ids = self._get_repair_card_waiting_spare_location_ids(companies)
        cutoff = now_dt - timedelta(days=thresholds["confirmed_stale_days"])
        domain = [
            ("state", "=", "confirmed"),
            ("write_date", "<=", fields.Datetime.to_string(cutoff)),
        ]
        if waiting_spare_location_ids:
            domain.append(("product_location_src_id", "not in", waiting_spare_location_ids))
        return self._build_repair_card_alert_section(
            key="confirmed_stale",
            title=_("Confirmadas sin movimiento"),
            empty_message=_("No hay ordenes confirmadas que lleven demasiado tiempo sin movimiento."),
            domain=(active_domain or []) + domain,
            companies=companies,
            now_dt=now_dt,
            limit=thresholds["section_limit"],
            state_labels=state_labels,
        )

    @api.model
    def _get_overdue_alert_section(
        self, companies, thresholds, now_dt, state_labels, active_domain=None
    ):
        domain = self._get_repair_card_priority_deadline_domain(now_dt)
        return self._build_repair_card_alert_section(
            key="overdue",
            title=_("Con retraso"),
            empty_message=_("No hay ordenes activas fuera de plazo ahora mismo."),
            domain=(active_domain or []) + domain,
            companies=companies,
            now_dt=now_dt,
            limit=thresholds["section_limit"],
            state_labels=state_labels,
            prepare_item_method=self._prepare_overdue_alert_item,
            order="create_date asc, id asc",
        )

    @api.model
    def _get_express_alert_section(
        self, companies, thresholds, now_dt, state_labels, active_domain=None
    ):
        domain = self._get_repair_card_priority_deadline_domain(
            now_dt,
            priorities=["express"],
            extra_hours=thresholds["express_risk_hours"],
        )
        return self._build_repair_card_alert_section(
            key="express",
            title=_("Express con riesgo"),
            empty_message=_("No hay ordenes express con riesgo ahora mismo."),
            domain=(active_domain or []) + domain,
            companies=companies,
            now_dt=now_dt,
            limit=thresholds["section_limit"],
            state_labels=state_labels,
            prepare_item_method=self._prepare_express_alert_item,
            order="create_date asc, id asc",
        )

    @api.model
    def _get_without_responsible_alert_section(
        self, companies, thresholds, now_dt, state_labels, active_domain=None
    ):
        return self._build_repair_card_alert_section(
            key="without_responsible",
            title=_("Sin responsable"),
            empty_message=_("No hay ordenes activas sin responsable."),
            domain=(active_domain or []) + [("user_id", "=", False)],
            companies=companies,
            now_dt=now_dt,
            limit=thresholds["section_limit"],
            state_labels=state_labels,
            prepare_item_method=self._prepare_without_responsible_alert_item,
            order="create_date asc, id asc",
        )

    @api.model
    def _get_repair_card_alert_sections(self, active_domain=None):
        companies = self._get_repair_card_sidebar_companies()
        now_dt = fields.Datetime.now()
        thresholds = self._get_repair_card_alert_thresholds()
        state_labels = self._get_repair_card_state_labels()
        return [
            self._get_overdue_alert_section(
                companies, thresholds, now_dt, state_labels, active_domain=active_domain
            ),
            self._get_express_alert_section(
                companies, thresholds, now_dt, state_labels, active_domain=active_domain
            ),
            self._get_waiting_spare_alert_section(
                companies, thresholds, now_dt, state_labels, active_domain=active_domain
            ),
            self._get_without_responsible_alert_section(
                companies, thresholds, now_dt, state_labels, active_domain=active_domain
            ),
            self._get_confirmed_stale_alert_section(
                companies, thresholds, now_dt, state_labels, active_domain=active_domain
            ),
        ]

    @api.model
    def get_repair_card_sidebar_data(self, active_domain=None):
        return {
            "generated_at": fields.Datetime.to_string(fields.Datetime.now()),
            "sections": self._get_repair_card_alert_sections(active_domain=active_domain),
        }

    @api.model
    def _has_repair_card_field(self, field_name):
        return field_name in self._fields

    @api.model
    def _get_repair_card_hero_base_domain(self, companies):
        domain = [("company_id", "in", companies.ids)]
        if self._has_repair_card_field("state"):
            domain.append(("state", "not in", ["cancel"]))
        return domain

    @api.model
    def _get_repair_card_waiting_spare_domain(self, companies):
        waiting_spare_location_ids = self._get_repair_card_waiting_spare_location_ids(companies)
        if not waiting_spare_location_ids:
            return [("id", "=", 0)]
        return [("product_location_src_id", "in", waiting_spare_location_ids)]

    @api.model
    def _get_repair_card_pending_pickup_domain(self, companies):
        done_location_ids = companies.mapped("x_repair_state_location_done_id").ids
        if not done_location_ids:
            return [("id", "=", 0)]
        return [
            ("state", "in", ["done", "cancel"]),
            ("product_location_src_id", "in", done_location_ids),
        ]

    @api.model
    def _get_repair_card_hero_sections_definition(self, companies):
        sections = [
            {
                "key": "draft",
                "title": _("Entrada / Nuevos"),
                "short_title": _("Entrada"),
                "domain": [("state", "=", "draft")],
            },
        ]
        if self._has_repair_card_field("x_budget_stage"):
            sections.append(
                {
                    "key": "estimating",
                    "title": _("En revision"),
                    "short_title": _("Revision"),
                    "domain": [("x_budget_stage", "=", "estimating")],
                }
            )
            sections.append(
                {
                    "key": "waiting_customer",
                    "title": _("Pendiente cliente"),
                    "short_title": _("Cliente"),
                    "domain": [("x_budget_stage", "=", "waiting_customer")],
                }
            )
            sections.append(
                {
                    "key": "accepted_budget",
                    "title": _("Presupuesto aceptado"),
                    "short_title": _("Aceptado"),
                    "domain": [("x_budget_stage", "=", "accepted")],
                }
            )
        sections.extend(
            [
                {
                    "key": "confirmed",
                    "title": _("Confirmadas"),
                    "short_title": _("Confirmadas"),
                    "domain": [("state", "=", "confirmed")],
                },
                {
                    "key": "under_repair",
                    "title": _("En reparacion"),
                    "short_title": _("Reparacion"),
                    "domain": [("state", "=", "under_repair")],
                },
                {
                    "key": "waiting_spare",
                    "title": _("Pendiente repuesto"),
                    "short_title": _("Repuesto"),
                    "domain": self._get_repair_card_waiting_spare_domain(companies),
                },
                {
                    "key": "pending_pickup",
                    "title": _("Pendiente recoger"),
                    "short_title": _("Recoger"),
                    "domain": self._get_repair_card_pending_pickup_domain(companies),
                },
            ]
        )
        return sections

    def _get_repair_card_phase_started_at(self):
        self.ensure_one()
        return fields.Datetime.to_datetime(self.write_date or self.create_date)

    def _get_repair_card_sla_elapsed_ratio(self, now_dt):
        self.ensure_one()
        phase_started_at = self._get_repair_card_phase_started_at()
        sla_hours = self._get_sat_priority_deadline_hours()
        if not phase_started_at or not sla_hours:
            return 0.0
        elapsed_hours = max((now_dt - phase_started_at).total_seconds() / 3600.0, 0.0)
        return elapsed_hours / sla_hours

    def _is_repair_card_sla_overdue(self, now_dt):
        self.ensure_one()
        return self._get_repair_card_sla_elapsed_ratio(now_dt) > 1.0

    def _is_repair_card_sla_at_risk(self, now_dt):
        self.ensure_one()
        ratio = self._get_repair_card_sla_elapsed_ratio(now_dt)
        return 0.8 <= ratio <= 1.0

    @api.model
    def _get_repair_card_active_repairs(self, companies, active_domain=None):
        return self.search(
            self._get_repair_card_effective_domain(companies, active_domain=active_domain),
            order="write_date asc, create_date asc, id asc",
        )

    @api.model
    def _get_repair_card_schedule_domain(self, day):
        start_dt = datetime.combine(day, time.min)
        end_dt = start_dt + timedelta(days=1)
        return [
            ("schedule_date", ">=", fields.Datetime.to_string(start_dt)),
            ("schedule_date", "<", fields.Datetime.to_string(end_dt)),
        ]

    @api.model
    def _build_repair_card_metric(self, key, title, repairs, severity):
        return {
            "key": key,
            "title": title,
            "count": len(repairs),
            "domain": [("id", "in", repairs.ids or [0])],
            "severity": severity,
            "enabled": bool(repairs),
        }

    @api.model
    def _get_repair_card_metric_repairs(self, companies, active_domain=None):
        now_dt = fields.Datetime.now()
        today = fields.Date.context_today(self)
        tomorrow = today + timedelta(days=1)
        active_repairs = self._get_repair_card_active_repairs(
            companies, active_domain=active_domain
        )
        waiting_spare_location_ids = self._get_repair_card_waiting_spare_location_ids(companies)
        done_location_ids = companies.mapped("x_repair_state_location_done_id").ids

        overdue_repairs = active_repairs.filtered(
            lambda repair: repair._is_repair_card_sla_overdue(now_dt)
        )
        critical_overdue_repairs = overdue_repairs.filtered(
            lambda repair: repair.x_sat_priority in ("express", "urgent")
        )
        regular_overdue_repairs = overdue_repairs - critical_overdue_repairs
        at_risk_repairs = active_repairs.filtered(
            lambda repair: repair._is_repair_card_sla_at_risk(now_dt)
        )
        draft_stale_repairs = active_repairs.filtered(
            lambda repair: repair.state == "draft"
            and repair._get_repair_card_phase_started_at()
            and repair._get_repair_card_phase_started_at() <= now_dt - timedelta(hours=48)
        )
        under_repair_stale_repairs = active_repairs.filtered(
            lambda repair: repair.state == "under_repair"
            and repair._get_repair_card_phase_started_at()
            and repair._get_repair_card_phase_started_at() <= now_dt - timedelta(hours=24)
        )
        waiting_spare_repairs = active_repairs.filtered(
            lambda repair: repair.product_location_src_id.id in waiting_spare_location_ids
        )
        without_responsible_repairs = active_repairs.filtered(lambda repair: not repair.user_id)
        confirmed_stale_repairs = active_repairs.filtered(
            lambda repair: repair.state == "confirmed"
            and repair._get_repair_card_phase_started_at()
            and repair._get_repair_card_phase_started_at() <= now_dt - timedelta(days=2)
        )

        today_schedule_repairs = self.search(
            self._get_repair_card_effective_domain(
                companies,
                active_domain=active_domain,
                extra_domain=self._get_repair_card_schedule_domain(today),
            ),
            order="schedule_date asc, id asc",
        )
        tomorrow_schedule_repairs = self.search(
            self._get_repair_card_effective_domain(
                companies,
                active_domain=active_domain,
                extra_domain=self._get_repair_card_schedule_domain(tomorrow),
            ),
            order="schedule_date asc, id asc",
        )
        today_at_risk_repairs = today_schedule_repairs.filtered(
            lambda repair: not (
                repair.state in ("done", "cancel", "delivered")
                or repair.product_location_src_id.id in done_location_ids
            )
        )

        return {
            "overdue_all": overdue_repairs,
            "overdue_critical": critical_overdue_repairs,
            "overdue_regular": regular_overdue_repairs,
            "sla_at_risk": at_risk_repairs,
            "today_at_risk": today_at_risk_repairs,
            "draft_stale": draft_stale_repairs,
            "under_repair_stale": under_repair_stale_repairs,
            "waiting_spare": waiting_spare_repairs,
            "without_responsible": without_responsible_repairs,
            "confirmed_stale": confirmed_stale_repairs,
            "today_schedule": today_schedule_repairs,
            "tomorrow_schedule": tomorrow_schedule_repairs,
        }

    @api.model
    def _get_repair_card_hero_indicators(self, companies, active_domain=None):
        metric_repairs = self._get_repair_card_metric_repairs(
            companies, active_domain=active_domain
        )
        return [
            self._build_repair_card_metric(
                "overdue_all",
                _("Con retraso"),
                metric_repairs["overdue_all"],
                "warning",
            ),
            self._build_repair_card_metric(
                "overdue_critical",
                _("SLA critico"),
                metric_repairs["overdue_critical"],
                "critical",
            ),
        ]

    @api.model
    def get_repair_card_sidebar_metrics_data(self, active_domain=None):
        companies = self._get_repair_card_sidebar_companies()
        metric_repairs = self._get_repair_card_metric_repairs(
            companies, active_domain=active_domain
        )
        return {
            "generated_at": fields.Datetime.to_string(fields.Datetime.now()),
            "groups": [
                {
                    "key": "critical",
                    "title": _("Critico"),
                    "severity": "critical",
                    "metrics": [
                        self._build_repair_card_metric(
                            "overdue_critical",
                            _("SLA superado - Express/Urgente"),
                            metric_repairs["overdue_critical"],
                            "critical",
                        ),
                        self._build_repair_card_metric(
                            "today_at_risk",
                            _("Compromisos de hoy en riesgo"),
                            metric_repairs["today_at_risk"],
                            "critical",
                        ),
                    ],
                },
                {
                    "key": "attention",
                    "title": _("Atencion"),
                    "severity": "warning",
                    "metrics": [
                        self._build_repair_card_metric(
                            "overdue_regular",
                            _("SLA superado - resto prioridades"),
                            metric_repairs["overdue_regular"],
                            "warning",
                        ),
                        self._build_repair_card_metric(
                            "sla_at_risk",
                            _("SLA en riesgo (>80% consumido)"),
                            metric_repairs["sla_at_risk"],
                            "warning",
                        ),
                        self._build_repair_card_metric(
                            "confirmed_stale",
                            _("Confirmadas sin movimiento"),
                            metric_repairs["confirmed_stale"],
                            "warning",
                        ),
                    ],
                },
                {
                    "key": "operational",
                    "title": _("Operativo"),
                    "severity": "info",
                    "metrics": [
                        self._build_repair_card_metric(
                            "draft_stale",
                            _("En ENTRADA sin primer toque +48h"),
                            metric_repairs["draft_stale"],
                            "info",
                        ),
                        self._build_repair_card_metric(
                            "waiting_spare",
                            _("Pendiente de repuesto"),
                            metric_repairs["waiting_spare"],
                            "info",
                        ),
                        self._build_repair_card_metric(
                            "without_responsible",
                            _("Sin responsable"),
                            metric_repairs["without_responsible"],
                            "info",
                        ),
                        self._build_repair_card_metric(
                            "under_repair_stale",
                            _("En reparacion sin movimiento +24h"),
                            metric_repairs["under_repair_stale"],
                            "info",
                        ),
                    ],
                },
                {
                    "key": "today",
                    "title": _("Hoy"),
                    "severity": "today",
                    "metrics": [
                        self._build_repair_card_metric(
                            "today_schedule",
                            _("Entregas comprometidas para hoy"),
                            metric_repairs["today_schedule"],
                            "today",
                        ),
                        self._build_repair_card_metric(
                            "tomorrow_schedule",
                            _("Entregas comprometidas manana"),
                            metric_repairs["tomorrow_schedule"],
                            "today",
                        ),
                    ],
                },
            ],
        }

    @api.model
    def get_repair_card_hero_data(self, active_domain=None):
        companies = self._get_repair_card_sidebar_companies()
        base_domain = self._get_repair_card_hero_base_domain(companies)
        active_domain = active_domain or []
        sections = []
        for definition in self._get_repair_card_hero_sections_definition(companies):
            full_domain = base_domain + active_domain + definition["domain"]
            sections.append(
                {
                    "key": definition["key"],
                    "title": definition["title"],
                    "short_title": definition["short_title"],
                    "count": self.search_count(full_domain),
                    "domain": full_domain,
                }
            )
        return {
            "generated_at": fields.Datetime.to_string(fields.Datetime.now()),
            "sections": sections,
            "indicators": self._get_repair_card_hero_indicators(
                companies, active_domain=active_domain
            ),
        }
