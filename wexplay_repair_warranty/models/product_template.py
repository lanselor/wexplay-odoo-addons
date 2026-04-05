# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_warranty_parts_months = fields.Integer(
        string="Meses garantía piezas",
        default=6,
    )
    x_warranty_labor_months = fields.Integer(
        string="Meses garantía mano de obra",
        default=6,
    )

    @api.constrains("x_warranty_parts_months", "x_warranty_labor_months")
    def _check_warranty_months_non_negative(self):
        for product in self:
            if product.x_warranty_parts_months < 0:
                raise ValidationError(_("Los meses de garantía de piezas no pueden ser negativos."))
            if product.x_warranty_labor_months < 0:
                raise ValidationError(_("Los meses de garantía de mano de obra no pueden ser negativos."))
