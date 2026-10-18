import base64
import math

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import file_open

from .device_constants import DEVICE_INSPECTION_TYPES


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_device_description = fields.Text(string="Descripción del dispositivo")
    x_device_condition_ids = fields.Many2many(
        "wex.repair.device.condition",
        string="Estado del dispositivo",
        groups="base.group_user",
        copy=False,
    )
    x_device_inspection_marks = fields.Json(
        string="Marcas de inspección",
        groups="base.group_user",
        copy=False,
    )

    @api.model
    def get_device_inspection_diagrams(self):
        self.check_access("read")
        diagrams = {
            device_type: {
                "front": _("Pantalla y teclado") if device_type == "laptop" else _("Frontal"),
                "back": _("Parte inferior") if device_type == "laptop" else _("Trasera"),
            }
            for device_type in DEVICE_INSPECTION_TYPES
        }
        diagrams["console"]["formats"] = [
            {"value": value, "label": label, "image_prefix": "console_%s" % value}
            for value, label in self._get_console_inspection_formats().items()
        ]
        return diagrams

    @api.model
    def _get_console_inspection_formats(self):
        return {
            "desktop": _("Sobremesa"),
            "classic_handheld": _("Portátil clásica"),
            "handheld_pc": _("PC de mano"),
        }

    def write(self, values):
        if "x_device_type" not in values:
            return super().write(values)
        self.check_access("write")
        changed = self.filtered(lambda repair: repair.x_device_type != values["x_device_type"])
        unchanged = self - changed
        result = True
        if changed:
            result = super(RepairOrder, changed).write(
                self._prepare_inspection_type_change_values(values)
            )
        if unchanged:
            result = super(RepairOrder, unchanged).write(values) and result
        return result

    @api.model
    def _prepare_inspection_type_change_values(self, values):
        prepared = dict(values)
        # La modal puede aportar evidencia nueva tras confirmar el cambio de tipo.
        prepared.setdefault("x_device_inspection_marks", False)
        prepared.setdefault("x_device_condition_ids", [fields.Command.clear()])
        return prepared

    @api.constrains(
        "x_device_type", "x_device_description",
        "x_device_condition_ids", "x_device_inspection_marks",
    )
    def _check_inspection_device_type(self):
        for repair in self:
            if repair.x_device_type:
                continue
            if (
                repair.x_device_description
                or repair.x_device_condition_ids
                or repair.x_device_inspection_marks
            ):
                raise ValidationError(_(
                    "Selecciona el tipo de dispositivo antes de describir o inspeccionar el equipo."
                ))

    @api.constrains("x_device_type", "x_device_condition_ids")
    def _check_inspection_conditions(self):
        for repair in self:
            incompatible = repair.x_device_condition_ids.filtered(
                lambda condition: condition.device_type
                and condition.device_type != repair.x_device_type
            )
            if incompatible:
                raise ValidationError(_(
                    "Retira los desperfectos que no corresponden al tipo de dispositivo seleccionado."
                ))

    @api.constrains("x_device_type", "x_device_inspection_marks")
    def _check_inspection_marks(self):
        for repair in self:
            marks = repair.x_device_inspection_marks
            if marks is False or marks is None:
                continue
            if not isinstance(marks, dict):
                raise ValidationError(_("El formato de las marcas de inspección no es válido."))
            expected_keys = {"device_type", "front", "back"}
            if marks.get("device_type") == "console":
                expected_keys.add("console_format")
            if set(marks) != expected_keys:
                raise ValidationError(_("El formato de las marcas de inspección no es válido."))
            if marks["device_type"] not in DEVICE_INSPECTION_TYPES:
                raise ValidationError(_("Este tipo de dispositivo no dispone de esquema de inspección."))
            if marks["device_type"] != repair.x_device_type:
                raise ValidationError(_("Borra las marcas antes de cambiar el tipo de dispositivo."))
            if marks["device_type"] == "console":
                repair._check_console_inspection_format(marks["console_format"])
            for view in ("front", "back"):
                repair._validate_inspection_view(marks[view])

    @api.model
    def _check_console_inspection_format(self, console_format):
        if not isinstance(console_format, str) or console_format not in self._get_console_inspection_formats():
            raise ValidationError(_("Selecciona un formato de consola válido para la inspección."))

    @api.model
    def _validate_inspection_view(self, strokes):
        if not isinstance(strokes, list) or len(strokes) > 500:
            raise ValidationError(_("Demasiados trazos de inspección o formato no válido."))
        point_count = 0
        for stroke in strokes:
            if not isinstance(stroke, list) or not stroke or len(stroke) > 4000:
                raise ValidationError(_("Un trazo de inspección no es válido o es demasiado largo."))
            point_count += len(stroke)
            if point_count > 20000:
                raise ValidationError(_("Las marcas de inspección contienen demasiados puntos."))
            for point in stroke:
                if not isinstance(point, list) or len(point) != 2:
                    raise ValidationError(_("Las coordenadas de inspección no son válidas."))
                if any(
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                    or not 0 <= value <= 1
                    for value in point
                ):
                    raise ValidationError(_("Las coordenadas de inspección deben estar dentro del esquema."))

    def _prepare_device_inspection_snapshot(self):
        self.ensure_one()
        description = self.x_device_description or ""
        conditions = self.x_device_condition_ids.sorted(
            lambda condition: (condition.sequence, condition.name, condition.id)
        ).mapped("name")
        views = self._get_device_inspection_document_views()
        if not description.strip() and not conditions and not views:
            return False
        return {"description": description, "conditions": conditions, "views": views}

    def _get_device_inspection_document_views(self):
        self.ensure_one()
        marks = self.x_device_inspection_marks
        if not marks or not (marks.get("front") or marks.get("back")):
            return []
        diagrams = self.get_device_inspection_diagrams()
        diagram = diagrams.get(self.x_device_type)
        if not diagram or marks.get("device_type") != self.x_device_type:
            return []
        prefix = self.x_device_type
        if prefix == "console":
            selected_format = next((
                item for item in diagram["formats"]
                if item["value"] == marks.get("console_format")
            ), None)
            if not selected_format:
                return []
            prefix = selected_format["image_prefix"]
        return [
            {"label": diagram[side], "src": self._get_device_inspection_document_image(
                prefix, side, marks.get(side, [])
            )}
            for side in ("front", "back")
        ]

    def _get_device_inspection_document_image(self, prefix, side, strokes):
        # El prefijo procede del catálogo Python; nunca de una ruta del usuario.
        path = "wexplay_repair/static/src/img/device_inspection/%s_%s.svg" % (prefix, side)
        with file_open(path, "rb") as source:
            svg = etree.parse(source).getroot()
        for stroke in strokes:
            points = ["%s,%s" % (x * 320, y * 400) for x, y in stroke]
            drawing = "M " + " L ".join(points)
            if len(points) == 1:
                drawing += " l 0.1,0"
            etree.SubElement(svg, "{http://www.w3.org/2000/svg}path", {
                "d": drawing, "fill": "none", "stroke": "#d83a3a",
                "stroke-width": "3", "stroke-linecap": "round", "stroke-linejoin": "round",
            })
        encoded = base64.b64encode(etree.tostring(svg)).decode("ascii")
        return "data:image/svg+xml;base64," + encoded

