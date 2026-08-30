# -*- coding: utf-8 -*-

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.wexplay_portal.controllers.portal import WexplayCustomerPortal

class WexplayRepairWorkflowPortal(WexplayCustomerPortal):
    def _get_portal_repair_domain(self, filterby="active"):
        if filterby == "pending_budget":
            return request.env["repair.order"]._get_portal_pending_budget_domain(
                user=request.env.user
            )
        return super()._get_portal_repair_domain(filterby=filterby)

    def _get_repair_searchbar_filters(self):
        filters = super()._get_repair_searchbar_filters()
        filters["pending_budget"] = {
            "label": "Pendientes",
            "domain": [("x_budget_stage", "=", "waiting_customer")],
        }
        return filters

    @http.route(
        ["/my/repairs", "/my/repairs/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_repairs(self, page=1, filterby="active", **kw):
        response = super().portal_my_repairs(page=page, filterby=filterby, **kw)
        if hasattr(response, "qcontext"):
            response.qcontext["pending_budget_alert"] = request.env[
                "repair.order"
            ]._get_portal_pending_budget_alert_values(user=request.env.user)
        return response

    def _redirect_to_repair_budget(self, repair_id, result=None):
        url = "/my/repairs/%s/budget" % repair_id
        query_items = []
        if result:
            query_items.append("result=%s" % result)
        if query_items:
            url = "%s?%s" % (url, "&".join(query_items))
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
        repair = budget_values["repair"]
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
            )
        return self._redirect_to_repair_budget(
            repair_id,
            result="accepted",
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
            )
        return self._redirect_to_repair_budget(
            repair_id,
            result="rejected",
        )
