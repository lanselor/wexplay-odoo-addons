from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="Precio con IVA",
        currency_field="currency_id",
        compute="_compute_wex_list_price_tax_included",
        inverse="_inverse_wex_list_price_tax_included",
        store=True,
        help="Introduce el precio con IVA para recalcular el precio base.",
    )

    @api.depends("list_price", "taxes_id", "currency_id")
    def _compute_wex_list_price_tax_included(self):
        for rec in self:
            if rec.taxes_id:
                # Calculamos el PVP (Base + IVA)
                res = rec.taxes_id.compute_all(
                    rec.list_price,
                    product=rec.product_variant_id,
                    currency=rec.currency_id,
                    quantity=1.0
                )
                # Redondeamos según la moneda para evitar decimales infinitos en UI
                rec.wex_list_price_tax_included = rec.currency_id.round(res['total_included'])
            else:
                rec.wex_list_price_tax_included = rec.list_price

    def _inverse_wex_list_price_tax_included(self):
        for rec in self:
            if rec.taxes_id:
                # Calculamos la proporción del IVA sin "forzar" el objeto impuesto.
                # Obtenemos cuánto IVA se añadiría a 1.0 unidad de base.
                dummy_res = rec.taxes_id.compute_all(
                    1.0, 
                    product=rec.product_variant_id, 
                    currency=rec.currency_id
                )
                
                # Ratio = Total con IVA / Base 1.0
                # Ejemplo: 1.21 si el IVA es 21%
                ratio = dummy_res['total_included'] 
                
                if ratio > 0:
                    base_price = rec.wex_list_price_tax_included / ratio
                    rec.list_price = rec.currency_id.round(base_price)
            else:
                rec.list_price = rec.wex_list_price_tax_included

    @api.onchange("wex_list_price_tax_included")
    def _onchange_wex_list_price_tax_included(self):
        """Dispara el recálculo visual inmediato sin esperar al guardado físico."""
        self._inverse_wex_list_price_tax_included()