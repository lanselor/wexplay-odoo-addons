from datetime import timedelta
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class WexItMaintenanceVisit(models.Model):
    _name = "wex.it.maintenance.visit"
    _description = "Actividad de mantenimiento IT Wex"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "scheduled_date desc, id desc"

    STATE_SELECTION = [
        ("draft", "Borrador"),
        ("scheduled", "Programada"),
        ("in_progress", "En curso"),
        ("done", "Realizada"),
        ("cancelled", "Cancelada"),
    ]

    VISIT_TYPE_SELECTION = [
        ("preventive", "Preventivo"),
        ("corrective", "Correctivo"),
        ("mixed", "Mixto"),
    ]

    ACTIVITY_MODE_SELECTION = [
        ("onsite", "Visita presencial"),
        ("remote", "Acción remota"),
        ("point_action", "Acción puntual"),
    ]

    name = fields.Char(string="Referencia", default="Nueva", copy=False, readonly=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        index=True,
        tracking=True,
        domain="[('x_is_it_maintenance_customer', '=', True)]",
    )
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    scheduled_date = fields.Datetime(string="Fecha programada", required=True, tracking=True, default=fields.Datetime.now)
    performed_date = fields.Datetime(string="Fecha realizada", tracking=True)
    technician_id = fields.Many2one("res.users", string="Técnico", required=True, default=lambda self: self.env.user)
    state = fields.Selection(selection=STATE_SELECTION, string="Estado", required=True, default="draft", tracking=True)
    visit_type = fields.Selection(selection=VISIT_TYPE_SELECTION, string="Tipo de mantenimiento", required=True, default="preventive", tracking=True)
    activity_mode = fields.Selection(selection=ACTIVITY_MODE_SELECTION, string="Modalidad", required=True, default="onsite", tracking=True)
    template_id = fields.Many2one("wex.it.maintenance.template", string="Plantilla de lista de comprobación")
    coverage_id = fields.Many2one("wex.it.coverage", string="Cobertura", ondelete="set null")
    summary = fields.Text(string="Resumen")
    recommendations = fields.Text(string="Recomendaciones")
    next_visit_date = fields.Date(string="Próxima visita")
    service_ids = fields.Many2many(
        "wex.it.service",
        "wex_it_service_visit_rel",
        "visit_id",
        "service_id",
        string="Servicios relacionados",
    )
    software_ids = fields.Many2many(
        "wex.it.software",
        "wex_it_software_visit_rel",
        "visit_id",
        "software_id",
        string="Software/licencias",
    )
    network_ids = fields.Many2many(
        "wex.it.network",
        "wex_it_network_visit_rel",
        "visit_id",
        "network_id",
        string="Redes",
    )
    line_ids = fields.One2many("wex.it.maintenance.visit.line", "visit_id", string="Líneas de actividad")
    checklist_line_ids = fields.One2many("wex.it.maintenance.visit.checklist.line", "visit_id", string="Lista de comprobación")
    review_ids = fields.One2many("wex.it.asset.review", "visit_id", string="Revisiones generadas")
    line_count = fields.Integer(compute="_compute_counts")
    review_count = fields.Integer(compute="_compute_counts")

    @api.depends("line_ids", "review_ids")
    def _compute_counts(self):
        for visit in self:
            visit.line_count = len(visit.line_ids)
            visit.review_count = len(visit.review_ids)

    @api.constrains("partner_id")
    def _check_partner_id(self):
        for visit in self:
            if visit.partner_id and not visit.partner_id.x_is_it_maintenance_customer:
                raise ValidationError("El cliente seleccionado no está habilitado para mantenimiento IT.")
            if visit.partner_id.company_id and visit.company_id != visit.partner_id.company_id:
                raise ValidationError("La compañía de la actividad debe coincidir con la del cliente.")

    @api.constrains("coverage_id", "service_ids", "software_ids", "network_ids")
    def _check_service_partner(self):
        for visit in self:
            if visit.coverage_id and visit.coverage_id.partner_id != visit.partner_id:
                raise ValidationError("La cobertura debe pertenecer al cliente seleccionado.")
            invalid_services = visit.service_ids.filtered(lambda service: service.partner_id != visit.partner_id)
            if invalid_services:
                raise ValidationError("Todos los servicios relacionados deben pertenecer al cliente seleccionado.")
            invalid_software = visit.software_ids.filtered(lambda software: software.partner_id != visit.partner_id)
            if invalid_software:
                raise ValidationError("Todo el software relacionado debe pertenecer al cliente seleccionado.")
            invalid_networks = visit.network_ids.filtered(lambda network: network.partner_id != visit.partner_id)
            if invalid_networks:
                raise ValidationError("Todas las redes relacionadas deben pertenecer al cliente seleccionado.")

    @api.model
    def _get_company_id_from_partner(self, partner):
        return partner.company_id.id or self.env.company.id

    @api.model
    def _prepare_create_vals(self, vals):
        partner = self.env["res.partner"].browse(vals["partner_id"]) if vals.get("partner_id") else False
        if partner and not vals.get("company_id"):
            vals["company_id"] = self._get_company_id_from_partner(partner)
        return vals

    def _needs_sequence_name(self):
        self.ensure_one()
        return self.name in ("New", "Nueva")

    def _assign_sequence_if_needed(self):
        for visit in self:
            if visit._needs_sequence_name():
                visit.name = self.env["ir.sequence"].next_by_code("wex.it.maintenance.visit") or "Nueva"

    def _should_apply_template_lines(self):
        self.ensure_one()
        return bool(self.template_id and not self.checklist_line_ids)

    def _apply_template_if_needed(self):
        for visit in self:
            if visit._should_apply_template_lines():
                visit._apply_template_lines()

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._prepare_create_vals(vals) for vals in vals_list]
        records = super().create(vals_list)
        records._assign_sequence_if_needed()
        records._apply_template_if_needed()
        return records

    def write(self, vals):
        result = super().write(vals)
        if vals.get("template_id"):
            self._apply_template_if_needed()
        return result

    def _get_template_line_commands(self):
        self.ensure_one()
        commands = [fields.Command.clear()]
        for line in self.template_id.line_ids:
            commands.append(fields.Command.create({
                "sequence": line.sequence,
                "name": line.name,
                "description": line.description,
            }))
        return commands

    def _apply_template_lines(self):
        self.ensure_one()
        if not self.template_id:
            return
        self.checklist_line_ids = self._get_template_line_commands()

    def action_apply_template(self):
        for visit in self:
            visit._apply_template_lines()

    def action_set_scheduled(self):
        self.write({"state": "scheduled"})

    def action_start(self):
        self.write({"state": "in_progress"})

    def _check_can_complete_visit(self):
        self.ensure_one()
        if not self.line_ids and not self.checklist_line_ids:
            raise UserError("No puedes completar una actividad sin líneas de trabajo o lista de comprobación.")

    def _prepare_done_values(self):
        self.ensure_one()
        values = {"state": "done"}
        if not self.performed_date:
            values["performed_date"] = fields.Datetime.now()
        return values

    def action_done(self):
        for visit in self:
            visit._check_can_complete_visit()
            visit.write(visit._prepare_done_values())
            visit._create_asset_reviews()

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def _get_asset_lines_grouped_by_asset(self):
        self.ensure_one()
        grouped_lines = defaultdict(lambda: self.env["wex.it.maintenance.visit.line"])
        for line in self.line_ids.filtered("asset_id"):
            grouped_lines[line.asset_id] |= line
        return grouped_lines

    def _has_existing_asset_review(self, asset):
        self.ensure_one()
        review_model = self.env["wex.it.asset.review"]
        return bool(review_model.search_count([("visit_id", "=", self.id), ("asset_id", "=", asset.id)]))

    def _join_line_field_values(self, lines, field_name):
        return "\n".join(filter(None, lines.mapped(field_name)))

    def _get_health_status_from_lines(self, lines):
        if any(line.result == "issue" for line in lines):
            return "critical"
        if any(line.result == "attention" for line in lines):
            return "attention"
        return "healthy"

    def _prepare_asset_review_vals(self, asset, lines):
        self.ensure_one()
        return {
            "asset_id": asset.id,
            "visit_id": self.id,
            "review_date": fields.Date.context_today(self),
            "technician_id": self.technician_id.id,
            "health_status": self._get_health_status_from_lines(lines),
            "tasks_done": self._join_line_field_values(lines, "action_performed"),
            "issues_found": self._join_line_field_values(lines, "issue_found"),
            "recommendations": self._join_line_field_values(lines, "observations"),
            "next_action": self.recommendations,
        }

    def _create_asset_reviews(self):
        review_model = self.env["wex.it.asset.review"]
        for visit in self:
            for asset, lines in visit._get_asset_lines_grouped_by_asset().items():
                if visit._has_existing_asset_review(asset):
                    continue
                review_model.create(visit._prepare_asset_review_vals(asset, lines))

    @api.model
    def _get_dashboard_limit(self):
        return 6

    @api.model
    def _get_open_visit_states(self):
        return ["draft", "scheduled", "in_progress"]

    @api.model
    def _get_dashboard_counts(self, customers):
        asset_model = self.env["wex.it.asset"]
        service_model = self.env["wex.it.service"]
        software_model = self.env["wex.it.software"]
        network_model = self.env["wex.it.network"]
        coverage_model = self.env["wex.it.coverage"]
        open_states = self._get_open_visit_states()
        return {
            "customers": len(customers),
            "assets": asset_model.search_count([]),
            "open_activities": self.search_count([("state", "in", open_states)]),
            "services": service_model.search_count([]),
            "software": software_model.search_count([]),
            "networks": network_model.search_count([]),
            "coverages": coverage_model.search_count([("state", "=", "active")]),
        }

    @api.model
    def _get_upcoming_visits_data(self, now, limit):
        return self.search_read(
            [("state", "in", self._get_open_visit_states()), ("scheduled_date", ">=", now)],
            ["name", "partner_id", "scheduled_date", "state", "activity_mode"],
            limit=limit,
            order="scheduled_date asc",
        )

    @api.model
    def _get_overdue_visits_data(self, now, limit):
        return self.search_read(
            [("state", "in", self._get_open_visit_states()), ("scheduled_date", "<", now)],
            ["name", "partner_id", "scheduled_date", "state", "activity_mode"],
            limit=limit,
            order="scheduled_date asc",
        )

    @api.model
    def _get_customers_without_next_visit_data(self, customers, now, limit):
        future_visits = self.search([
            ("state", "in", self._get_open_visit_states()),
            ("scheduled_date", ">=", now),
        ])
        partner_ids_with_future = set(future_visits.mapped("partner_id").ids)
        customers_without_next_visit = customers.filtered(
            lambda partner: partner.id not in partner_ids_with_future
        )[:limit]
        return [
            {"id": partner.id, "name": partner.display_name, "service_level": partner.service_level or ""}
            for partner in customers_without_next_visit
        ]

    @api.model
    def _get_problematic_assets_data(self, limit):
        asset_model = self.env["wex.it.asset"]
        return asset_model.search_read(
            [("status", "in", ["maintenance", "issue"])],
            ["name", "partner_id", "internal_code", "status"],
            limit=limit,
            order="write_date desc",
        )

    @api.model
    def _get_expiring_services_data(self, expiring_date, limit):
        service_model = self.env["wex.it.service"]
        return service_model.search_read(
            [("status", "=", "active"), ("renewal_date", "!=", False), ("renewal_date", "<=", expiring_date)],
            ["name", "partner_id", "renewal_date", "status"],
            limit=limit,
            order="renewal_date asc",
        )

    @api.model
    def _get_recent_visits_data(self, limit):
        return self.search_read(
            [("state", "=", "done")],
            ["name", "partner_id", "performed_date", "visit_type", "activity_mode"],
            limit=limit,
            order="performed_date desc",
        )

    @api.model
    def get_dashboard_data(self):
        today = fields.Date.context_today(self)
        now = fields.Datetime.now()
        limit = self._get_dashboard_limit()
        customer_model = self.env["res.partner"]
        customers = customer_model.search([("x_is_it_maintenance_customer", "=", True)])
        expiring_date = today + timedelta(days=30)
        return {
            "counts": self._get_dashboard_counts(customers),
            "upcoming_visits": self._get_upcoming_visits_data(now, limit),
            "overdue_visits": self._get_overdue_visits_data(now, limit),
            "customers_without_next_visit": self._get_customers_without_next_visit_data(customers, now, limit),
            "problematic_assets": self._get_problematic_assets_data(limit),
            "expiring_services": self._get_expiring_services_data(expiring_date, limit),
            "recent_visits": self._get_recent_visits_data(limit),
        }


