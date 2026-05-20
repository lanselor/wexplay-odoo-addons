# -*- coding: utf-8 -*-

from odoo import http
from odoo.addons.wexplay_portal.controllers.portal import WexplayCustomerPortal
from odoo.http import request


class WexplayPortalRepairCommunication(WexplayCustomerPortal):
    @http.route(
        ["/my/repairs/<int:repair_id>/conversation/live"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_repair_conversation_live(self, repair_id, **_kwargs):
        repair = self._get_portal_repair_or_404(repair_id)
        payload = repair._get_portal_repair_conversation_values(customer_view=True)
        return request.make_json_response(payload)

    @http.route(
        ["/my/repairs/<int:repair_id>/conversation/message"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_repair_conversation_message(self, repair_id, **post):
        repair = self._get_portal_repair_or_404(repair_id)
        body = (post.get("body") or "").strip()
        return_mode = (post.get("return_mode") or "").strip()
        if body:
            repair._portal_post_customer_conversation_message(body)
        if return_mode == "popup":
            return request.redirect(
                "/my/repairs/%s?open_portal_chat=1#portalRepairChatPopup" % repair.id
            )
        return request.redirect(
            "/my/repairs/%s?tab=conversation#portalRepairConversationComposer" % repair.id
        )
