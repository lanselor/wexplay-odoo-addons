from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="PVP (con IVA)",
        currency_field="currency_id",
        help="Campo auxiliar: al introducirlo, recalcula el Precio de venta (sin IVA).",
    )

    @api.onchange("wex_list_price_tax_included", "taxes_id", "currency_id")
    def _onchange_wex_list_price_tax_included(self):
        """
        Si el usuario introduce PVP con IVA, recalcula list_price (sin IVA)
        usando impuestos de ventas del producto.
        """
        for rec in self:
            if rec.wex_list_price_tax_included is False:
                continue

            # Si no hay impuestos, el precio sin IVA es el mismo
            if not rec.taxes_id:
                rec.list_price = rec.wex_list_price_tax_included
                continue

            # Usar motor fiscal de Odoo para calcular base sin IVA
            # compute_all: pasar price_include=True para tratar el input como "con IVA"
            taxes_res = rec.taxes_id.compute_all(
                rec.wex_list_price_tax_included,
                currency=rec.currency_id,
                quantity=1.0,
                product=rec.product_variant_id,
                partner=False,
                is_refund=False,
                handle_price_include=True,
            )

            # total_excluded es base sin IVA
            rec.list_price = rec.currency_id.round(taxes_res["total_excluded"])

    @api.onchange("list_price", "taxes_id", "currency_id")
    def _onchange_list_price_to_wex_tax_included(self):
        """
        Si cambia list_price o impuestos, recalcula el campo auxiliar PVP con IVA.
        """
        for rec in self:
            if not rec.list_price:
                rec.wex_list_price_tax_included = rec.list_price
                continue

            if not rec.taxes_id:
                rec.wex_list_price_tax_included = rec.list_price
                continue

            taxes_res = rec.taxes_id.compute_all(
                rec.list_price,
                currency=rec.currency_id,
                quantity=1.0,
                product=rec.product_variant_id,
                partner=False,
                is_refund=False,
                handle_price_include=False,
            )

            rec.wex_list_price_tax_included = rec.currency_id.round(taxes_res["total_included"])
