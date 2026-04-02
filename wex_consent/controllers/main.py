# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from werkzeug.exceptions import Forbidden


class WexConsentController(http.Controller):
    @http.route("/wex_consent/kiosk", type="http", auth="user", website=False)
    def wex_consent_kiosk(self, **kwargs):
        if not (
            request.env.user.has_group("wex_consent.group_wex_consent_kiosk")
            or request.env.user.has_group("wex_consent.group_wex_consent_manager")
        ):
            raise Forbidden()
        action = request.env.ref("wex_consent.action_wex_consent_kiosk_client")
        return request.render(
            "wex_consent.kiosk_entry_page",
            {
                "kiosk_src": "/web#action=%s" % action.id,
            },
        )
