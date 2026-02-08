from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_vendor_url = fields.Char(string="URL proveedor (Wexplay)")
