# -*- coding: utf-8 -*-

import base64

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class WexKnowledgeImageController(http.Controller):
    def _can_read_article_image(self, article):
        user = request.env.user
        if not user._is_public() and article._user_can_read_record(user):
            return True
        if hasattr(article, "_can_user_read_portal_article") and article._can_user_read_portal_article(user):
            return True
        if hasattr(article, "_can_read_public_article") and article.public_link_enabled:
            return article._can_read_public_article(article.public_access_token)
        return False

    @http.route(
        ["/wex_knowledge/image/<int:image_id>/<string:access_token>"],
        type="http",
        auth="public",
    )
    def knowledge_article_image(self, image_id, access_token, **kwargs):
        image = request.env["wex.knowledge.article.image"].sudo().search(
            [
                ("id", "=", image_id),
                ("access_token", "=", access_token),
            ],
            limit=1,
        )
        if not image:
            raise NotFound()

        article = image.article_id.sudo()
        if not self._can_read_article_image(article):
            raise NotFound()

        dms_file = image.dms_file_id
        binary = dms_file.image_1920 or dms_file.content
        if not binary:
            raise NotFound()

        filename = image.dms_file_name or image.name or "knowledge-image"
        headers = [
            ("Content-Type", dms_file.mimetype or "application/octet-stream"),
            ("Cache-Control", "private, max-age=300, must-revalidate"),
            ("X-Content-Type-Options", "nosniff"),
            ("Content-Disposition", 'inline; filename="%s"' % filename),
        ]
        return request.make_response(base64.b64decode(binary), headers)
