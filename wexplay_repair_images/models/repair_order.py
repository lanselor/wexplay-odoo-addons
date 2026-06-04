# -*- coding: utf-8 -*-

import base64
import io
import logging
import mimetypes
import os
from uuid import uuid4

from PIL import Image, ImageOps

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_image_ids = fields.One2many(
        comodel_name="wex.image.record",
        inverse_name="repair_order_id",
        string="Imágenes",
    )
    x_image_count = fields.Integer(compute="_compute_x_image_count", store=False)

    def _compute_x_image_count(self):
        count_by_repair = {}
        groups = self.env["wex.image.record"].read_group(
            [("repair_order_id", "in", self.ids)],
            ["repair_order_id"],
            ["repair_order_id"],
        )
        for group in groups:
            repair_group = group.get("repair_order_id")
            if not repair_group:
                continue
            count_by_repair[repair_group[0]] = (
                group.get("__count")
                or group.get("repair_order_id_count")
                or 0
            )
        for rec in self:
            rec.x_image_count = count_by_repair.get(rec.id, 0)

    def _get_sat_image_directory(self):
        self.ensure_one()
        return self._get_or_create_sat_directory("IMAGES", create_defaults=True)

    def _get_next_image_sequence(self):
        self.ensure_one()
        max_sequence = max(self.x_image_ids.mapped("sequence") or [0])
        return max_sequence + 10

    def _get_next_image_index(self):
        self.ensure_one()
        return len(self.x_image_ids) + 1

    def _build_sat_image_display_name(self, image_index):
        self.ensure_one()
        return _("Imagen %03d") % image_index

    def _build_sat_image_filename(self, original_filename=False):
        self.ensure_one()
        _root, extension = os.path.splitext(original_filename or "")
        extension = extension.lower() or ".jpg"
        unique_token = uuid4().hex
        return "imagen-%s%s" % (unique_token, extension)

    def _compress_sat_image(self, binary_content, filename):
        """Redimensiona y recomprime la imagen si la compresión SAT está activa.

        Devuelve el binary procesado (base64). Si está desactivada, el formato
        no es comprimible (GIF) o falla cualquier paso, devuelve el original.
        """
        self.ensure_one()
        company = self.company_id
        if not company.x_sat_image_compress_enabled:
            return binary_content

        mimetype, _ = mimetypes.guess_type(filename or "")
        if not mimetype or not mimetype.startswith("image/"):
            return binary_content
        if mimetype == "image/gif":
            return binary_content

        max_px = max(company.x_sat_image_max_px or 1920, 320)
        quality = min(max(company.x_sat_image_quality or 85, 1), 95)

        try:
            raw = base64.b64decode(binary_content)
            img = Image.open(io.BytesIO(raw))

            needs_resize = max(img.size) > max_px

            # PNG lossless sin resize: no hay nada que ganar re-encodando
            if not needs_resize and mimetype not in ("image/jpeg", "image/webp"):
                return binary_content

            img = ImageOps.exif_transpose(img)

            if needs_resize:
                img.thumbnail((max_px, max_px), Image.LANCZOS)

            out = io.BytesIO()
            if mimetype == "image/jpeg":
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                img.save(out, format="JPEG", quality=quality, optimize=True)
            elif mimetype == "image/webp":
                img.save(out, format="WEBP", quality=quality)
            else:
                img.save(out, format=img.format or "PNG", optimize=True)

            processed = out.getvalue()
            if len(processed) >= len(raw):
                return binary_content

            return base64.b64encode(processed)

        except Exception:
            _logger.warning(
                "SAT image compress failed for '%s', using original", filename, exc_info=True
            )
            return binary_content

    def _collect_sat_report_images(self):
        self.ensure_one()
        images = []
        image_records = self.x_image_ids.filtered("x_include_in_sat_report").sorted(
            lambda r: (r.sequence, r.id)
        )
        image_records.mapped("dms_file_id").read(["mimetype"])
        image_records.mapped("tag_ids")
        for rec in image_records:
            img_data = rec.dms_file_id.image_1920
            if not img_data:
                continue
            mimetype = rec.dms_file_id.mimetype or "image/jpeg"
            data_b64 = img_data.decode("utf-8") if isinstance(img_data, bytes) else img_data
            images.append({
                "name": rec.name or "",
                "src": "data:%s;base64,%s" % (mimetype, data_b64),
                "description": rec.description or "",
                "tags": ", ".join(rec._get_repair_image_tag_names()),
            })
        return images

    def _get_repair_image_for_chatter_action(self, image_id):
        self.ensure_one()
        image = self.x_image_ids.filtered(lambda record: record.id == image_id)[:1]
        if not image:
            raise UserError(_("La imagen seleccionada no pertenece a este SAT."))
        return image

    def get_repair_images_chatter_values(self):
        self.ensure_one()
        images = self.x_image_ids.sorted(lambda record: (record.sequence, record.id))
        return {
            "count": len(images),
            "can_manage_images": self.env.user.has_group(
                "wexplay_image_core.group_wex_image_user"
            ),
            "images": [
                {
                    "id": image.id,
                    "name": image.name or _("Imagen SAT"),
                    "description": image.description or "",
                    "sequence": image.sequence,
                    "include_in_report": image.x_include_in_sat_report,
                    "thumbnail_url": image.thumbnail_url or image.preview_url or "",
                    "uploaded_by_name": image.uploaded_by_id.display_name or "",
                    "uploaded_at": fields.Datetime.to_string(image.uploaded_at) if image.uploaded_at else "",
                    "tags": image._get_repair_image_tag_names(),
                }
                for image in images
            ],
        }

    def upload_repair_image_from_dropzone(self, filename, binary_content):
        self.ensure_one()
        if not binary_content:
            raise UserError(_("La imagen está vacía."))
        mimetype, _ = mimetypes.guess_type(filename or "")
        if not mimetype or not mimetype.startswith("image/"):
            raise UserError(_("Solo se admiten archivos de imagen (JPG, PNG, WebP, GIF)."))
        binary_content = self._compress_sat_image(binary_content, filename)
        directory = self._get_sat_image_directory()
        image_index = self._get_next_image_index()
        sequence = self._get_next_image_sequence()
        display_name = self._build_sat_image_display_name(image_index)
        safe_filename = self._build_sat_image_filename(original_filename=filename)
        image = self.env["wex.image.record"].with_context(
            skip_repair_image_chatter=True
        ).create_image_from_binary(
            name=display_name,
            binary_content=binary_content,
            directory=directory,
            res_model="repair.order",
            res_id=self.id,
            description=False,
            tag_ids=[],
            sequence=sequence,
            company_id=self.company_id.id,
            extra_vals={
                "repair_order_id": self.id,
                "dms_file_name": safe_filename,
            },
        )
        image._post_images_batch_added_to_repair_chatter()
        return {"image_id": image.id, "image_name": image.name}

    def action_open_repair_image_preview(self, image_id):
        self.ensure_one()
        return self._get_repair_image_for_chatter_action(image_id).action_open_preview()

    def action_open_repair_image_dms_file(self, image_id):
        self.ensure_one()
        return self._get_repair_image_for_chatter_action(image_id).action_open_dms_file()

    def action_toggle_repair_image_sat_report(self, image_id):
        self.ensure_one()
        image = self._get_repair_image_for_chatter_action(image_id)
        image.x_include_in_sat_report = not image.x_include_in_sat_report
        return image.x_include_in_sat_report

    def action_open_image_upload_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Subir imágenes"),
            "res_model": "wex.repair.image.upload.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_repair_order_id": self.id,
            },
        }
