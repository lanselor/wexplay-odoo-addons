# -*- coding: utf-8 -*-

import base64
import io
import logging
import mimetypes
import os
import shutil
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

    def _build_sat_video_display_name(self, media_index):
        self.ensure_one()
        return _("Vídeo %03d") % media_index

    def _build_sat_video_filename(self):
        self.ensure_one()
        return "video-%s.mp4" % uuid4().hex

    def _get_video_processing_settings(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "max_px": int(params.get_param("wexplay_repair_images.video_max_px", 1280)),
            "crf": int(params.get_param("wexplay_repair_images.video_crf", 28)),
            "max_duration_seconds": int(
                params.get_param("wexplay_repair_images.video_max_duration_seconds", 60)
            ),
            "max_size_mb": int(params.get_param("wexplay_repair_images.video_max_size_mb", 100)),
        }

    def _check_video_metadata(self, metadata, file_size):
        self.ensure_one()
        video_stream = next(
            (stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "video"),
            False,
        )
        if not video_stream:
            raise UserError(_("El archivo no contiene una pista de vídeo válida."))
        duration = float(metadata.get("format", {}).get("duration") or 0)
        if duration <= 0:
            raise UserError(_("No se pudo determinar la duración del vídeo."))
        settings = self._get_video_processing_settings()
        if duration > max(settings["max_duration_seconds"], 1):
            raise UserError(_("El vídeo supera la duración máxima configurada."))
        if file_size > max(settings["max_size_mb"], 1) * 1024 * 1024:
            raise UserError(_("El vídeo supera el tamaño máximo configurado."))

    def create_video_processing_job(self, filename, content):
        self.ensure_one()
        self.check_access_rights("read")
        self.check_access_rule("read")
        if not self.env.user.has_group("wexplay_image_core.group_wex_image_user"):
            raise UserError(_("No tienes permisos para subir contenido multimedia."))
        mimetype, _encoding = mimetypes.guess_type(filename or "")
        if mimetype not in ("video/mp4", "video/quicktime", "video/webm", "video/x-matroska"):
            raise UserError(_("Solo se admiten vídeos MP4, MOV, WebM y MKV."))
        attachment = self.env["ir.attachment"].create({
            "name": filename or "video",
            "raw": content,
            "res_model": "wex.repair.media.process.job",
            "res_id": 0,
            "mimetype": mimetype,
        })
        job = self.env["wex.repair.media.process.job"].create({
            "repair_order_id": self.id,
            "source_attachment_id": attachment.id,
            "source_filename": filename or "video",
            "progress_message": _("Vídeo en cola"),
        })
        job.enqueue_processing()
        return job

    def _create_video_media_from_paths(self, output_path, thumbnail_path, source_filename):
        self.ensure_one()
        with open(output_path, "rb") as video_file, open(thumbnail_path, "rb") as thumbnail_file:
            video_content = base64.b64encode(video_file.read())
            thumbnail_content = base64.b64encode(thumbnail_file.read())
        directory = self._get_sat_image_directory()
        media_index = self._get_next_image_index()
        media = self.env["wex.image.record"].with_context(skip_repair_image_chatter=True).create_media_from_binary(
            name=self._build_sat_video_display_name(media_index),
            binary_content=video_content,
            directory=directory,
            res_model="repair.order",
            res_id=self.id,
            sequence=self._get_next_image_sequence(),
            company_id=self.company_id.id,
            extra_vals={
                "repair_order_id": self.id,
                "dms_file_name": self._build_sat_video_filename(),
                "media_thumbnail": thumbnail_content,
            },
        )
        media._post_images_batch_added_to_repair_chatter()
        return media

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
        image_records = self.x_image_ids.filtered(
            lambda record: record.x_include_in_sat_report and record.media_kind == "image"
        ).sorted(
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
                    "preview_url": image.preview_url or "",
                    "content_url": image.content_url or "",
                    "media_kind": image.media_kind or "image",
                    "file_size_human": image.file_size_human or "",
                    "uploaded_by_name": image.uploaded_by_id.display_name or "",
                    "uploaded_at": fields.Datetime.to_string(image.uploaded_at) if image.uploaded_at else "",
                    "tags": image._get_repair_image_tag_names(),
                }
                for image in images
            ],
            "jobs": self._get_repair_media_job_values(),
        }

    def _get_repair_media_job_values(self):
        self.ensure_one()
        jobs = self.env["wex.repair.media.process.job"].search(
            [("repair_order_id", "=", self.id), ("state", "in", ("queued", "processing", "error"))],
            order="id desc",
        )
        return [
            {
                "id": job.id,
                "name": job.source_filename,
                "state": job.state,
                "progress_percent": job.progress_percent,
                "progress_message": job.progress_message or "",
                "error_message": job.error_message or "",
            }
            for job in jobs
        ]

    def get_repair_media_job_values(self):
        self.ensure_one()
        return self._get_repair_media_job_values()

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
        if image.media_kind != "image":
            raise UserError(_("Solo las imágenes pueden incluirse en el informe SAT."))
        image.x_include_in_sat_report = not image.x_include_in_sat_report
        return image.x_include_in_sat_report

    def action_requeue_repair_video_job(self, job_id):
        self.ensure_one()
        job = self.env["wex.repair.media.process.job"].search([
            ("id", "=", job_id), ("repair_order_id", "=", self.id),
        ], limit=1)
        if not job:
            raise UserError(_("El trabajo de vídeo no pertenece a este SAT."))
        job.sudo().action_requeue()
        return True

    def action_cancel_repair_video_job(self, job_id):
        self.ensure_one()
        job = self.env["wex.repair.media.process.job"].search([
            ("id", "=", job_id), ("repair_order_id", "=", self.id),
        ], limit=1)
        if not job:
            raise UserError(_("El trabajo de vídeo no pertenece a este SAT."))
        job.sudo().action_cancel()
        return True

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
