from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="Precio con IVA",
        currency_field="currency_id",
        compute="_compute_wex_list_price_tax_included",
        inverse="_inverse_wex_list_price_tax_included",
        help="Introduce el precio final con impuestos. Odoo calculará la base.",
    )

    @api.depends("list_price", "taxes_id")
    def _compute_wex_list_price_tax_included(self):
        for rec in self:
            # Si no hay impuestos, el precio con IVA es igual al precio de venta
            if not rec.taxes_id:
                rec.wex_list_price_tax_included = rec.list_price
                continue
            
            # Calculamos el precio con IVA a partir del list_price (Base)
            taxes = rec.taxes_id.compute_all(
                rec.list_price,
                currency=rec.currency_id,
                quantity=1.0,
                product=rec.product_variant_id,
            )
            rec.wex_list_price_tax_included = taxes['total_included']

    @api.onchange("wex_list_price_tax_included")
    def _inverse_wex_list_price_tax_included(self):
        for rec in self:
            if rec.wex_list_price_tax_included:
                if rec.taxes_id:
                    # Forzamos a Odoo a tratar los impuestos como 'incluidos' 
                    # solo para este cálculo de desglose temporal
                    taxes_to_calculate = rec.taxes_id.with_context(force_price_include=True)
                    
                    res = taxes_to_calculate.compute_all(
                        rec.wex_list_price_tax_included,
                        currency=rec.currency_id,
                        quantity=1.0,
                        product=rec.product_variant_id,
                        handle_price_include=True
                    )
                    # El total_excluded es la base imponible real
                    rec.list_price = res['total_excluded']
                else:
                    rec.list_price = rec.wex_list_price_tax_included