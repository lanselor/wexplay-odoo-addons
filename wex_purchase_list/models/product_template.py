from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="Precio con IVA",
        currency_field="currency_id",
        compute="_compute_wex_list_price_tax_included",
        inverse="_inverse_wex_list_price_tax_included",
        help="Introduce el precio final con IVA. Odoo recalcula la base (Precio de venta sin IVA).",
    )

    @api.depends("list_price", "taxes_id", "currency_id")
    def _compute_wex_list_price_tax_included(self):
        for rec in self:
            base = rec.list_price or 0.0

            if not rec.currency_id:
                rec.wex_list_price_tax_included = base
                continue

            if not rec.taxes_id:
                rec.wex_list_price_tax_included = rec.currency_id.round(base)
                continue

            taxes = rec.taxes_id.compute_all(
                base,
                currency=rec.currency_id,
                quantity=1.0,
                product=rec.product_variant_id,
                partner=False,
                is_refund=False,
                handle_price_include=False,  # base sin IVA
            )
            rec.wex_list_price_tax_included = rec.currency_id.round(taxes["total_included"])

    def _inverse_wex_list_price_tax_included(self):
        for rec in self:
            price_inc = rec.wex_list_price_tax_included or 0.0

            if not rec.currency_id:
                rec.list_price = price_inc
                continue

            if not rec.taxes_id:
                rec.list_price = rec.currency_id.round(price_inc)
                continue

            res = rec.taxes_id.compute_all(
                price_inc,
                currency=rec.currency_id,
                quantity=1.0,
                product=rec.product_variant_id,
                partner=False,
                is_refund=False,
                handle_price_include=True,  # input con IVA
            )
            rec.list_price = rec.currency_id.round(res["total_excluded"])
