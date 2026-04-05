# -*- coding: utf-8 -*-

import os

from odoo import _, fields, models


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_image_ids = fields.One2many(
        comodel_name="wex.image.record",
        inverse_name="repair_order_id",
        string="Imágenes",
    )
    x_image_count = fields.Integer(compute="_compute_x_image_count", store=False)

    def _compute_x_image_count(self):
        for rec in self:
            rec.x_image_count = len(rec.x_image_ids)

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

    def _build_sat_image_filename(self, image_index, original_filename=False):
        self.ensure_one()
        _root, extension = os.path.splitext(original_filename or "")
        extension = extension.lower() or ".jpg"
        return "imagen-%03d%s" % (image_index, extension)

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
