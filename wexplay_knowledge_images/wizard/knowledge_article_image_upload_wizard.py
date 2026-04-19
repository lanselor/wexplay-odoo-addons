# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class KnowledgeArticleImageUploadWizard(models.TransientModel):
    _name = "wex.knowledge.article.image.upload.wizard"
    _description = "Knowledge Article Image Upload Wizard"

    article_id = fields.Many2one(
        comodel_name="wex.knowledge.article",
        required=True,
        readonly=True,
    )
    name = fields.Char()
    filename = fields.Char()
    description = fields.Text()
    image_file = fields.Binary(required=True, attachment=False)

    def action_upload_image(self):
        self.ensure_one()
        article = self.article_id
        if not article._user_can_edit_record(self.env.user):
            raise AccessError(_("You do not have permission to edit the selected article."))
        if not self.image_file:
            raise UserError(_("Select an image before uploading."))

        next_sequence = (max(article.image_ids.mapped("sequence")) + 10) if article.image_ids else 10
        image = self.env["wex.knowledge.article.image"].create_embedded_image_from_binary(
            article=article,
            name=self.name or article._build_embedded_image_name(article._get_next_embedded_image_index()),
            binary_content=self.image_file,
            filename=article._build_embedded_image_filename(
                self.filename or "knowledge-image.png",
                article._get_next_embedded_image_index(),
            ),
            description=self.description,
            sequence=next_sequence,
        )

        existing_body = article.body_html or ""
        image_html = image._build_embedded_html()
        separator = "\n" if existing_body else ""
        article.write({"body_html": "%s%s%s" % (existing_body, separator, image_html)})
        return {"type": "ir.actions.act_window_close"}
