# -*- coding: utf-8 -*-

import base64
from urllib.parse import quote

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.wexplay_portal.controllers.portal import WexplayCustomerPortal


class WexplayRepairDeliveryPortal(WexplayCustomerPortal):
    @http.route(
        ["/my/repairs/<int:repair_id>/shipping/<int:operation_id>/label"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_repair_shipping_label(self, repair_id, operation_id, **kw):
        repair = self._get_portal_repair_or_404(repair_id)
        try:
            label_values = repair._get_portal_shipping_label_download_values(
                operation_id,
                user=request.env.user,
            )
        except AccessError:
            raise NotFound()

        if not label_values:
            raise NotFound()

        filename = label_values["filename"]
        ascii_filename = filename.encode("ascii", "ignore").decode("ascii") or "shipping-label.pdf"
        headers = [
            ("Content-Type", label_values["mimetype"]),
            ("Cache-Control", "private, no-store, max-age=0"),
            ("X-Content-Type-Options", "nosniff"),
            (
                "Content-Disposition",
                "attachment; filename=\"%s\"; filename*=UTF-8''%s"
                % (ascii_filename.replace('"', ""), quote(filename, safe="")),
            ),
        ]
        return request.make_response(base64.b64decode(label_values["content"]), headers)
