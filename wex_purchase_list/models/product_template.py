from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="Precio con IVA",
        currency_field="currency_id",
        compute="_compute_wex_list_price_tax_included",
        inverse="_inverse_wex_list_price_tax_included",
        help="Introduce el precio final. Odoo extraerá la base usando el motor fiscal.",
    )

    @api.depends("list_price", "taxes_id", "currency_id")
    def _compute_wex_list_price_tax_included(self):
        for rec in self:
            # Cálculo estándar: Base -> Total
            taxes_res = rec.taxes_id.compute_all(
                rec.list_price,
                currency=rec.currency_id,
                quantity=1.0,
                product=rec.product_variant_id,
            )
            rec.wex_list_price_tax_included = taxes_res['total_included']

    def _inverse_wex_list_price_tax_included(self):
        for rec in self:
            if rec.taxes_id:
                # CLAVE: Para que handle_price_include funcione, los impuestos 
                # evaluados DEBEN tener el atributo price_include = True.
                # Lo hacemos en memoria sin tocar la base de datos.
                taxes_to_calculate = rec.taxes_id.mapped(
                    lambda t: t.with_context(force_price_include=True)
                )
                
                # Cálculo inverso: Total -> Base
                taxes_res = taxes_to_calculate.compute_all(
                    rec.wex_list_price_tax_included,
                    currency=rec.currency_id,
                    quantity=1.0,
                    product=rec.product_variant_id,
                    handle_price_include=True  # Odoo ahora sí sabe qué hacer
                )
                # total_excluded es la base imponible exacta según el motor de Odoo
                rec.list_price = taxes_res['total_excluded']
            else:
                rec.list_price = rec.wex_list_price_tax_included

    @api.onchange("wex_list_price_tax_included")
    def _onchange_wex_list_price_tax_included(self):
        """Permite ver el cambio en list_price antes de guardar."""
        self._inverse_wex_list_price_tax_included()