class WexItMaintenanceVisitLine(models.Model):
    _name = "wex.it.maintenance.visit.line"
    _description = "Línea de actividad de mantenimiento IT Wex"
    _order = "sequence, id"

    RESULT_SELECTION = [
        ("ok", "Correcto"),
        ("attention", "Requiere atención"),
        ("issue", "Incidencia detectada"),
    ]

    sequence = fields.Integer(default=10)
    visit_id = fields.Many2one("wex.it.maintenance.visit", required=True, ondelete="cascade", index=True)
    partner_id = fields.Many2one(related="visit_id.partner_id", store=True, index=True)
    company_id = fields.Many2one(related="visit_id.company_id", store=True, index=True)
    asset_id = fields.Many2one("wex.it.asset", string="Activo", ondelete="set null")
    service_id = fields.Many2one("wex.it.service", string="Servicio", ondelete="set null")
    software_id = fields.Many2one("wex.it.software", string="Software/licencia", ondelete="set null")
    network_id = fields.Many2one("wex.it.network", string="Red", ondelete="set null")
    action_performed = fields.Char(string="Acción realizada", required=True)
    result = fields.Selection(selection=RESULT_SELECTION, string="Resultado", required=True, default="ok")
    issue_found = fields.Text(string="Incidencia detectada")
    observations = fields.Text(string="Observaciones")

    @api.constrains("asset_id", "service_id", "software_id", "network_id")
    def _check_related_partner(self):
        for line in self:
            if line.asset_id and line.asset_id.partner_id != line.visit_id.partner_id:
                raise ValidationError("El activo seleccionado debe pertenecer al mismo cliente que la actividad.")
            if line.service_id and line.service_id.partner_id != line.visit_id.partner_id:
                raise ValidationError("El servicio seleccionado debe pertenecer al mismo cliente que la actividad.")
            if line.software_id and line.software_id.partner_id != line.visit_id.partner_id:
                raise ValidationError("El software seleccionado debe pertenecer al mismo cliente que la actividad.")
            if line.network_id and line.network_id.partner_id != line.visit_id.partner_id:
                raise ValidationError("La red seleccionada debe pertenecer al mismo cliente que la actividad.")


class WexItMaintenanceVisitChecklistLine(models.Model):
    _name = "wex.it.maintenance.visit.checklist.line"
    _description = "Línea de checklist de actividad de mantenimiento IT Wex"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    visit_id = fields.Many2one("wex.it.maintenance.visit", required=True, ondelete="cascade", index=True)
    name = fields.Char(required=True)
    description = fields.Text()
    is_done = fields.Boolean(string="Hecho")
    notes = fields.Text()
