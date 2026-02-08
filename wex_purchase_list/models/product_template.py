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

    def _wex_get_tax_product(self):
        self.ensure_one()
        # En template a veces product_variant_id no está listo; usar el primero disponible
        return self.product_variant_id or self.product_variant_ids[:1]

    @api.onchange("wex_list_price_tax_included", "taxes_id", "currency_id")
    def _onchange_wex_list_price_tax_included(self):
        """Actualizar list_price en pantalla al editar Precio con IVA."""
        for rec in self:
            if not rec.currency_id:
                continue

            price_inc = rec.wex_list_price_tax_included
            if price_inc is False:
                continue

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
                handle_price_include=True,
            )
            rec.list_price = rec.currency_id.round(taxes_res["total_excluded"])

    @api.depends("list_price", "taxes_id", "currency_id")
    def _compute_wex_list_price_tax_included(self):
        for rec in self:
            if not rec.currency_id:
                rec.wex_list_price_tax_included = rec.list_price
                continue
            if not rec.taxes_id:
                rec.wex_list_price_tax_included = rec.curre
