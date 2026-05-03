# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import UserError


class WexRepairImageUploadWizard(models.TransientModel):
    _name = "wex.repair.image.upload.wizard"
    _description = "Asistente de subida de imágenes SAT"

    repair_order_id = fields.Many2one(
        comodel_name="repair.order",
        required=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        comodel_name="wex.repair.image.upload.wizard.line",
        inverse_name="wizard_id",
        string="Imágenes",
    )

    def action_upload_images(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Añade al menos una imagen antes de subirla."))

        directory = self.repair_order_id._get_sat_image_directory()
        image_model = self.env["wex.image.record"]
        next_sequence = self.repair_order_id._get_next_image_sequence()
        next_index = self.repair_order_id._get_next_image_index()
        created_images = image_model

        for offset, line in enumerate(self.line_ids.sorted(lambda item: (item.sequence, item.id))):
            image_index = next_index + offset
            sequence = next_sequence + (offset * 10)
            display_name = self.repair_order_id._build_sat_image_display_name(image_index)
            filename = self.repair_order_id._build_sat_image_filename(
                original_filename=line.filename,
            )
            created_images |= image_model.with_context(
                skip_repair_image_chatter=True
            ).create_image_from_binary(
                name=display_name,
                binary_content=line.image_file,
                directory=directory,
                res_model="repair.order",
                res_id=self.repair_order_id.id,
                description=line.description,
                tag_ids=line.tag_ids.ids,
                sequence=sequence,
                company_id=self.repair_order_id.company_id.id,
                extra_vals={
                    "repair_order_id": self.repair_order_id.id,
                    "dms_file_name": filename,
                },
            )
        created_images._post_images_batch_added_to_repair_chatter()
        return {"type": "ir.actions.act_window_close"}


class WexRepairImageUploadWizardLine(models.TransientModel):
    _name = "wex.repair.image.upload.wizard.line"
    _description = "Línea de subida de imágenes SAT"
    _order = "sequence asc, id asc"

    wizard_id = fields.Many2one(
        comodel_name="wex.repair.image.upload.wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    filename = fields.Char()
    description = fields.Text(string="Descripción")
    tag_ids = fields.Many2many(
        comodel_name="wex.image.tag",
        relation="wex_repair_image_upload_wizard_line_tag_rel",
        column1="line_id",
        column2="tag_id",
        string="Etiquetas",
    )
    image_file = fields.Binary(string="Imagen", required=True, attachment=False)
