from odoo import fields, models

from odoo.addons.wexplay_repair.models.device_constants import DEVICE_TYPE_SELECTION


class WexTeardownNameRule(models.Model):
    _name = "wex.teardown.name.rule"
    _description = "Regla de nombre de despiece obsoleta"
    _order = "sequence, name"

    name = fields.Char(required=True)
    device_type = fields.Selection(DEVICE_TYPE_SELECTION, index=True)
    component_type_id = fields.Many2one("wex.teardown.component.type", ondelete="restrict")
    product_category_id = fields.Many2one("product.category", ondelete="restrict")
    pattern = fields.Char(default="{component} {part_number} para {device_type} {brand} {model}")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=False)
