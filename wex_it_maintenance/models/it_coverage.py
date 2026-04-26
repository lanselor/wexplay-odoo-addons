from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WexItCoverage(models.Model):
    _name = "wex.it.coverage"
    _description = "Cobertura IT Wex"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id, date_start desc, id desc"

    STATE_SELECTION = [
        ("draft", "Borrador"),
        ("active", "Activa"),
        ("suspended", "Suspendida"),
        ("expired", "Vencida"),
        ("cancelled", "Cancelada"),
    ]

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        index=True,
        tracking=True,
        domain="[('x_is_it_maintenance_customer', '=', True)]",
    )
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    state = fields.Selection(selection=STATE_SELECTION, default="draft", required=True, tracking=True)
    date_start = fields.Date(string="Fecha inicio", tracking=True)
    date_end = fields.Date(string="Fecha fin", tracking=True)
    renewal_date = fields.Date(string="Fecha renovación")
    covered_asset_limit = fields.Integer(string="Equipos cubiertos")
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
        string="Frecuencia sugerida",
    )
    maintenance_template_id = fields.Many2one("wex.it.maintenance.template", string="Checklist sugerido")
    asset_ids = fields.Many2many(
        "wex.it.asset",
        "wex_it_coverage_asset_rel",
        "coverage_id",
        "asset_id",
        string="Activos cubiertos",
    )
    service_ids = fields.One2many("wex.it.service", "coverage_id", string="Servicios incluidos")
    software_ids = fields.One2many("wex.it.software", "coverage_id", string="Software/licencias")
    network_ids = fields.One2many("wex.it.network", "coverage_id", string="Redes")
    credential_ids = fields.One2many("wex.it.credential", "coverage_id", string="Credenciales")
    coverage_terms = fields.Text(string="Condiciones de cobertura")
    internal_notes = fields.Text(string="Notas internas")
    active = fields.Boolean(default=True)

    @api.constrains("partner_id")
    def _check_partner_id(self):
        for coverage in self:
            if coverage.partner_id and not coverage.partner_id.x_is_it_maintenance_customer:
                raise ValidationError("El cliente seleccionado no está habilitado para mantenimiento IT.")
            if coverage.partner_id.company_id and coverage.company_id != coverage.partner_id.company_id:
                raise ValidationError("La compañía de la cobertura debe coincidir con la del cliente.")

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for coverage in self:
            if coverage.date_start and coverage.date_end and coverage.date_end < coverage.date_start:
                raise ValidationError("La fecha de fin no puede ser anterior a la fecha de inicio.")

    @api.constrains("partner_id", "asset_ids")
    def _check_asset_partner(self):
        for coverage in self:
            invalid_assets = coverage.asset_ids.filtered(lambda asset: asset.partner_id != coverage.partner_id)
            if invalid_assets:
                raise ValidationError("Todos los activos cubiertos deben pertenecer al cliente de la cobertura.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner = self.env["res.partner"].browse(vals["partner_id"]) if vals.get("partner_id") else False
            if partner and not vals.get("company_id"):
                vals["company_id"] = partner.company_id.id or self.env.company.id
        return super().create(vals_list)
