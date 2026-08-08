# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    x_sat_image_compress_enabled = fields.Boolean(
        related="company_id.x_sat_image_compress_enabled",
        string="Comprimir imágenes SAT",
        readonly=False,
    )
    x_sat_image_max_px = fields.Integer(
        related="company_id.x_sat_image_max_px",
        string="Resolución máxima (px)",
        readonly=False,
    )
    x_sat_image_quality = fields.Integer(
        related="company_id.x_sat_image_quality",
        string="Calidad JPEG/WebP",
        readonly=False,
    )
    x_sat_video_compress_enabled = fields.Boolean(
        config_parameter="wexplay_repair_images.video_compress_enabled", default=True
    )
    x_sat_video_max_px = fields.Integer(
        config_parameter="wexplay_repair_images.video_max_px", default=1280
    )
    x_sat_video_crf = fields.Integer(
        config_parameter="wexplay_repair_images.video_crf", default=28
    )
    x_sat_video_max_duration_seconds = fields.Integer(
        config_parameter="wexplay_repair_images.video_max_duration_seconds", default=60
    )
    x_sat_video_max_size_mb = fields.Integer(
        config_parameter="wexplay_repair_images.video_max_size_mb", default=100
    )
    x_sat_video_ffmpeg_path = fields.Char(
        string="Ruta de FFmpeg",
        config_parameter="wexplay_repair_images.ffmpeg_path",
        default="ffmpeg",
    )
    x_sat_video_ffprobe_path = fields.Char(
        string="Ruta de FFprobe",
        config_parameter="wexplay_repair_images.ffprobe_path",
        default="ffprobe",
    )
