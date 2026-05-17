from odoo import api, fields, models

from odoo.addons.wexplay_repair.models.device_constants import DEVICE_TYPE_SELECTION


class WexTeardownCategoryRule(models.Model):
    _name = "wex.teardown.category.rule"
    _description = "Regla de categoria de despiece obsoleta"
    _order = "sequence, device_type, component_type_id"

    name = fields.Char(compute="_compute_name", store=True)
    device_type = fields.Selection(DEVICE_TYPE_SELECTION, index=True)
    component_type_id = fields.Many2one("wex.teardown.component.type", ondelete="restrict")
    product_category_id = fields.Many2one("product.category", string="Categoria de producto", ondelete="restrict")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=False)

    @api.depends("device_type", "component_type_id", "product_category_id")
    def _compute_name(self):
        selection = dict(DEVICE_TYPE_SELECTION)
        for rec in self:
            device = selection.get(rec.device_type, rec.device_type or "")
            component = rec.component_type_id.name or ""
            category = rec.product_category_id.complete_name or rec.product_category_id.name or ""
            rec.name = " / ".join(part for part in [device, component, category] if part)
