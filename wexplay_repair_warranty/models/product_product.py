# -*- coding: utf-8 -*-

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_add_to_purchase_list(self):
        self.ensure_one()
        return self.product_tmpl_id.action_add_to_purchase_list()
