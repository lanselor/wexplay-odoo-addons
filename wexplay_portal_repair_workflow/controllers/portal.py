# -*- coding: utf-8 -*-

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.wexplay_portal.controllers.portal import WexplayCustomerPortal


class WexplayRepairWorkflowPortal(WexplayCustomerPortal):
    def _redirect_to_repair_budget(self, repair_id, result=None):
        url = "/my/repairs/%s/budget" % repair_id
        if result:
            url = "%s?result=%s" % (url, result)
        return request.redirect(url)

    def _get_budget_action_error_result(self, exception):
        if isinstance(exception, AccessError):
            raise NotFound()
        return "error"

    @http.route(
        ["/my/repairs/<int:repair_id>/budget"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_repair_budget_page(self, repair_id, result=None, **kw):
        repair = self._get_portal_repair_or_404(repair_id)
        values = self._prepare_portal_layout_values()
        budget_values = repair._get_portal_budget_summary_values()
        repair._create_portal_repair_event("budget_viewed", user=request.env.user)
        values.update(
            {
                "page_name": "repair_budget",
                "repair": repair,
                "budget_values": budget_values,
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
        try:
            repair.action_portal_accept_budget(user=request.env.user)
        except (AccessError, UserError) as exception:
            result = self._get_budget_action_error_result(exception)
            return self._redirect_to_repair_budget(repair_id, result=result)
        return self._redirect_to_repair_budget(repair_id, result="accepted")

    @http.route(
        ["/my/repairs/<int:repair_id>/budget/reject"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_repair_budget_reject(self, repair_id, **kw):
        repair = self._get_portal_repair_or_404(repair_id)
        try:
            repair.action_portal_reject_budget(user=request.env.user)
        except (AccessError, UserError) as exception:
            result = self._get_budget_action_error_result(exception)
            return self._redirect_to_repair_budget(repair_id, result=result)
        return self._redirect_to_repair_budget(repair_id, result="rejected")
