from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_condition = fields.Selection(
        [
            ("new", "Nuevo"),
            ("refurbished", "Reacondicionado"),
            ("used", "Usado"),
        ],
        string="Estado Wexplay",
        default="new",
        index=True,
    )
    wex_teardown_component_id = fields.Many2one(
        "wex.teardown.component.type",
        string="Componente de despiece",
        ondelete="restrict",
    )
    wex_teardown_part_number = fields.Char(string="Part number de despiece", index=True)
    wex_teardown_model_id = fields.Many2one(
        "wex.repair.device_model",
        string="Modelo SAT",
        ondelete="restrict",
    )
    wex_teardown_brand_id = fields.Many2one(
        related="wex_teardown_model_id.brand_id",
        string="Marca SAT",
        store=True,
        readonly=True,
    )
    wex_teardown_device_type = fields.Selection(
        related="wex_teardown_model_id.device_type",
        string="Tipo de dispositivo SAT",
        store=True,
        readonly=True,
    )
