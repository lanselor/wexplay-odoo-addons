# -*- coding: utf-8 -*-

import base64
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class JobCancelled(Exception):
    pass


class WexRepairMediaProcessJob(models.Model):
    _name = "wex.repair.media.process.job"
    _description = "SAT Video Processing Job"
    _order = "id asc"

    STATE_QUEUED = "queued"
    STATE_PROCESSING = "processing"
    STATE_DONE = "done"
    STATE_ERROR = "error"
    STATE_CANCELLED = "cancelled"

    FFMPEG_TIMEOUT_SECONDS = 600

    repair_order_id = fields.Many2one("repair.order", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="repair_order_id.company_id", store=True, readonly=True)
    source_attachment_id = fields.Many2one("ir.attachment", ondelete="set null")
    source_filename = fields.Char(required=True, readonly=True)
    created_by_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    media_id = fields.Many2one("wex.image.record", readonly=True, ondelete="set null")
    queue_job_uuid = fields.Char(readonly=True, index=True)
    state = fields.Selection(
        [
            (STATE_QUEUED, "En cola"),
            (STATE_PROCESSING, "Procesando"),
            (STATE_DONE, "Completado"),
            (STATE_ERROR, "Error"),
            (STATE_CANCELLED, "Cancelado"),
        ],
        default=STATE_QUEUED,
        required=True,
        index=True,
    )
    progress_percent = fields.Integer(default=0, readonly=True)
    progress_message = fields.Char(readonly=True)
    error_message = fields.Text(readonly=True)
    queued_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    started_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(readonly=True)

    def enqueue_processing(self):
        self.ensure_one()
        if self.state != self.STATE_QUEUED:
            return
        queue_job = self.with_delay(
            channel="root.sat_video",
            description=_("Procesar vídeo SAT: %s") % self.source_filename,
            identity_key="wexplay_sat_video_%s" % self.id,
        ).process_queued_video()
        self.write({"queue_job_uuid": queue_job.uuid})

    def process_queued_video(self):
        self.ensure_one()
        self._check_not_cancelled()
        self._mark_processing()
        self._process_job()

    def _process_job(self):
        self.ensure_one()
        source_path = output_path = thumbnail_path = False
        try:
            self._check_not_cancelled()
            if not self.source_attachment_id:
                raise JobCancelled()
            self._set_progress(25, _("Validando vídeo"))
            source_path, output_path, thumbnail_path = self._create_temp_paths()
            try:
                self._write_source(source_path)
                metadata = self._probe_video(source_path)
                self.repair_order_id._check_video_metadata(metadata, self.source_attachment_id.file_size)
                self._set_progress(45, _("Comprimiendo vídeo"))
                self._transcode_video(source_path, output_path)
                self._set_progress(80, _("Generando miniatura"))
                self._create_thumbnail(output_path, thumbnail_path)
                self._check_not_cancelled()
                media = self.repair_order_id.with_user(self.created_by_id)._create_video_media_from_paths(
                    output_path, thumbnail_path, self.source_filename
                )
            finally:
                for path in (source_path, output_path, thumbnail_path):
                    if path and os.path.exists(path):
                        os.unlink(path)
                if source_path:
                    shutil.rmtree(os.path.dirname(source_path), ignore_errors=True)
            self._remove_source_attachment()
            self._mark_done(media)
        except JobCancelled:
            self._remove_source_attachment()
            self._mark_cancelled()
        except Exception as exc:
            _logger.exception("SAT video processing failed for job %s", self.id)
            self._mark_error(exc)

    def _mark_processing(self):
        self._commit_status_update({
            "state": self.STATE_PROCESSING,
            "started_at": fields.Datetime.now(),
            "progress_percent": 10,
            "progress_message": _("Preparando vídeo"),
            "error_message": False,
        })

    def _mark_done(self, media):
        self._commit_status_update({
            "state": self.STATE_DONE,
            "media_id": media.id,
            "finished_at": fields.Datetime.now(),
            "progress_percent": 100,
            "progress_message": _("Vídeo listo"),
        })

    def _mark_cancelled(self):
        self._commit_status_update({
            "state": self.STATE_CANCELLED,
            "finished_at": fields.Datetime.now(),
            "progress_message": _("Vídeo cancelado"),
        })

    def _mark_error(self, error):
        self._commit_status_update({
            "state": self.STATE_ERROR,
            "finished_at": fields.Datetime.now(),
            "error_message": str(error),
            "progress_message": _("No se pudo procesar el vídeo"),
        })

    def _commit_status_update(self, values):
        self.write(values)
        self.env.cr.commit()

    def _set_progress(self, percent, message):
        self._commit_status_update({
            "progress_percent": percent,
            "progress_message": message,
        })

    def action_requeue(self):
        for job in self:
            if job.state != self.STATE_ERROR:
                continue
            job.write({
                "state": self.STATE_QUEUED,
                "queued_at": fields.Datetime.now(),
                "started_at": False,
                "finished_at": False,
                "progress_percent": 0,
                "progress_message": _("Vídeo en cola"),
                "error_message": False,
                "queue_job_uuid": False,
            })
            job.enqueue_processing()
        return True

    def action_cancel(self):
        for job in self:
            if job.state not in (
                self.STATE_QUEUED,
                self.STATE_PROCESSING,
                self.STATE_ERROR,
            ):
                continue
            is_processing = job.state == self.STATE_PROCESSING
            job.write({
                "state": self.STATE_CANCELLED,
                "finished_at": fields.Datetime.now(),
                "progress_message": _("Cancelando vídeo") if is_processing else _("Vídeo cancelado"),
            })
            if not is_processing or not job.queue_job_uuid:
                job._remove_source_attachment()
            job._cancel_queued_job()
        return True

    def _cancel_queued_job(self):
        self.ensure_one()
        if not self.queue_job_uuid:
            return
        queue_job = self.env["queue.job"].sudo().search(
            [("uuid", "=", self.queue_job_uuid)], limit=1
        )
        if queue_job:
            queue_job.button_cancelled()

    def _remove_source_attachment(self):
        self.ensure_one()
        attachment = self.source_attachment_id
        if not attachment:
            return
        # La FK exige liberar el trabajo antes de eliminar su archivo temporal.
        self.write({"source_attachment_id": False})
        attachment.unlink()

    def _is_cancelled(self):
        self.env.cr.execute(
            "SELECT state FROM wex_repair_media_process_job WHERE id = %s", [self.id]
        )
        row = self.env.cr.fetchone()
        return not row or row[0] == self.STATE_CANCELLED

    def _check_not_cancelled(self):
        if self._is_cancelled():
            raise JobCancelled()

    def _create_temp_paths(self):
        workdir = tempfile.mkdtemp(prefix="wexplay_sat_video_")
        return (os.path.join(workdir, "source"), os.path.join(workdir, "video.mp4"), os.path.join(workdir, "thumbnail.jpg"))

    def _write_source(self, source_path):
        with open(source_path, "wb") as source_file:
            source_file.write(base64.b64decode(self.source_attachment_id.datas))

    def _run_ffmpeg(self, args):
        executable = self.env["ir.config_parameter"].sudo().get_param("wexplay_repair_images.ffmpeg_path", "ffmpeg")
        with tempfile.TemporaryFile() as error_file:
            process = subprocess.Popen(
                [executable, "-hide_banner", "-loglevel", "error", "-nostats", "-y", *args],
                stdout=subprocess.DEVNULL,
                stderr=error_file,
            )
            deadline = time.monotonic() + self.FFMPEG_TIMEOUT_SECONDS
            while process.poll() is None:
                if self._is_cancelled():
                    self._terminate_ffmpeg(process)
                    raise JobCancelled()
                if time.monotonic() > deadline:
                    self._terminate_ffmpeg(process)
                    raise UserError(_("FFmpeg superó el tiempo máximo de procesamiento."))
                time.sleep(0.5)
            if process.returncode:
                error_file.seek(0)
                stderr = error_file.read().decode("utf-8", errors="replace")
                raise subprocess.CalledProcessError(process.returncode, process.args, stderr=stderr)

    @staticmethod
    def _terminate_ffmpeg(process):
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def _probe_video(self, source_path):
        executable = self.env["ir.config_parameter"].sudo().get_param("wexplay_repair_images.ffprobe_path", "ffprobe")
        result = subprocess.run([executable, "-v", "error", "-show_entries", "format=duration", "-show_streams", "-of", "json", source_path], check=True, capture_output=True, text=True, timeout=30)
        return json.loads(result.stdout)

    def _transcode_video(self, source_path, output_path):
        self._check_not_cancelled()
        settings = self.repair_order_id._get_video_processing_settings()
        max_px = max(settings["max_px"], 320)
        crf = min(max(settings["crf"], 18), 35)
        self._run_ffmpeg(["-i", source_path, "-vf", "scale=%s:%s:force_original_aspect_ratio=decrease:force_divisible_by=2" % (max_px, max_px), "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", output_path])

    def _create_thumbnail(self, output_path, thumbnail_path):
        self._check_not_cancelled()
        self._run_ffmpeg(["-ss", "00:00:01", "-i", output_path, "-frames:v", "1", thumbnail_path])
