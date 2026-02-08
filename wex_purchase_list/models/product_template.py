from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="Precio con IVA",
        currency_field="currency_id",
        help="Introduce el precio final con IVA. Se recalculará el Precio de venta (sin IVA).",
    )

    def _wex_get_tax_product(self):
        self.ensure_one()
        # En template, mejor pasar una variante existente si la hay
        return self.product_variant_id or self.product_variant_ids[:1]

    @api.onchange("wex_list_price_tax_included", "taxes_id", "currency_id")
    def _onchange_wex_list_price_tax_included(self):
        """
        Entrada: precio con IVA (wex_list_price_tax_included)
        Salida: list_price (sin IVA)
        """
        for rec in self:
            if rec.wex_list_price_tax_included is False:
                continue
            if not rec.currency_id:
                continue

            price_inc = rec.wex_list_price_tax_included or 0.0

            # Si no hay impuestos, el precio sin IVA es igual
            if not rec.taxes_id:
                rec.list_price = rec.currency_id.round(price_inc)
                continue

            product = rec._wex_get_tax_product()
            taxes_res = rec.taxes_id.compute_all(
                price_inc,
                currency=rec.currency_id,
                quantity=1.0,
                product=product,
                partner=False,
                is_refund=False,
                handle_price_include=True,  # input es con IVA
            )
            rec.list_price = rec.currency_id.round(taxes_res["total_excluded"])
