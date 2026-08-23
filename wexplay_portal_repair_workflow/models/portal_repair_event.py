# -*- coding: utf-8 -*-

from odoo import api, fields, models


class WexPortalRepairEvent(models.Model):
    _name = "wex.portal.repair.event"
    _description = "Actividad portal SAT"
    _order = "event_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Descripción",
        compute="_compute_name",
        store=True,
    )
    event_type = fields.Selection(
        selection=[
            ("budget_viewed", "Presupuesto visto"),
            ("budget_accepted", "Presupuesto aceptado"),
            ("budget_rejected", "Presupuesto rechazado"),
            ("report_downloaded", "Informe descargado"),
        ],
        string="Tipo de evento",
        required=True,
        readonly=True,
    )
    report_variant = fields.Selection(
        selection=[
            ("wexplay", "Informe con datos Wexplay"),
            ("custom", "Informe personalizado"),
        ],
        string="Variante de informe",
        readonly=True,
    )
    event_date = fields.Datetime(
        string="Fecha del evento",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
    )
    repair_id = fields.Many2one(
        comodel_name="repair.order",
        string="SAT",
        required=True,
        readonly=True,
        ondelete="cascade",
        check_company=True,
    )
    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Cotización",
        readonly=True,
        ondelete="set null",
        check_company=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente",
        readonly=True,
    )
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Empresa",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario portal",
        readonly=True,
    )
    responsible_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsable SAT",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda",
        readonly=True,
    )
    amount_total = fields.Monetary(
        string="Importe",
        currency_field="currency_id",
        readonly=True,
    )
    repair_state = fields.Char(
        string="Estado SAT",
        readonly=True,
    )
    budget_stage = fields.Char(
        string="Estado presupuesto",
        readonly=True,
    )
    sale_order_state = fields.Char(
        string="Estado cotización",
        readonly=True,
    )
    repair_schedule_date = fields.Datetime(
        string="Salida prevista SAT",
        related="repair_id.schedule_date",
        readonly=True,
    )
    handled_state = fields.Selection(
        selection=[
            ("pending", "Pendiente"),
            ("in_progress", "En gestión"),
            ("done", "Hecho"),
            ("ignored", "Sin acción"),
        ],
        string="Gestión interna",
        required=True,
        default="pending",
    )
    handled_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Gestionado por",
        readonly=True,
    )
    handled_at = fields.Datetime(
        string="Fecha de gestión",
        readonly=True,
    )
    pending_days = fields.Integer(
        string="Días desde evento",
        compute="_compute_pending_days",
    )
    note = fields.Text(
        string="Nota interna",
    )

    @api.depends("event_type", "report_variant", "repair_id.name")
    def _compute_name(self):
        for event in self:
            label = event._get_event_type_label()
            repair_name = event.repair_id.display_name or "SAT"
            event.name = "%s - %s" % (label, repair_name)

    @api.depends("event_date", "handled_at")
    def _compute_pending_days(self):
        now = fields.Datetime.to_datetime(fields.Datetime.now())
        for event in self:
            if not event.event_date:
                event.pending_days = 0
                continue
            event_date = fields.Datetime.to_datetime(event.event_date)
            reference_date = fields.Datetime.to_datetime(event.handled_at) or now
            event.pending_days = max((reference_date - event_date).days, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("handled_state"):
                vals["handled_state"] = self._get_default_handled_state(vals.get("event_type"))
        return super().create(vals_list)

    @api.model
    def _get_default_handled_state(self, event_type):
        if event_type in ("budget_viewed", "report_downloaded"):
            return "done"
        return "pending"

    def _get_event_type_label(self):
        self.ensure_one()
        label = dict(self._fields["event_type"].selection).get(
            self.event_type, self.event_type or ""
        )
        if self.event_type == "report_downloaded" and self.report_variant:
            variant = dict(self._fields["report_variant"].selection).get(
                self.report_variant, self.report_variant
            )
            return "%s: %s" % (label, variant)
        return label

    def _prepare_handled_values(self, handled_state):
        values = {"handled_state": handled_state}
        if handled_state in ("in_progress", "done", "ignored"):
            values.update(
                {
                    "handled_by_id": self.env.user.id,
                    "handled_at": fields.Datetime.now(),
                }
            )
        return values

    def action_mark_in_progress(self):
        self.write(self._prepare_handled_values("in_progress"))
        return True

    def action_mark_done(self):
        self.write(self._prepare_handled_values("done"))
        return True

    def action_ignore(self):
        self.write(self._prepare_handled_values("ignored"))
        return True

    def action_reset_pending(self):
        self.write(
            {
                "handled_state": "pending",
                "handled_by_id": False,
                "handled_at": False,
            }
        )
        return True

    def _get_open_form_action(self, record):
        record.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": record._name,
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_repair(self):
        self.ensure_one()
        return self._get_open_form_action(self.repair_id)

    def action_open_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            return False
        return self._get_open_form_action(self.sale_order_id)
