# -*- coding: utf-8 -*-

import mimetypes
import os
import re
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class KnowledgeArticleImage(models.Model):
    _name = "wex.knowledge.article.image"
    _description = "Knowledge Article Image"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence asc, id asc"

    name = fields.Char(required=True, tracking=True)
    description = fields.Text()
    sequence = fields.Integer(default=10)
    article_id = fields.Many2one(
        comodel_name="wex.knowledge.article",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    uploaded_by_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        readonly=True,
    )
    uploaded_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    access_token = fields.Char(required=True, readonly=True, copy=False, default=lambda self: uuid.uuid4().hex)
    is_embedded = fields.Boolean(default=True)

    dms_file_name = fields.Char(readonly=True)
    dms_file_id = fields.Many2one(
        comodel_name="dms.file",
        required=True,
        ondelete="restrict",
        index=True,
    )
    dms_directory_id = fields.Many2one(
        related="dms_file_id.directory_id",
        comodel_name="dms.directory",
        store=False,
        readonly=True,
    )
    mimetype = fields.Char(related="dms_file_id.mimetype", store=False, readonly=True)
    file_size = fields.Float(related="dms_file_id.size", store=False, readonly=True)
    checksum = fields.Char(related="dms_file_id.checksum", store=False, readonly=True)
    preview_image = fields.Image(related="dms_file_id.image_1920", readonly=True)
    image_url = fields.Char(compute="_compute_image_url")

    _sql_constraints = [
        ("wex_knowledge_article_image_sequence_positive", "CHECK(sequence >= 0)", "Sequence must be positive."),
        ("wex_knowledge_article_image_access_token_unique", "unique(access_token)", "The image token must be unique."),
    ]

    @api.depends("access_token")
    def _compute_image_url(self):
        for image in self:
            if not image.id or not image.access_token:
                image.image_url = False
                continue
            image.image_url = "/wex_knowledge/image/%s/%s" % (image.id, image.access_token)

    @api.constrains("article_id", "company_id")
    def _check_company_consistency(self):
        for image in self:
            if image.article_id.company_id and image.company_id != image.article_id.company_id:
                raise ValidationError(_("The image company must match the article company."))

    @api.constrains("dms_file_id")
    def _check_dms_file(self):
        for image in self:
            if image.dms_file_id and image.dms_file_id.mimetype and not image.dms_file_id.mimetype.startswith("image/"):
                raise ValidationError(_("Only image files can be linked to embedded article images."))

    @api.model
    def _find_existing_dms_file(self, directory, filename):
        return self.env["dms.file"].search(
            [
                ("directory_id", "=", directory.id),
                ("name", "=", filename),
            ],
            limit=1,
        )

    @api.model
    def _split_filename_parts(self, filename):
        base_name, extension = os.path.splitext(filename or "")
        return base_name or "image", extension

    @api.model
    def _get_unique_dms_filename(self, directory, filename):
        base_name, extension = self._split_filename_parts(filename)
        candidate = filename
        index = 1
        while self._find_existing_dms_file(directory, candidate):
            index += 1
            candidate = "%s-%s%s" % (base_name, index, extension)
        return candidate

    @api.model
    def _guess_mimetype(self, filename):
        mimetype, _encoding = mimetypes.guess_type(filename or "")
        return mimetype or "application/octet-stream"

    @api.model
    def _check_supported_image_mimetype(self, filename, mimetype=False):
        checked_mimetype = mimetype or self._guess_mimetype(filename)
        if not checked_mimetype.startswith("image/"):
            raise UserError(_("Only image uploads are supported in this flow."))
        return checked_mimetype

    @api.model
    def create_embedded_image_from_binary(
        self,
        *,
        article,
        name,
        binary_content,
        filename,
        description=False,
        sequence=10,
        mimetype=False,
    ):
        if not binary_content:
            raise UserError(_("The uploaded image is empty."))

        article.ensure_one()
        self._check_supported_image_mimetype(filename, mimetype=mimetype)
        directory = article._get_or_create_knowledge_images_directory()
        safe_filename = article._sanitize_knowledge_image_dms_name(
            filename,
            fallback="knowledge-image",
        )
        unique_filename = self._get_unique_dms_filename(directory, safe_filename)
        dms_file = self.env["dms.file"].create(
            {
                "directory_id": directory.id,
                "name": unique_filename,
                "content": binary_content,
            }
        )
        return self.create(
            {
                "name": name,
                "description": description,
                "sequence": sequence,
                "article_id": article.id,
                "company_id": article.company_id.id or self.env.company.id,
                "uploaded_by_id": self.env.user.id,
                "uploaded_at": fields.Datetime.now(),
                "dms_file_id": dms_file.id,
                "dms_file_name": unique_filename,
            }
        )

    def _build_embedded_html(self):
        self.ensure_one()
        alt_text = self.name or _("Embedded image")
        return '<p><img src="%s" alt="%s" class="img-fluid"/></p>' % (self.image_url, alt_text)

    def _get_panel_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "image_url": self.image_url,
            "uploaded_by_name": self.uploaded_by_id.display_name or "",
            "uploaded_at": fields.Datetime.to_string(self.uploaded_at) if self.uploaded_at else "",
            "dms_file_name": self.dms_file_name or "",
            "dms_file_id": self.dms_file_id.id,
        }

    def _remove_html_references_from_article(self):
        for image in self:
            body_html = image.article_id.body_html or ""
            if not body_html or not image.image_url:
                continue
            pattern = r"<img\b[^>]*\bsrc=(['\"])%s\1[^>]*>" % re.escape(image.image_url)
            cleaned_html = re.sub(pattern, "", body_html, flags=re.IGNORECASE)
            if cleaned_html != body_html:
                image.article_id.write({"body_html": cleaned_html})

    def _delete_linked_dms_files(self):
        dms_files = self.mapped("dms_file_id")
        for dms_file in dms_files:
            remaining_links = self.search_count([("dms_file_id", "=", dms_file.id)])
            if remaining_links <= 1:
                dms_file.unlink()

    def action_delete_image(self):
        self.ensure_one()
        if not self.article_id._user_can_edit_record(self.env.user):
            raise UserError(_("You do not have permission to delete this embedded image."))
        self._remove_html_references_from_article()
        self.unlink()
        return True

    def action_open_dms_file(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("DMS File"),
            "res_model": "dms.file",
            "res_id": self.dms_file_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def unlink(self):
        dms_files = self.mapped("dms_file_id")
        result = super().unlink()
        for dms_file in dms_files:
            if not self.search_count([("dms_file_id", "=", dms_file.id)]):
                dms_file.sudo().unlink()
        return result
