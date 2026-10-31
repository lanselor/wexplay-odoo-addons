from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    wex_return_location_id = fields.Many2one(
        "stock.location", string="Ubicación de devoluciones", check_company=True,
        domain="[('usage', '=', 'internal'), ('company_id', '=', id)]",
        ondelete="restrict",
    )

    @api.constrains("wex_return_location_id")
    def _check_wex_return_location(self):
        for company in self:
            location = company.wex_return_location_id
            if not location:
                continue
            if not location.active or location.scrap_location or location.usage != "internal" or location.company_id != company:
                raise ValidationError(_("La ubicación de devoluciones debe estar activa, ser interna, no ser de desecho y pertenecer a la compañía."))
            warehouses = self.env["stock.warehouse"].search([("company_id", "=", company.id)])
            if location and any(
                location.parent_path.startswith(warehouse.lot_stock_id.parent_path)
                for warehouse in warehouses if warehouse.lot_stock_id.parent_path
            ):
                raise ValidationError(_("La ubicación de devoluciones debe estar fuera de las ubicaciones de stock de los almacenes."))
            repair_types = self.env["stock.picking.type"].search([
                ("company_id", "=", company.id), ("code", "=", "repair_operation"),
            ])
            if any(
                source.usage == "internal" and source.parent_path
                and location.parent_path.startswith(source.parent_path)
                for source in repair_types.default_location_src_id
            ):
                raise ValidationError(_("La ubicación de devoluciones debe estar fuera de las ubicaciones de suministro de reparaciones."))

    def _ensure_wex_return_location(self):
        parent = self.env.ref("stock.stock_location_locations")
        for company in self.filtered(lambda item: not item.wex_return_location_id):
            location = self.env["stock.location"].create({
                "name": _("Devoluciones a proveedor"),
                "usage": "internal",
                "location_id": parent.id,
                "company_id": company.id,
            })
            company.wex_return_location_id = location

    @api.model
    def _initialize_wex_return_locations(self):
        self.search([])._ensure_wex_return_location()

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._ensure_wex_return_location()
        return companies
