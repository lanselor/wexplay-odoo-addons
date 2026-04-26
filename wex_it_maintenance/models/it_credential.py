from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class WexItCredential(models.Model):
    _name = "wex.it.credential"
    _description = "Credencial IT Wex"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id, name, id"

    CREDENTIAL_TYPE_SELECTION = [
        ("password", "Contraseña"),
        ("api_key", "Clave API"),
        ("license", "Licencia"),
        ("pin", "PIN"),
        ("other", "Otro"),
    ]

    name = fields.Char(string="Nombre", required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        index=True,
        domain="[('x_is_it_maintenance_customer', '=', True)]",
    )
    asset_id = fields.Many2one("wex.it.asset", string="Activo", ondelete="set null")
    service_id = fields.Many2one("wex.it.service", string="Servicio", ondelete="set null")
    software_id = fields.Many2one("wex.it.software", string="Software/licencia", ondelete="set null")
    network_id = fields.Many2one("wex.it.network", string="Red", ondelete="set null")
    coverage_id = fields.Many2one("wex.it.coverage", string="Cobertura", ondelete="set null")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    credential_type = fields.Selection(selection=CREDENTIAL_TYPE_SELECTION, string="Tipo de credencial", required=True, default="password")
    login = fields.Char(string="Usuario / login")
    secret_value = fields.Char(string="Secreto", tracking=True)
    url = fields.Char(string="URL")
    notes = fields.Text(string="Notas")
    last_updated = fields.Date(string="Última actualización", default=fields.Date.context_today)
    rotation_due_date = fields.Date(string="Próxima rotación")
    active = fields.Boolean(string="Activa", default=True)
    can_view_secret = fields.Boolean(compute="_compute_secret_flags")
    show_secret_preview = fields.Boolean(compute="_compute_secret_flags")
    secret_preview = fields.Char(compute="_compute_secret_preview")

    @api.depends_context("uid", "show_secret")
    def _compute_secret_flags(self):
        has_group = self.env.user.has_group("wex_it_maintenance.group_it_maintenance_credential_user")
        show_secret = bool(self.env.context.get("show_secret"))
        for credential in self:
            credential.can_view_secret = has_group
            credential.show_secret_preview = has_group and show_secret

    @api.depends("secret_value")
    @api.depends_context("uid", "show_secret")
    def _compute_secret_preview(self):
        has_group = self.env.user.has_group("wex_it_maintenance.group_it_maintenance_credential_user")
        show_secret = bool(self.env.context.get("show_secret"))
        for credential in self:
            credential.secret_preview = credential.secret_value if has_group and show_secret else False

    @api.constrains("partner_id", "asset_id", "service_id", "software_id", "network_id", "coverage_id")
    def _check_customer_links(self):
        for credential in self:
            customer = credential.partner_id
            asset_customer = credential.asset_id.partner_id
            service_customer = credential.service_id.partner_id
            software_customer = credential.software_id.partner_id
            network_customer = credential.network_id.partner_id
            coverage_customer = credential.coverage_id.partner_id
            linked_customers = [
                partner
                for partner in [customer, asset_customer, service_customer, software_customer, network_customer, coverage_customer]
                if partner
            ]
            if not linked_customers:
                raise ValidationError("La credencial debe estar vinculada al menos a un cliente, activo o servicio.")
            commercial_partners = {partner.commercial_partner_id.id for partner in linked_customers}
            if len(commercial_partners) > 1:
                raise ValidationError("Cliente, activo y servicio deben pertenecer al mismo cliente.")
            main_partner = linked_customers[0].commercial_partner_id
            if not main_partner.x_is_it_maintenance_customer:
                raise ValidationError("El cliente seleccionado no está habilitado para mantenimiento IT.")

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = [self._sync_customer_and_company(vals) for vals in vals_list]
        return super().create(normalized_vals_list)

    def write(self, vals):
        vals = self._sync_customer_and_company(vals)
        return super().write(vals)

    @api.model
    def _sync_customer_and_company(self, vals):
        asset = self.env["wex.it.asset"].browse(vals.get("asset_id")) if vals.get("asset_id") else False
        service = self.env["wex.it.service"].browse(vals.get("service_id")) if vals.get("service_id") else False
        software = self.env["wex.it.software"].browse(vals.get("software_id")) if vals.get("software_id") else False
        network = self.env["wex.it.network"].browse(vals.get("network_id")) if vals.get("network_id") else False
        coverage = self.env["wex.it.coverage"].browse(vals.get("coverage_id")) if vals.get("coverage_id") else False
        if asset:
            vals.setdefault("partner_id", asset.partner_id.id)
            vals.setdefault("company_id", asset.company_id.id)
        elif service:
            vals.setdefault("partner_id", service.partner_id.id)
            vals.setdefault("company_id", service.company_id.id)
        elif software:
            vals.setdefault("partner_id", software.partner_id.id)
            vals.setdefault("company_id", software.company_id.id)
        elif network:
            vals.setdefault("partner_id", network.partner_id.id)
            vals.setdefault("company_id", network.company_id.id)
        elif coverage:
            vals.setdefault("partner_id", coverage.partner_id.id)
            vals.setdefault("company_id", coverage.company_id.id)
        elif vals.get("partner_id") and not vals.get("company_id"):
            partner = self.env["res.partner"].browse(vals["partner_id"])
            vals["company_id"] = partner.company_id.id or self.env.company.id
        return vals

    def action_show_secret(self):
        self.ensure_one()
        if not self.env.user.has_group("wex_it_maintenance.group_it_maintenance_credential_user"):
            raise AccessError("No tienes permisos para ver credenciales.")
        return {
            "type": "ir.actions.act_window",
            "res_model": "wex.it.credential",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
            "context": {**self.env.context, "show_secret": True},
        }
