from odoo import api, models, _
from odoo.exceptions import AccessError


class ProductImage(models.Model):
    _inherit = "product.image"

    def _check_teardown_media_owner(self):
        if not self.env.user.has_group("wex_teardown.group_wex_teardown_user"):
            return
        for image in self:
            product = image.product_tmpl_id or image.product_variant_id.product_tmpl_id
            if not product:
                raise AccessError(_("Vincule la imagen a un producto."))
            product.check_access("write")
            if product.company_id and product.company_id not in self.env.companies:
                raise AccessError(_("La imagen pertenece a un producto de otra compañía."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_teardown_media_owner()
        return records

    def write(self, vals):
        self._check_teardown_media_owner()
        result = super().write(vals)
        self._check_teardown_media_owner()
        return result

    def unlink(self):
        self._check_teardown_media_owner()
        return super().unlink()
