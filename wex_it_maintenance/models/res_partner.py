from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_is_it_maintenance_customer = fields.Boolean(
        string="Cliente de mantenimiento IT",
        tracking=True,
    )
    contract_start_date = fields.Date(string="Fecha inicio contrato")
    contract_end_date = fields.Date(string="Fecha fin contrato")
    visit_frequency = fields.Selection(
        selection=[
            ("weekly", "Semanal"),
            ("biweekly", "Quincenal"),
            ("monthly", "Mensual"),
            ("quarterly", "Trimestral"),
            ("semiannual", "Semestral"),
            ("annual", "Anual"),
            ("on_demand", "Bajo demanda"),
        ],
        string="Frecuencia de visita",
    )
    service_level = fields.Selection(
        selection=[
            ("basic", "Básico"),
            ("standard", "Estándar"),
            ("premium", "Premium"),
            ("custom", "Personalizado"),
        ],
        string="Nivel de servicio",
    )
    internal_notes = fields.Text(string="Notas internas")
    it_asset_ids = fields.One2many("wex.it.asset", "partner_id", string="Activos IT")
    it_asset_review_ids = fields.One2many("wex.it.asset.review", "partner_id", string="Revisiones de activos")
    it_service_ids = fields.One2many("wex.it.service", "partner_id", string="Servicios IT")
    it_visit_ids = fields.One2many("wex.it.maintenance.visit", "partner_id", string="Actividades")
    it_credential_ids = fields.One2many("wex.it.credential", "partner_id", string="Credenciales")
    it_asset_count = fields.Integer(compute="_compute_it_counts", string="Nº activos")
    it_service_count = fields.Integer(compute="_compute_it_counts", string="Nº servicios")
    it_visit_count = fields.Integer(compute="_compute_it_counts", string="Nº actividades")
    it_credential_count = fields.Integer(compute="_compute_it_counts", string="Nº credenciales")
    it_open_visit_count = fields.Integer(compute="_compute_it_workspace_metrics", string="Actividades abiertas")
    it_issue_asset_count = fields.Integer(compute="_compute_it_workspace_metrics", string="Activos con incidencias")
    it_active_service_count = fields.Integer(compute="_compute_it_workspace_metrics", string="Servicios activos")
    it_review_count = fields.Integer(compute="_compute_it_workspace_metrics", string="Nº revisiones")
    it_next_visit_date = fields.Datetime(compute="_compute_it_workspace_metrics", string="Próxima actividad")
    it_last_done_visit_date = fields.Datetime(compute="_compute_it_workspace_metrics", string="Última actividad realizada")

    @api.depends("it_asset_ids", "it_service_ids", "it_visit_ids", "it_credential_ids")
    def _compute_it_counts(self):
        for partner in self:
            partner.it_asset_count = len(partner.it_asset_ids)
            partner.it_service_count = len(partner.it_service_ids)
            partner.it_visit_count = len(partner.it_visit_ids)
            partner.it_credential_count = len(partner.it_credential_ids)

    @api.depends(
        "it_asset_ids.status",
        "it_service_ids.status",
        "it_visit_ids.state",
        "it_visit_ids.scheduled_date",
        "it_visit_ids.performed_date",
        "it_asset_ids.review_ids",
        "it_credential_ids",
    )
    def _compute_it_workspace_metrics(self):
        for partner in self:
            open_visits = partner.it_visit_ids.filtered(lambda visit: visit.state in ("draft", "scheduled", "in_progress"))
            done_visits = partner.it_visit_ids.filtered(lambda visit: visit.state == "done" and visit.performed_date)
            next_visit = open_visits.sorted(lambda visit: visit.scheduled_date or fields.Datetime.now())[:1]
            last_done_visit = done_visits.sorted(lambda visit: visit.performed_date, reverse=True)[:1]
            partner.it_open_visit_count = len(open_visits)
            partner.it_issue_asset_count = len(partner.it_asset_ids.filtered(lambda asset: asset.status in ("maintenance", "issue")))
            partner.it_active_service_count = len(partner.it_service_ids.filtered(lambda service: service.status == "active"))
            partner.it_review_count = len(partner.it_asset_review_ids)
            partner.it_next_visit_date = next_visit.scheduled_date if next_visit else False
            partner.it_last_done_visit_date = last_done_visit.performed_date if last_done_visit else False

    @api.constrains("contract_start_date", "contract_end_date")
    def _check_contract_dates(self):
        for partner in self:
            if (
                partner.contract_start_date
                and partner.contract_end_date
                and partner.contract_end_date < partner.contract_start_date
            ):
                raise ValidationError("La fecha de fin de contrato no puede ser anterior a la fecha de inicio.")

    def _get_it_customer_code_prefix(self):
        self.ensure_one()
        base_name = (self.commercial_partner_id.name or self.name or "").upper()
        sanitized = "".join(character for character in base_name if character.isalnum() or character == " ")
        tokens = [token for token in sanitized.split() if token]
        prefix = tokens[0] if tokens else sanitized.replace(" ", "")
        prefix = (prefix or "CLIENT")[:6]
        return prefix

    def action_open_it_assets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Activos IT",
            "res_model": "wex.it.asset",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def action_open_it_workspace(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Workspace cliente",
            "res_model": "res.partner",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(self.env.ref("wex_it_maintenance.view_partner_form_it_maintenance_workspace").id, "form")],
            "target": "current",
            "context": {"form_view_ref": "wex_it_maintenance.view_partner_form_it_maintenance_workspace"},
        }

    def action_open_it_services(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Servicios IT",
            "res_model": "wex.it.service",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def action_open_it_visits(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Actividades IT",
            "res_model": "wex.it.maintenance.visit",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def action_open_it_reviews(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Revisiones de activos",
            "res_model": "wex.it.asset.review",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"search_default_group_customer": 1},
        }

    def action_open_it_credentials(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Credenciales",
            "res_model": "wex.it.credential",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def action_open_it_reports(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Informes de actividad",
            "res_model": "wex.it.maintenance.visit",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id), ("state", "=", "done")],
            "context": {"default_partner_id": self.id},
        }

    def action_open_base_contact(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Ficha de contacto",
            "res_model": "res.partner",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(self.env.ref("base.view_partner_form").id, "form")],
            "target": "current",
        }
