# -*- coding: utf-8 -*-

import re
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .device_constants import DEVICE_TYPE_SELECTION


class RepairOrder(models.Model):
    _inherit = "repair.order"

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

    @api.model
    def _get_repair_card_alert_thresholds(self):
        return {
            "waiting_spare_days": 3,
            "confirmed_stale_days": 2,
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
            ("state", "not in", ["done", "cancel"]),
        ]

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
        }

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
    ):
        base_domain = self._get_repair_card_base_domain(companies)
        full_domain = base_domain + domain
        repairs = self.search(full_domain, order="write_date asc, create_date asc, id asc", limit=limit)
        count = self.search_count(full_domain)
        return {
            "key": key,
            "title": title,
            "empty_message": empty_message,
            "count": count,
            "items": [
                self._prepare_repair_card_alert_item(repair, now_dt, state_labels)
                for repair in repairs
            ],
            "domain": full_domain,
        }

    @api.model
    def _get_waiting_spare_alert_section(self, companies, thresholds, now_dt, state_labels):
        waiting_spare_location_ids = self._get_repair_card_waiting_spare_location_ids(companies)
        if not waiting_spare_location_ids:
            return {
                "key": "waiting_spare",
                "title": _("Pendiente de repuesto"),
                "empty_message": _("No hay ubicacion de pendiente de repuesto configurada en las companias activas."),
                "count": 0,
                "items": [],
                "domain": [],
            }

        cutoff = now_dt - timedelta(days=thresholds["waiting_spare_days"])
        return self._build_repair_card_alert_section(
            key="waiting_spare",
            title=_("Pendiente de repuesto"),
            empty_message=_("No hay ordenes envejecidas en pendiente de repuesto ahora mismo."),
            domain=[
                ("product_location_src_id", "in", waiting_spare_location_ids),
                ("write_date", "<=", fields.Datetime.to_string(cutoff)),
            ],
            companies=companies,
            now_dt=now_dt,
            limit=thresholds["section_limit"],
            state_labels=state_labels,
        )

    @api.model
    def _get_confirmed_stale_alert_section(self, companies, thresholds, now_dt, state_labels):
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
            domain=domain,
            companies=companies,
            now_dt=now_dt,
            limit=thresholds["section_limit"],
            state_labels=state_labels,
        )

    @api.model
    def _get_repair_card_alert_sections(self):
        companies = self._get_repair_card_sidebar_companies()
        now_dt = fields.Datetime.now()
        thresholds = self._get_repair_card_alert_thresholds()
        state_labels = self._get_repair_card_state_labels()
        return [
            self._get_waiting_spare_alert_section(companies, thresholds, now_dt, state_labels),
            self._get_confirmed_stale_alert_section(companies, thresholds, now_dt, state_labels),
        ]

    @api.model
    def get_repair_card_sidebar_data(self):
        return {
            "generated_at": fields.Datetime.to_string(fields.Datetime.now()),
            "sections": self._get_repair_card_alert_sections(),
        }
