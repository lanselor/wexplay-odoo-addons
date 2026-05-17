import unicodedata
from string import Formatter

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import ustr

from odoo.addons.wexplay_repair.models.device_constants import DEVICE_TYPE_SELECTION


class WexTeardownComponentType(models.Model):
    _name = "wex.teardown.component.type"
    _description = "Componente de despiece"
    _order = "device_type, sequence, name"

    name = fields.Char(string="Nombre", required=True, translate=True)
    device_type = fields.Selection(DEVICE_TYPE_SELECTION, string="Tipo de dispositivo", required=True, index=True)
    code = fields.Char(string="Código", readonly=True, copy=False, index=True)
    product_category_id = fields.Many2one(
        "product.category",
        string="Categoría de producto",
        required=True,
        ondelete="restrict",
    )
    name_pattern = fields.Char(
        string="Patrón de nombre",
        required=True,
        default="{component} {part_number} para {device_type} {brand} {model}",
        help="Variables disponibles: {component}, {part_number}, {device_type}, {brand}, {model}.",
    )
    sequence = fields.Integer(string="Secuencia", default=10)
    active = fields.Boolean(string="Activo", default=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "Ya existe un componente con ese código."),
        (
            "device_name_unique",
            "unique(device_type, name)",
            "Ya existe un componente con ese nombre para este tipo de dispositivo.",
        ),
    ]

    _ALLOWED_NAME_PATTERN_KEYS = {
        "component",
        "part_number",
        "device_type",
        "brand",
        "model",
    }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["code"] = self._make_component_code(vals.get("device_type"), vals.get("name"))
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "name" in vals or "device_type" in vals:
            for rec in self:
                rec.code = rec._make_component_code(rec.device_type, rec.name)
        return res

    @api.model
    def _make_component_code(self, device_type, name):
        device = device_type or "component"
        slug = self._slugify(name or "component")
        return f"{device}_{slug}"

    @api.model
    def _slugify(self, value):
        text = ustr(value).strip().lower()
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        chars = []
        previous_sep = False
        for char in normalized:
            if char.isalnum():
                chars.append(char)
                previous_sep = False
            elif not previous_sep:
                chars.append("_")
                previous_sep = True
        return "".join(chars).strip("_") or "component"

    @api.constrains("name_pattern")
    def _check_name_pattern(self):
        for rec in self:
            unknown_keys = rec._get_unknown_pattern_keys()
            if unknown_keys:
                raise ValidationError(
                    _(
                        "El patron de nombre contiene variables no permitidas: %s.\n"
                        "Variables permitidas: {component}, {part_number}, {device_type}, {brand}, {model}."
                    )
                    % ", ".join("{%s}" % key for key in sorted(unknown_keys))
                )
            try:
                (rec.name_pattern or "").format(
                    component="",
                    part_number="",
                    device_type="",
                    brand="",
                    model="",
                )
            except (KeyError, ValueError) as error:
                raise ValidationError(_("El patrón de nombre no es válido: %s") % error)

    def _get_unknown_pattern_keys(self):
        self.ensure_one()
        keys = set()
        for _, field_name, _, _ in Formatter().parse(self.name_pattern or ""):
            if field_name:
                keys.add(field_name.split(".", 1)[0].split("[", 1)[0])
        return keys - self._ALLOWED_NAME_PATTERN_KEYS

    def render_product_name(self, line):
        self.ensure_one()
        values = line._get_name_values()
        return " ".join((self.name_pattern or "").format(**values).split())
