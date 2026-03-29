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

    @api.constrains("service_ids")
    def _check_service_partner(self):
        for visit in self:
            invalid_services = visit.service_ids.filtered(lambda service: service.partner_id != visit.partner_id)
            if invalid_services:
                raise ValidationError("Todos los servicios relacionados deben pertenecer al cliente seleccionado.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner = self.env["res.partner"].browse(vals["partner_id"]) if vals.get("partner_id") else False
            if partner and not vals.get("company_id"):
                vals["company_id"] = partner.company_id.id or self.env.company.id
        records = super().create(vals_list)
        for record in records:
            if record.name == "New":
                record.name = self.env["ir.sequence"].next_by_code("wex.it.maintenance.visit") or "Nueva"
            if record.template_id and not record.checklist_line_ids:
                record._apply_template_lines()
        return records

    def write(self, vals):
        result = super().write(vals)
        if vals.get("template_id"):
            for visit in self:
                if visit.template_id and not visit.checklist_line_ids:
                    visit._apply_template_lines()
        return result

    def _apply_template_lines(self):
        self.ensure_one()
        if not self.template_id:
            return
        commands = [fields.Command.clear()]
        for line in self.template_id.line_ids:
            commands.append(fields.Command.create({
                "sequence": line.sequence,
                "name": line.name,
                "description": line.description,
            }))
        self.checklist_line_ids = commands

    def action_apply_template(self):
        for visit in self:
            visit._apply_template_lines()

    def action_set_scheduled(self):
        self.write({"state": "scheduled"})

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_done(self):
        for visit in self:
            if not visit.line_ids and not visit.checklist_line_ids:
                raise UserError("No puedes completar una actividad sin líneas de trabajo o lista de comprobación.")
            values = {"state": "done"}
            if not visit.performed_date:
                values["performed_date"] = fields.Datetime.now()
            visit.write(values)
            visit._create_asset_reviews()

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def _create_asset_reviews(self):
        review_model = self.env["wex.it.asset.review"]
        for visit in self:
            asset_lines = visit.line_ids.filtered("asset_id")
            grouped_lines = defaultdict(lambda: self.env["wex.it.maintenance.visit.line"])
            for line in asset_lines:
                grouped_lines[line.asset_id] |= line
            for asset, lines in grouped_lines.items():
                if review_model.search_count([("visit_id", "=", visit.id), ("asset_id", "=", asset.id)]):
                    continue
                issues = "\n".join(filter(None, lines.mapped("issue_found")))
                actions = "\n".join(filter(None, lines.mapped("action_performed")))
                recommendations = "\n".join(filter(None, lines.mapped("observations")))
                health_status = "healthy"
                if any(line.result == "issue" for line in lines):
                    health_status = "critical"
                elif any(line.result == "attention" for line in lines):
                    health_status = "attention"
                review_model.create({
                    "asset_id": asset.id,
                    "visit_id": visit.id,
                    "review_date": fields.Date.context_today(self),
                    "technician_id": visit.technician_id.id,
                    "health_status": health_status,
                    "tasks_done": actions,
                    "issues_found": issues,
                    "recommendations": recommendations,
                    "next_action": visit.recommendations,
                })

    @api.model
    def get_dashboard_data(self):
        today = fields.Date.context_today(self)
        now = fields.Datetime.now()
        limit = 6
        customer_model = self.env["res.partner"]
        asset_model = self.env["wex.it.asset"]
        service_model = self.env["wex.it.service"]
        customers = customer_model.search([("x_is_it_maintenance_customer", "=", True)])
        future_visits = self.search([
            ("state", "in", ["draft", "scheduled", "in_progress"]),
            ("scheduled_date", ">=", now),
        ])
        partner_ids_with_future = set(future_visits.mapped("partner_id").ids)
        customers_without_next_visit = customers.filtered(lambda partner: partner.id not in partner_ids_with_future)[:limit]
        expiring_date = today + timedelta(days=30)
        return {
            "counts": {
                "customers": len(customers),
                "assets": asset_model.search_count([]),
                "open_activities": self.search_count([("state", "in", ["draft", "scheduled", "in_progress"])]),
                "services": service_model.search_count([]),
            },
            "upcoming_visits": self.search_read(
                [("state", "in", ["draft", "scheduled", "in_progress"]), ("scheduled_date", ">=", now)],
                ["name", "partner_id", "scheduled_date", "state", "activity_mode"],
                limit=limit,
                order="scheduled_date asc",
            ),
            "overdue_visits": self.search_read(
                [("state", "in", ["draft", "scheduled", "in_progress"]), ("scheduled_date", "<", now)],
                ["name", "partner_id", "scheduled_date", "state", "activity_mode"],
                limit=limit,
                order="scheduled_date asc",
            ),
            "customers_without_next_visit": [
                {"id": partner.id, "name": partner.display_name, "service_level": partner.service_level or ""}
                for partner in customers_without_next_visit
            ],
            "problematic_assets": asset_model.search_read(
                [("status", "in", ["maintenance", "issue"])],
                ["name", "partner_id", "internal_code", "status"],
                limit=limit,
                order="write_date desc",
            ),
            "expiring_services": service_model.search_read(
                [("status", "=", "active"), ("renewal_date", "!=", False), ("renewal_date", "<=", expiring_date)],
                ["name", "partner_id", "renewal_date", "status"],
                limit=limit,
                order="renewal_date asc",
            ),
            "recent_visits": self.search_read(
                [("state", "=", "done")],
                ["name", "partner_id", "performed_date", "visit_type", "activity_mode"],
                limit=limit,
                order="performed_date desc",
            ),
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
    action_performed = fields.Char(string="Acción realizada", required=True)
    result = fields.Selection(selection=RESULT_SELECTION, string="Resultado", required=True, default="ok")
    issue_found = fields.Text(string="Incidencia detectada")
    observations = fields.Text(string="Observaciones")

    @api.constrains("asset_id", "service_id")
    def _check_related_partner(self):
        for line in self:
            if line.asset_id and line.asset_id.partner_id != line.visit_id.partner_id:
                raise ValidationError("El activo seleccionado debe pertenecer al mismo cliente que la actividad.")
            if line.service_id and line.service_id.partner_id != line.visit_id.partner_id:
                raise ValidationError("El servicio seleccionado debe pertenecer al mismo cliente que la actividad.")


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
