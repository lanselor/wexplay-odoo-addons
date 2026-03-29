from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WexItAssetReview(models.Model):
    _name = "wex.it.asset.review"
    _description = "Revisión de activo IT Wex"
    _order = "review_date desc, id desc"

    HEALTH_STATUS_SELECTION = [
        ("healthy", "Correcto"),
        ("attention", "Requiere atención"),
        ("critical", "Crítico"),
    ]

    asset_id = fields.Many2one("wex.it.asset", string="Activo", required=True, ondelete="cascade", index=True)
    visit_id = fields.Many2one("wex.it.maintenance.visit", string="Actividad", ondelete="set null", index=True)
    partner_id = fields.Many2one(related="asset_id.partner_id", store=True, index=True)
    company_id = fields.Many2one(related="asset_id.company_id", store=True, index=True)
    review_date = fields.Date(string="Fecha de revisión", required=True, default=fields.Date.context_today)
    technician_id = fields.Many2one("res.users", string="Técnico", required=True, default=lambda self: self.env.user)
    health_status = fields.Selection(selection=HEALTH_STATUS_SELECTION, string="Estado de salud", required=True, default="healthy")
    tasks_done = fields.Text(string="Tareas realizadas")
    issues_found = fields.Text(string="Incidencias detectadas")
    recommendations = fields.Text(string="Recomendaciones")
    next_action = fields.Text(string="Próxima acción")

    @api.constrains("asset_id", "visit_id")
    def _check_asset_visit_partner(self):
        for review in self:
            if review.visit_id and review.asset_id.partner_id != review.visit_id.partner_id:
                raise ValidationError("El activo y la actividad deben pertenecer al mismo cliente.")
