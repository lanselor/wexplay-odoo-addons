import math

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_list_price_tax_included = fields.Monetary(
        string="Precio con IVA",
        currency_field="currency_id",
        compute="_compute_wex_list_price_tax_included",
        inverse="_inverse_wex_list_price_tax_included",
        store=False,
        help="Introduce el precio con IVA para recalcular el precio base.",
    )

    # NUEVO: margen real sobre PVP (margen sobre venta)
    wex_margin_percent = fields.Float(
        string="Margen (%)",
        default=15.0,
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

    def _round_currency(self, amount):
        self.ensure_one()
        return self.currency_id.round(amount) if self.currency_id else amount

    def _round_commercial_price(self, amount):
        """Redondeo comercial Wexplay: siempre hacia arriba al siguiente 0 o 5."""
        if not amount:
            return 0.0
        return math.ceil(amount / 5.0) * 5.0

    def _get_price_tax_included(self, base_price):
        self.ensure_one()
        if not self.taxes_id:
            return self._round_currency(base_price)

        taxes_res = self.taxes_id.compute_all(
            base_price,
            product=self.product_variant_id,
            currency=self.currency_id,
            quantity=1.0,
        )
        return self._round_currency(taxes_res["total_included"])

    def _get_tax_included_ratio(self):
        self.ensure_one()
        if not self.taxes_id:
            return 1.0

        taxes_res = self.taxes_id.compute_all(
            1.0,
            product=self.product_variant_id,
            currency=self.currency_id,
            quantity=1.0,
        )
        return taxes_res["total_included"] or 1.0

    def _get_price_tax_excluded(self, tax_included_price):
        self.ensure_one()
        if not self.taxes_id:
            return self._round_currency(tax_included_price)

        base_price = tax_included_price / self._get_tax_included_ratio()
        return self._round_currency(base_price)

    def _get_suggested_base_price_from_margin(self):
        self.ensure_one()
        cost = self.standard_price or 0.0
        margin = (self.wex_margin_percent or 0.0) / 100.0
        if not cost or margin >= 1.0:
            return 0.0
        return cost / (1.0 - margin)

    def _get_suggested_price_tax_included(self):
        self.ensure_one()
        base_price = self._get_suggested_base_price_from_margin()
        if not base_price:
            return 0.0
        return self._round_commercial_price(self._get_price_tax_included(base_price))

    @api.depends("list_price", "taxes_id", "currency_id", "product_variant_id")
    def _compute_wex_list_price_tax_included(self):
        for rec in self:
            rec.wex_list_price_tax_included = rec._get_price_tax_included(rec.list_price or 0.0)

    def _inverse_wex_list_price_tax_included(self):
        for rec in self:
            rec.list_price = rec._get_price_tax_excluded(rec.wex_list_price_tax_included or 0.0)

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

    @api.depends("standard_price", "wex_margin_percent", "taxes_id", "currency_id", "product_variant_id")
    def _compute_wex_suggested_price_tax_included(self):
        for rec in self:
            rec.wex_suggested_price_tax_included = rec._get_suggested_price_tax_included()

    @api.onchange("standard_price", "wex_margin_percent", "taxes_id")
    def _onchange_wex_pricing_inputs(self):
        for rec in self:
            rec.wex_suggested_price_tax_included = rec._get_suggested_price_tax_included()

    def action_apply_wex_suggested_price(self):
        for rec in self:
            suggested_price = rec._get_suggested_price_tax_included()
            if suggested_price:
                rec.write({
                    "list_price": rec._get_price_tax_excluded(suggested_price),
                })
        return True
