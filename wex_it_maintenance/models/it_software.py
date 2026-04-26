from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WexItSoftware(models.Model):
    _name = "wex.it.software"
    _description = "Software y licencias IT Wex"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id, name, id"

    STATUS_SELECTION = [
        ("active", "Activo"),
        ("warning", "Atención"),
        ("paused", "Pausado"),
        ("inactive", "Inactivo"),
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
    software_type_id = fields.Many2one("wex.it.software.type", string="Tipo", required=True)
    coverage_id = fields.Many2one("wex.it.coverage", string="Cobertura", ondelete="set null")
    status = fields.Selection(selection=STATUS_SELECTION, default="active", required=True, tracking=True)
    responsible_user_id = fields.Many2one("res.users", string="Usuario responsable")
    vendor = fields.Char(string="Proveedor")
    managed_by_wex = fields.Boolean(string="Gestionado por Wexplay")
    renewal_required = fields.Boolean(string="Requiere renovación")
    renewal_date = fields.Date(string="Fecha de renovación")
    documentation_url = fields.Char(string="URL de documentación")
    asset_ids = fields.Many2many(
        "wex.it.asset",
        "wex_it_software_asset_rel",
        "software_id",
        "asset_id",
        string="Activos relacionados",
    )
    credential_ids = fields.One2many("wex.it.credential", "software_id", string="Credenciales")
    visit_ids = fields.Many2many(
        "wex.it.maintenance.visit",
        "wex_it_software_visit_rel",
        "software_id",
        "visit_id",
        string="Actividades",
    )
    notes = fields.Text(string="Notas")
    active = fields.Boolean(default=True)

    @api.onchange("software_type_id")
    def _onchange_software_type_id(self):
        for software in self:
            if software.software_type_id:
                software.renewal_required = software.software_type_id.default_renewal_required
                software.managed_by_wex = software.software_type_id.default_managed_by_wex

    @api.constrains("partner_id", "coverage_id", "asset_ids")
    def _check_customer_links(self):
        for software in self:
            if software.partner_id and not software.partner_id.x_is_it_maintenance_customer:
                raise ValidationError("El cliente seleccionado no está habilitado para mantenimiento IT.")
            if software.partner_id.company_id and software.company_id != software.partner_id.company_id:
                raise ValidationError("La compañía del software debe coincidir con la del cliente.")
            if software.coverage_id and software.coverage_id.partner_id != software.partner_id:
                raise ValidationError("La cobertura debe pertenecer al mismo cliente.")
            invalid_assets = software.asset_ids.filtered(lambda asset: asset.partner_id != software.partner_id)
            if invalid_assets:
                raise ValidationError("Todos los activos relacionados deben pertenecer al mismo cliente.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner = self.env["res.partner"].browse(vals["partner_id"]) if vals.get("partner_id") else False
            if partner and not vals.get("company_id"):
                vals["company_id"] = partner.company_id.id or self.env.company.id
        return super().create(vals_list)
