from odoo import api, fields, models
from odoo.exceptions import ValidationError


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

    # NUEVO: margen real sobre PVP (margen sobre venta)
    wex_margin_percent = fields.Float(
        string="Margen (%)",
        default=0.0,
        help="Margen real sobre PVP (margen sobre venta). "
             "Base sugerida (sin IVA) = Coste / (1 - margen/100).",
    )

    # NUEVO: sugerencia de precio (mostrada con IVA incluido)
    wex_suggested_price_tax_included = fields.Monetary(
        string="Sugerencia de precio (IVA incl.)",
        currency_field="currency_id",
        compute="_compute_wex_suggested_price_tax_included",
        store=False,
        readonly=True,
        help="Precio sugerido aplicando el margen sobre venta al coste y mostrando el total con IVA.",
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
                rec.wex_list_price_tax_included = rec.currency_id.round(res["total_included"])
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
                ratio = dummy_res["total_included"]

                if ratio > 0:
                    base_price = rec.wex_list_price_tax_included / ratio
                    rec.list_price = rec.currency_id.round(base_price)
            else:
                rec.list_price = rec.wex_list_price_tax_included

    @api.onchange("wex_list_price_tax_included")
    def _onchange_wex_list_price_tax_included(self):
        """Dispara el recálculo visual inmediato sin esperar al guardado físico."""
        self._inverse_wex_list_price_tax_included()

    # --------------------------
    # NUEVO: Margen y sugerencia
    # --------------------------

    @api.constrains("wex_margin_percent")
    def _check_wex_margin_percent(self):
        for rec in self:
            if rec.wex_margin_percent >= 100.0:
                raise ValidationError("El margen (%) debe ser menor que 100.")
            if rec.wex_margin_percent < 0.0:
                raise ValidationError("El margen (%) no puede ser negativo.")

    @api.depends("standard_price", "wex_margin_percent", "taxes_id", "currency_id")
    def _compute_wex_suggested_price_tax_included(self):
        for rec in self:
            currency = rec.currency_id
            if not currency:
                rec.wex_suggested_price_tax_included = 0.0
                continue

            cost = rec.standard_price or 0.0
            m = (rec.wex_margin_percent or 0.0) / 100.0

            # Base sugerida (sin IVA) según margen real sobre PVP:
            # base = coste / (1 - m)
            if m >= 1.0 or not cost:
                rec.wex_suggested_price_tax_included = 0.0
                continue

            base_suggested = cost / (1.0 - m)

            # Si no hay impuestos de venta, el "IVA incl." coincide con la base
            if not rec.taxes_id:
                rec.wex_suggested_price_tax_included = currency.round(base_suggested)
                continue

            taxes_res = rec.taxes_id.compute_all(
                base_suggested,
                currency=currency,
                quantity=1.0,
                product=rec.product_variant_id,
            )
            rec.wex_suggested_price_tax_included = currency.round(taxes_res["total_included"])
