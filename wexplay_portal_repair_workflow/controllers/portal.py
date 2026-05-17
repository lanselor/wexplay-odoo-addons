# -*- coding: utf-8 -*-

import json
import logging

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.wexplay_portal.controllers.portal import WexplayCustomerPortal

_logger = logging.getLogger(__name__)


class WexplayRepairWorkflowPortal(WexplayCustomerPortal):
    def _redirect_to_repair_budget(self, repair_id, result=None, debug=False):
        url = "/my/repairs/%s/budget" % repair_id
        query_items = []
        if result:
            query_items.append("result=%s" % result)
        if debug:
            query_items.append("debug=1")
        if query_items:
            url = "%s?%s" % (url, "&".join(query_items))
        return request.redirect(url)

    def _get_budget_action_error_result(self, exception):
        if isinstance(exception, AccessError):
            raise NotFound()
        return "error"

    def _is_portal_budget_debug_enabled(self, kw=None):
        kw = kw or {}
        return str(kw.get("debug") or "").lower() in ("1", "true", "yes", "on")

    @http.route(
        ["/my/repairs/<int:repair_id>/budget"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_repair_budget_page(self, repair_id, result=None, **kw):
        repair = self._get_portal_repair_or_404(repair_id)
        debug_enabled = self._is_portal_budget_debug_enabled(kw)
        values = self._prepare_portal_layout_values()
        budget_values = repair._get_portal_budget_summary_values()
        debug_values = {}
        if debug_enabled:
            debug_values = repair._log_portal_budget_debug_snapshot(
                "page_load",
                user=request.env.user,
                extra={"result": result or ""},
            )
            _logger.info(
                "Portal budget page debug enabled for repair %s and user %s",
                repair.id,
                request.env.user.id,
            )
        repair._create_portal_repair_event("budget_viewed", user=request.env.user)
        repair = budget_values["repair"]
        values.update(
            {
                "page_name": "repair_budget",
                "repair": repair,
                "budget_values": budget_values,
                "debug_enabled": debug_enabled,
                "debug_values": debug_values,
                "debug_values_json": json.dumps(debug_values) if debug_values else "{}",
                "result": result,
            }
        )
        return request.render(
            "wexplay_portal_repair_workflow.portal_repair_budget_page",
            values,
        )

    @http.route(
        ["/my/repairs/<int:repair_id>/budget/accept"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_repair_budget_accept(self, repair_id, **kw):
        repair = self._get_portal_repair_or_404(repair_id)
        debug_enabled = self._is_portal_budget_debug_enabled(kw)
        try:
            repair.action_portal_accept_budget(user=request.env.user)
        except (AccessError, UserError) as exception:
            repair._log_portal_budget_debug_snapshot(
                "accept_error",
                user=request.env.user,
                extra={
                    "error_type": exception.__class__.__name__,
                    "error_message": str(exception),
                },
            )
            result = self._get_budget_action_error_result(exception)
            return self._redirect_to_repair_budget(
                repair_id,
                result=result,
                debug=debug_enabled,
            )
        return self._redirect_to_repair_budget(
            repair_id,
            result="accepted",
            debug=debug_enabled,
        )

    @http.route(
        ["/my/repairs/<int:repair_id>/budget/reject"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_repair_budget_reject(self, repair_id, **kw):
        repair = self._get_portal_repair_or_404(repair_id)
        debug_enabled = self._is_portal_budget_debug_enabled(kw)
        try:
            repair.action_portal_reject_budget(user=request.env.user)
        except (AccessError, UserError) as exception:
            repair._log_portal_budget_debug_snapshot(
                "reject_error",
                user=request.env.user,
                extra={
                    "error_type": exception.__class__.__name__,
                    "error_message": str(exception),
                },
            )
            result = self._get_budget_action_error_result(exception)
            return self._redirect_to_repair_budget(
                repair_id,
                result=result,
                debug=debug_enabled,
            )
        return self._redirect_to_repair_budget(
            repair_id,
            result="rejected",
            debug=debug_enabled,
        )
