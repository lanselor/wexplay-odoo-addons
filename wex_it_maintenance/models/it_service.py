from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WexItService(models.Model):
    _name = "wex.it.service"
    _description = "Servicio IT Wex"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id, name, id"

    SERVICE_TYPE_SELECTION = [
        ("m365", "Microsoft 365"),
        ("vpn", "VPN"),
        ("nas", "NAS"),
        ("backup", "Copia de seguridad"),
        ("domain", "Dominio"),
        ("router_firewall", "Router / Firewall"),
        ("local_server", "Servidor local"),
        ("network_printer", "Impresora de red"),
        ("remote_access", "Acceso remoto"),
        ("management_software", "Software de gestión"),
        ("other", "Otro"),
    ]

    STATUS_SELECTION = [
        ("active", "Activo"),
        ("warning", "Atención"),
        ("paused", "Pausado"),
        ("inactive", "Inactivo"),
    ]

    name = fields.Char(string="Nombre", required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        index=True,
        tracking=True,
        domain="[('x_is_it_maintenance_customer', '=', True)]",
    )
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    service_type = fields.Selection(selection=SERVICE_TYPE_SELECTION, string="Tipo de servicio", required=True)
    status = fields.Selection(selection=STATUS_SELECTION, string="Estado", required=True, default="active", tracking=True)
    responsible_user_id = fields.Many2one("res.users", string="Usuario responsable")
    renewal_date = fields.Date(string="Fecha de renovación")
    documentation_url = fields.Char(string="URL de documentación")
    notes = fields.Text(string="Notas")
    credential_ids = fields.One2many("wex.it.credential", "service_id", string="Credenciales")
    visit_ids = fields.Many2many(
        "wex.it.maintenance.visit",
        "wex_it_service_visit_rel",
        "service_id",
        "visit_id",
        string="Actividades",
    )

    @api.constrains("partner_id")
    def _check_partner_id(self):
        for service in self:
            if service.partner_id and not service.partner_id.x_is_it_maintenance_customer:
                raise ValidationError("El cliente seleccionado no está habilitado para mantenimiento IT.")
            if service.partner_id.company_id and service.company_id != service.partner_id.company_id:
                raise ValidationError("La compañía del servicio debe coincidir con la del cliente.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner = self.env["res.partner"].browse(vals["partner_id"]) if vals.get("partner_id") else False
            if partner and not vals.get("company_id"):
                vals["company_id"] = partner.company_id.id or self.env.company.id
        return super().create(vals_list)
