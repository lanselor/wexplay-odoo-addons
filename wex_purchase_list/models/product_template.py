from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="Precio con IVA",
        currency_field="currency_id",
        compute="_compute_wex_list_price_tax_included",
        inverse="_inverse_wex_list_price_tax_included",
        store=True, # Lo guardamos para evitar recálculos infinitos en UI
    )

    @api.depends("list_price", "taxes_id")
    def _compute_wex_list_price_tax_included(self):
        for rec in self:
            if rec.taxes_id:
                # Calculamos el precio CON impuestos partiendo de la base
                res = rec.taxes_id.compute_all(
                    rec.list_price,
                    product=rec.product_variant_id,
                    currency=rec.currency_id,
                    quantity=1.0
                )
                rec.wex_list_price_tax_included = res['total_included']
            else:
                rec.wex_list_price_tax_included = rec.list_price

    def _inverse_wex_list_price_tax_included(self):
        for rec in self:
            if rec.taxes_id:
                # PASO CLAVE: Marcamos los impuestos como "incluidos" temporalmente
                # para que compute_all haga la división (Precio / 1.21)
                taxes_included = rec.taxes_id.filtered(lambda t: t.amount_type == 'percent')
                
                # Simulamos que el impuesto YA está incluido para extraer la base
                # Usamos handle_price_include=True para que el resultado total_excluded sea la base real
                res = rec.taxes_id.with_context(force_price_include=True).compute_all(
                    rec.wex_list_price_tax_included,
                    product=rec.product_variant_id,
                    currency=rec.currency_id,
                    quantity=1.0,
                    handle_price_include=True
                )
                rec.list_price = res['total_excluded']
            else:
                rec.list_price = rec.wex_list_price_tax_included

    @api.onchange("wex_list_price_tax_included")
    def _onchange_wex_price_tax_included(self):
        # Esto permite que la UI se actualice al momento de escribir sin esperar a guardar
        self._inverse_wex_list_price_tax_included()