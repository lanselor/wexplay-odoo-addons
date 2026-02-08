from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="Precio con IVA",
        currency_field="currency_id",
        compute="_compute_wex_list_price_tax_included",
        inverse="_inverse_wex_list_price_tax_included",
        store=False, # No necesitamos guardarlo en DB, es un ayudante de cálculo
        help="Introduce el precio final con impuestos. Odoo recalcula automáticamente el Precio de venta (sin IVA).",
    )

    @api.depends("list_price", "taxes_id")
    def _compute_wex_list_price_tax_included(self):
        """Calcula el precio CON IVA basándose en el precio base (list_price)."""
        for rec in self:
            if rec.taxes_id:
                # Calculamos el total incluido
                taxes = rec.taxes_id.compute_all(
                    rec.list_price, 
                    rec.currency_id, 
                    1.0, 
                    product=rec.product_variant_id, 
                    partner=False
                )
                rec.wex_list_price_tax_included = taxes['total_included']
            else:
                rec.wex_list_price_tax_included = rec.list_price

    def _inverse_wex_list_price_tax_included(self):
        """Cuando escribes en 'Precio con IVA', extrae el IVA y actualiza 'list_price'."""
        for rec in self:
            if rec.taxes_id:
                # El truco está en 'price_include=True' para que Odoo entienda 
                # que el valor que le damos ya tiene el impuesto dentro.
                # 'total_excluded' nos dará la base imponible.
                taxes = rec.taxes_id.compute_all(
                    rec.wex_list_price_tax_included, 
                    rec.currency_id, 
                    1.0, 
                    product=rec.product_variant_id, 
                    partner=False,
                    handle_price_include=True # Crucial para restar el IVA
                )
                rec.list_price = taxes['total_excluded']
            else:
                rec.list_price = rec.wex_list_price_tax_included