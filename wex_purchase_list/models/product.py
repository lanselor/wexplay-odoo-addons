from odoo import fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_vendor_url = fields.Char(string="URL proveedor (Wexplay)")

    def action_add_to_purchase_list(self):
        self.ensure_one()

        if len(self.product_variant_ids) != 1:
            raise UserError(_("Este producto tiene varias variantes. Abre una variante concreta y añádela desde ahí."))

        qty = float(self.env.context.get("wex_qty", 1.0))

        result = self.env["wex_purchase_list.line"].add_from_origin(
            origin_model="product.template",
            origin_id=self.id,
            product_id=self.product_variant_ids[0].id,
            qty=qty,
            state="to_purchase",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OK"),
                "message": result.get("message") or _("Operación completada."),
                "type": "success",
                "sticky": False,
            }
        }


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_add_to_purchase_list(self):
        self.ensure_one()
        qty = float(self.env.context.get("wex_qty", 1.0))

        result = self.env["wex_purchase_list.line"].add_from_origin(
            origin_model="product.product",
            origin_id=self.id,
            product_id=self.id,
            qty=qty,
            state="to_purchase",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OK"),
                "message": result.get("message") or _("Operación completada."),
                "type": "success",
                "sticky": False,
            }
        }

    def action_apply_wex_suggested_price(self):
        for product in self:
            product.product_tmpl_id.action_apply_wex_suggested_price()
        return True
