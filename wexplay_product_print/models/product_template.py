# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_get_zebra_label_payload(self):
        self.ensure_one()
        self.check_access("read")
        if not self.default_code:
            raise UserError(
                _("El producto necesita una referencia interna antes de imprimir la etiqueta Zebra.")
            )
        return {
            "document_code": "product_label_zebra",
            "report_name": "wexplay_product_print.report_product_label_zebra_76x25",
            "reference": self.default_code,
        }