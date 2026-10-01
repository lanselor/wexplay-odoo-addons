from odoo import api, fields, models, _
from odoo.exceptions import UserError


# Una identidad Python no puede fabricarse desde contexto RPC/importaciones.
_TEARDOWN_TOKEN = object()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    wex_teardown_origin_line_id = fields.Many2one(
        "wex.teardown.line", string="Pieza de origen", copy=False,
        readonly=True, ondelete="restrict", index=True,
        groups="wex_teardown.group_wex_teardown_user",
    )
    wex_teardown_preparation_state = fields.Selection(
        [("pending", "En preparación"), ("ready", "Preparación finalizada"),
         ("cancelled", "Preparación cancelada")],
        string="Preparación de despiece", readonly=True, copy=False, index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("_teardown_token") is not _TEARDOWN_TOKEN:
            if any(vals.get("wex_teardown_preparation_state") or vals.get("wex_teardown_origin_line_id") for vals in vals_list):
                raise UserError(_("Prepare el producto desde su despiece."))
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get("_teardown_token") is not _TEARDOWN_TOKEN:
            if {"wex_teardown_origin_line_id", "wex_teardown_preparation_state"} & vals.keys():
                raise UserError(_("La preparación se gestiona desde Despieces."))
            if vals.get("active") or vals.get("is_published") or vals.get("website_published"):
                if any(p.wex_teardown_preparation_state in ("pending", "cancelled") for p in self):
                    raise UserError(_("Finalice la pieza desde Despieces antes de activar o publicar el producto."))
        return super().write(vals)

    def _write_teardown_values(self, vals):
        return self.with_context(_teardown_token=_TEARDOWN_TOKEN).write(vals)

    def action_open_teardown_origin(self):
        self.ensure_one()
        line = self.wex_teardown_origin_line_id
        line.check_access("read")
        return line.action_open_edit_form()


    wex_condition = fields.Selection(
        [
            ("new", "Nuevo"),
            ("refurbished", "Reacondicionado"),
            ("used", "Usado"),
        ],
        string="Estado Wexplay",
        default="new",
        index=True,
    )
    wex_teardown_component_id = fields.Many2one(
        "wex.teardown.component.type",
        string="Componente de despiece",
        ondelete="restrict",
    )
    wex_teardown_part_number = fields.Char(string="Part number de despiece", index=True)
    wex_teardown_model_id = fields.Many2one(
        "wex.repair.device_model",
        string="Modelo SAT",
        ondelete="restrict",
    )
    wex_teardown_brand_id = fields.Many2one(
        related="wex_teardown_model_id.brand_id",
        string="Marca SAT",
        store=True,
        readonly=True,
    )
    wex_teardown_device_type = fields.Selection(
        related="wex_teardown_model_id.device_type",
        string="Tipo de dispositivo SAT",
        store=True,
        readonly=True,
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("_teardown_token") is not _TEARDOWN_TOKEN:
            for vals in vals_list:
                template = self.env["product.template"].browse(vals.get("product_tmpl_id"))
                if vals.get("active", True) and template.wex_teardown_preparation_state in ("pending", "cancelled"):
                    raise UserError(_("No cree variantes activas de un producto pendiente de despiece."))
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("active") and self.env.context.get("_teardown_token") is not _TEARDOWN_TOKEN:
            if any(p.product_tmpl_id.wex_teardown_preparation_state in ("pending", "cancelled") for p in self):
                raise UserError(_("Finalice la pieza desde Despieces antes de activar su variante."))
        return super().write(vals)
