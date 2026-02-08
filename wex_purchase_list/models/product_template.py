from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="Precio con IVA",
        currency_field="currency_id",
        compute="_compute_wex_list_price_tax_included",
        inverse="_inverse_wex_list_price_tax_included",
        help="Introduce el precio final con impuestos. Odoo recalcula automáticamente el Precio de venta (sin IVA).",
    )

    @api.depends("list_price", "taxes_id", "currency_id")
    def _compute_wex_list_price_tax_included(self):
        for rec in self:
            if not rec.currency_id:
                rec.wex_list_price_tax_included = rec.list_price
                continue

            if not rec.taxes_id:
                rec.wex_list_price_tax_included = rec.currency_id.round(rec.list_price or 0.0)
                continue

            taxes_res = rec.taxes_id.compute_all(
                rec.list_price or 0.0,
                currency=rec.currency_id,
                quantity=1.0,
                product=rec.product_variant_id,
                partner=False,
                is_refund=False,
                handle_price_include=False,
            )
            rec.wex_list_price_tax_included = rec.currency_id.round(taxes_res["total_included"])

    def _inverse_wex_list_price_tax_included(self):
        for rec in self:
            if not rec.currency_id:
                rec.list_price = rec.wex_list_price_tax_included
                continue

            price_inc = rec.wex_list_price_tax_included or 0.0

            if not rec.taxes_id:
                rec.list_price = rec.currency_id.round(price_inc)
                continue

            taxes_res = rec.taxes_id.compute_all(
                price_inc,
                currency=rec.currency_id,
                quantity=1.0,
                product=rec.product_variant_id,
                partner=False,
                is_refund=False,
                handle_price_include=True,  # <- el input es "con IVA"
            )
            rec.list_price = rec.currency_id.round(taxes_res["total_excluded"])
