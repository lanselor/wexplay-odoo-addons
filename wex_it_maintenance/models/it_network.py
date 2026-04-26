from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WexItNetwork(models.Model):
    _name = "wex.it.network"
    _description = "Red IT Wex"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id, name, id"

    STATUS_SELECTION = [
        ("active", "Activa"),
        ("warning", "Atención"),
        ("paused", "Pausada"),
        ("inactive", "Inactiva"),
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
    network_type_id = fields.Many2one("wex.it.network.type", string="Tipo", required=True)
    coverage_id = fields.Many2one("wex.it.coverage", string="Cobertura", ondelete="set null")
    status = fields.Selection(selection=STATUS_SELECTION, default="active", required=True, tracking=True)
    responsible_user_id = fields.Many2one("res.users", string="Usuario responsable")
    documentation_url = fields.Char(string="URL de documentación")
    asset_ids = fields.Many2many(
        "wex.it.asset",
        "wex_it_network_asset_rel",
        "network_id",
        "asset_id",
        string="Activos relacionados",
    )
    credential_ids = fields.One2many("wex.it.credential", "network_id", string="Credenciales")
    visit_ids = fields.Many2many(
        "wex.it.maintenance.visit",
        "wex_it_network_visit_rel",
        "network_id",
        "visit_id",
        string="Actividades",
    )
    notes = fields.Text(string="Notas")
    active = fields.Boolean(default=True)

    @api.constrains("partner_id", "coverage_id", "asset_ids")
    def _check_customer_links(self):
        for network in self:
            if network.partner_id and not network.partner_id.x_is_it_maintenance_customer:
                raise ValidationError("El cliente seleccionado no está habilitado para mantenimiento IT.")
            if network.partner_id.company_id and network.company_id != network.partner_id.company_id:
                raise ValidationError("La compañía de la red debe coincidir con la del cliente.")
            if network.coverage_id and network.coverage_id.partner_id != network.partner_id:
                raise ValidationError("La cobertura debe pertenecer al mismo cliente.")
            invalid_assets = network.asset_ids.filtered(lambda asset: asset.partner_id != network.partner_id)
            if invalid_assets:
                raise ValidationError("Todos los activos relacionados deben pertenecer al mismo cliente.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner = self.env["res.partner"].browse(vals["partner_id"]) if vals.get("partner_id") else False
            if partner and not vals.get("company_id"):
                vals["company_id"] = partner.company_id.id or self.env.company.id
        return super().create(vals_list)
