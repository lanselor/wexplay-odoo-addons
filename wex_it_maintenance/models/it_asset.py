import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WexItAsset(models.Model):
    _name = "wex.it.asset"
    _description = "Activo IT Wex"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id, internal_code, id"

    ASSET_TYPE_SELECTION = [
        ("desktop", "Sobremesa"),
        ("laptop", "Portátil"),
        ("monitor", "Monitor"),
        ("printer", "Impresora"),
        ("smartphone", "Smartphone"),
        ("tablet", "Tablet"),
        ("nas", "NAS"),
        ("server", "Servidor"),
        ("router", "Router"),
        ("switch", "Switch"),
        ("access_point", "Punto de acceso"),
        ("peripheral", "Periférico"),
        ("other", "Otro"),
    ]

    STATUS_SELECTION = [
        ("draft", "Borrador"),
        ("in_use", "En uso"),
        ("maintenance", "En mantenimiento"),
        ("issue", "Con incidencia"),
        ("retired", "Retirado"),
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
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    asset_type = fields.Selection(selection=ASSET_TYPE_SELECTION, string="Tipo de activo", required=True, tracking=True)
    serial_number = fields.Char(string="Número de serie")
    internal_code = fields.Char(string="Código interno", copy=False, index=True, readonly=True)
    manufacturer = fields.Char(string="Fabricante")
    model = fields.Char(string="Modelo")
    location_within_customer = fields.Char(string="Ubicación dentro del cliente")
    assigned_user = fields.Char(string="Usuario asignado")
    purchase_date = fields.Date(string="Fecha de compra")
    warranty_end_date = fields.Date(string="Fin de garantía")
    status = fields.Selection(selection=STATUS_SELECTION, default="in_use", required=True, tracking=True)
    notes = fields.Text(string="Notas")
    active = fields.Boolean(string="Activo", default=True)
    cpu = fields.Char(string="CPU")
    ram = fields.Char(string="RAM")
    storage = fields.Char(string="Disco")
    operating_system = fields.Char(string="Sistema operativo")
    ip_address = fields.Char(string="Dirección IP")
    mac_address = fields.Char(string="Dirección MAC")
    technical_observations = fields.Text(string="Observaciones técnicas")
    review_ids = fields.One2many("wex.it.asset.review", "asset_id", string="Revisiones")
    credential_ids = fields.One2many("wex.it.credential", "asset_id", string="Credenciales")
    visit_line_ids = fields.One2many("wex.it.maintenance.visit.line", "asset_id", string="Líneas de actividad")
    review_count = fields.Integer(compute="_compute_related_counts")
    credential_count = fields.Integer(compute="_compute_related_counts")

    _sql_constraints = [
        ("wex_it_asset_internal_code_company_uniq", "unique(company_id, internal_code)", "El código interno debe ser único por compañía."),
    ]

    @api.depends("review_ids", "credential_ids")
    def _compute_related_counts(self):
        for asset in self:
            asset.review_count = len(asset.review_ids)
            asset.credential_count = len(asset.credential_ids)

    @api.constrains("partner_id")
    def _check_partner_id(self):
        for asset in self:
            if asset.partner_id and not asset.partner_id.x_is_it_maintenance_customer:
                raise ValidationError("El cliente seleccionado no está habilitado para mantenimiento IT.")
            if asset.partner_id.company_id and asset.company_id != asset.partner_id.company_id:
                raise ValidationError("La compañía del activo debe coincidir con la del cliente.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner = self.env["res.partner"].browse(vals["partner_id"]) if vals.get("partner_id") else False
            if not vals.get("company_id"):
                vals["company_id"] = partner.company_id.id or self.env.company.id
            if not vals.get("internal_code") and vals.get("partner_id") and vals.get("asset_type"):
                vals["internal_code"] = self._generate_internal_code(
                    vals["partner_id"],
                    vals["asset_type"],
                    vals["company_id"],
                )
        records = super().create(vals_list)
        for record in records.filtered(lambda asset: not asset.internal_code):
            record.internal_code = record._generate_internal_code(record.partner_id.id, record.asset_type, record.company_id.id)
        return records

    @api.model
    def _asset_type_code_map(self):
        return {
            "desktop": "PC",
            "laptop": "PORT",
            "monitor": "MON",
            "printer": "PRN",
            "smartphone": "PHONE",
            "tablet": "TAB",
            "nas": "NAS",
            "server": "SRV",
            "router": "RTR",
            "switch": "SWT",
            "access_point": "AP",
            "peripheral": "PER",
            "other": "OTH",
        }

    @api.model
    def _get_internal_code_prefix(self, partner, asset_type):
        customer_prefix = partner._get_it_customer_code_prefix()
        asset_type_code = self._asset_type_code_map().get(asset_type, "AST")
        return f"{customer_prefix}-{asset_type_code}"

    @api.model
    def _get_next_internal_code_number(self, partner_id, asset_type, company_id):
        partner = self.env["res.partner"].browse(partner_id)
        code_prefix = self._get_internal_code_prefix(partner, asset_type)
        domain = [
            ("company_id", "=", company_id),
            ("partner_id", "=", partner.id),
            ("asset_type", "=", asset_type),
            ("internal_code", "=like", f"{code_prefix}-%"),
        ]
        last_asset = self.search(domain, order="internal_code desc, id desc", limit=1)
        next_number = 1
        if last_asset and last_asset.internal_code:
            match = re.search(r"-(\d+)$", last_asset.internal_code)
            if match:
                next_number = int(match.group(1)) + 1
        return next_number

    @api.model
    def _generate_internal_code(self, partner_id, asset_type, company_id):
        partner = self.env["res.partner"].browse(partner_id)
        code_prefix = self._get_internal_code_prefix(partner, asset_type)
        next_number = self._get_next_internal_code_number(partner_id, asset_type, company_id)
        return f"{code_prefix}-{next_number:03d}"
