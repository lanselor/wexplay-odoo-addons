from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="Precio con IVA",
        currency_field="currency_id",
        compute="_compute_wex_list_price_tax_included",
        inverse="_inverse_wex_list_price_tax_included",
        store=True,
        help="Introduce el precio final con IVA. Odoo recalcula el Precio de venta (sin IVA).",
    )

    @api.depends("list_price", "taxes_id", "currency_id")
    def _compute_wex_list_price_tax_included(self):
        for rec in self:
            currency = rec.currency_id
            base = rec.list_price or 0.0

            if not currency:
                rec.wex_list_price_tax_included = base
                continue

            if not rec.taxes_id:
                rec.wex_list_price_tax_included = currency.round(base)
                continue

            res = rec.taxes_id.compute_all(
                base,
                currency=currency,
                quantity=1.0,
                product=rec.product_variant_id,
                partner=False,
                is_refund=False,
                handle_price_include=False,  # list_price es base sin IVA
            )
            rec.wex_list_price_tax_included = currency.round(res["total_included"])

    def _inverse_wex_list_price_tax_included(self):
        for rec in self:
            currency = rec.currency_id
            price_inc = rec.wex_list_price_tax_included or 0.0

            if not currency:
                rec.list_price = price_inc
                continue

            if not rec.taxes_id:
                rec.list_price = currency.round(price_inc)
                continue

            # El input es "precio final con impuestos".
            # Para extraer la base, compute_all debe tratar el input como "price_include".
            # En vez de forzar contextos globales, usamos handle_price_include=True.
            res = rec.taxes_id.compute_all(
                price_inc,
                currency=currency,
                quantity=1.0,
                product=rec.product_variant_id,
                partner=False,
                is_refund=False,
                handle_price_include=True,
            )
            rec.list_price = currency.round(res["total_excluded"])

    @api.onchange("wex_list_price_tax_included")
    def _onchange_wex_price_tax_included(self):
        # UX: aplicar al momento en formulario
        self._inverse_wex_list_price_tax_included()
