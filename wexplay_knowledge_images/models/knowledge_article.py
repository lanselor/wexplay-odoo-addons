# -*- coding: utf-8 -*-

import os
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class KnowledgeArticle(models.Model):
    _inherit = "wex.knowledge.article"

    image_ids = fields.One2many(
        comodel_name="wex.knowledge.article.image",
        inverse_name="article_id",
        string="Embedded Images",
    )
    image_count = fields.Integer(compute="_compute_image_count")

    def _compute_image_count(self):
        for article in self:
            article.image_count = len(article.image_ids)

    def _user_can_read_record(self, user=None):
        self.ensure_one()
        user = user or self.env.user
        if self._user_is_manager(user):
            return True
        if not self.is_global and self.company_id not in user.company_ids:
            return False
        if self.visibility == "internal":
            return True
        if self.visibility == "private":
            return user == self.author_id or user == self.owner_id or user in self.collaborator_ids
        if self.visibility == "by_group":
            return bool(self.allowed_group_ids & user.groups_id)
        return False

    def _check_user_can_read_embedded_media(self, user=None):
        user = user or self.env.user
        for article in self:
            if not article._user_can_read_record(user):
                raise AccessError(_("You do not have permission to access this article media."))

    @api.model
    def _sanitize_knowledge_image_dms_name(self, name, fallback="ARTICLE"):
        sanitized = (name or "").strip()
        if not sanitized:
            sanitized = fallback
        sanitized = re.sub(r'[<>:"/\\|?*]+', "-", sanitized)
        sanitized = re.sub(r"[\x00-\x1f]", "", sanitized)
        sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
        if not sanitized:
            sanitized = fallback
        return sanitized[:120]

    def _get_knowledge_images_safe_name(self):
        self.ensure_one()
        fallback = "ARTICLE-%s" % self.id if self.id else "ARTICLE"
        return self._sanitize_knowledge_image_dms_name(self.name, fallback=fallback)

    def _get_knowledge_image_dms_storage(self):
        self.ensure_one()
        storage = self.company_id.x_wex_knowledge_images_dms_storage_id
        if not storage:
            raise UserError(_("Configura primero el almacenamiento DMS de Knowledge en Ajustes."))
        return storage

    def _get_or_create_knowledge_images_root_directory(self):
        self.ensure_one()
        company = self.company_id
        root_directory = company.x_wex_knowledge_images_dms_root_directory_id
        if root_directory and root_directory.exists():
            return root_directory

        storage = self._get_knowledge_image_dms_storage()
        root_directory = self.env["dms.directory"].search(
            [
                ("is_root_directory", "=", True),
                ("storage_id", "=", storage.id),
                ("name", "=", "KNOWLEDGE"),
            ],
            limit=1,
        )
        if not root_directory:
            root_directory = self.env["dms.directory"].create(
                {
                    "name": "KNOWLEDGE",
                    "is_root_directory": True,
                    "storage_id": storage.id,
                }
            )
        company.x_wex_knowledge_images_dms_root_directory_id = root_directory
        return root_directory

    def _get_or_create_knowledge_child_directory(self, parent_directory, name):
        self.ensure_one()
        directory = self.env["dms.directory"].search(
            [
                ("parent_id", "=", parent_directory.id),
                ("name", "=", name),
            ],
            limit=1,
        )
        if not directory:
            directory = self.env["dms.directory"].create(
                {
                    "name": name,
                    "parent_id": parent_directory.id,
                }
            )
        return directory

    def _get_or_create_knowledge_article_directory(self):
        self.ensure_one()
        root_directory = self._get_or_create_knowledge_images_root_directory()
        return self._get_or_create_knowledge_child_directory(
            root_directory,
            self._get_knowledge_images_safe_name(),
        )

    def _get_or_create_knowledge_images_directory(self):
        self.ensure_one()
        article_directory = self._get_or_create_knowledge_article_directory()
        return self._get_or_create_knowledge_child_directory(article_directory, "IMAGES")

    def _get_next_embedded_image_index(self):
        self.ensure_one()
        existing_names = self.image_ids.mapped("name")
        max_index = 0
        for name in existing_names:
            match = re.search(r"(\d+)$", name or "")
            if match:
                max_index = max(max_index, int(match.group(1)))
        return max_index + 1

    def _build_embedded_image_name(self, image_index):
        self.ensure_one()
        return _("%s - Image %s") % (self.name or _("Article"), image_index)

    def _build_embedded_image_filename(self, original_filename, image_index):
        self.ensure_one()
        _base_name, extension = os.path.splitext(original_filename or "")
        safe_article_name = self._get_knowledge_images_safe_name().lower().replace(" ", "-")
        extension = extension.lower() or ".png"
        return "%s-image-%s%s" % (safe_article_name, image_index, extension)

    def action_open_image_upload_wizard(self):
        self.ensure_one()
        if not self._user_can_edit_record(self.env.user):
            raise AccessError(_("You do not have permission to edit the selected article."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Insert Image"),
            "res_model": "wex.knowledge.article.image.upload.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_article_id": self.id,
            },
        }

    def upload_embedded_image_from_editor(self, filename, binary_content, name=False, description=False):
        self.ensure_one()
        if not self._user_can_edit_record(self.env.user):
            raise AccessError(_("You do not have permission to edit the selected article."))
        image_index = self._get_next_embedded_image_index()
        image_name = name or self._build_embedded_image_name(image_index)
        next_sequence = (max(self.image_ids.mapped("sequence")) + 10) if self.image_ids else 10
        image = self.env["wex.knowledge.article.image"].create_embedded_image_from_binary(
            article=self,
            name=image_name,
            binary_content=binary_content,
            filename=self._build_embedded_image_filename(filename, image_index),
            description=description,
            sequence=next_sequence,
        )
        return {
            "image_id": image.id,
            "image_url": image.image_url,
            "name": image.name,
            "dms_file_name": image.dms_file_name,
            "uploaded_by_name": image.uploaded_by_id.display_name or self.env.user.display_name,
            "uploaded_at": fields.Datetime.to_string(image.uploaded_at) if image.uploaded_at else "",
            "html": image._build_embedded_html(),
        }

    def get_embedded_image_panel_data(self):
        self.ensure_one()
        self._check_user_can_read_embedded_media(self.env.user)
        return {
            "article_id": self.id,
            "items": [image._get_panel_payload() for image in self.image_ids.sorted(lambda rec: (rec.sequence, rec.id))],
        }

    def delete_embedded_image_from_panel(self, image_id):
        self.ensure_one()
        image = self.env["wex.knowledge.article.image"].browse(image_id)
        if not image.exists() or image.article_id != self:
            raise UserError(_("The embedded image does not belong to this article."))
        image.action_delete_image()
        return self.get_embedded_image_panel_data()
