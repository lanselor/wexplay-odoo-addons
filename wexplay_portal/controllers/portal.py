# -*- coding: utf-8 -*-

import base64

from werkzeug.exceptions import NotFound

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request


class WexplayCustomerPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        repair_model = request.env["repair.order"]
        if "repair_count" in counters:
            values["repair_count"] = repair_model.search_count(
                repair_model._get_portal_visible_domain(request.env.user)
            )

        values["show_it_maintenance_entry"] = self._is_it_maintenance_customer()
        return values

    def _is_it_maintenance_customer(self):
        partner = request.env.user.partner_id.commercial_partner_id
        return (
            "x_is_it_maintenance_customer" in partner._fields
            and bool(partner.x_is_it_maintenance_customer)
        )

    def _get_portal_repair_domain(self, filterby="all"):
        domain = request.env["repair.order"]._get_portal_visible_domain(request.env.user)
        if filterby == "active":
            return domain + [
                ("state", "not in", request.env["repair.order"]._get_portal_done_states())
            ]
        if filterby == "done":
            return domain + [
                ("state", "in", request.env["repair.order"]._get_portal_done_states())
            ]
        return domain

    def _get_portal_repair_or_404(self, repair_id):
        repair = request.env["repair.order"].search(
            self._get_portal_repair_domain() + [("id", "=", repair_id)],
            limit=1,
        )
        if not repair:
            raise NotFound()
        return repair

    def _get_portal_repair_image_or_404(self, repair_id, image_id):
        repair = self._get_portal_repair_or_404(repair_id)
        image = repair._get_portal_image_records().filtered(lambda rec: rec.id == image_id)[:1]
        if not image:
            raise NotFound()
        return repair, image

    def _get_repair_searchbar_filters(self):
        return {
            "all": {
                "label": _("All"),
                "domain": [],
            },
            "active": {
                "label": _("Active"),
                "domain": [
                    ("state", "not in", request.env["repair.order"]._get_portal_done_states())
                ],
            },
            "done": {
                "label": _("Completed"),
                "domain": [
                    ("state", "in", request.env["repair.order"]._get_portal_done_states())
                ],
            },
        }

    @http.route(
        ["/my/repairs", "/my/repairs/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_repairs(self, page=1, filterby="all", **kw):
        values = self._prepare_portal_layout_values()
        repair_model = request.env["repair.order"]
        searchbar_filters = self._get_repair_searchbar_filters()
        filterby = filterby if filterby in searchbar_filters else "all"
        domain = self._get_portal_repair_domain(filterby=filterby)

        repairs_count = repair_model.search_count(domain)
        pager = portal_pager(
            url="/my/repairs",
            url_args={"filterby": filterby},
            total=repairs_count,
            page=page,
            step=self._items_per_page,
        )
        repairs = repair_model.search(
            domain,
            order="create_date desc, id desc",
            limit=self._items_per_page,
            offset=pager["offset"],
        )

        values.update(
            {
                "page_name": "repair",
                "default_url": "/my/repairs",
                "pager": pager,
                "repairs": repairs,
                "repair_count": repairs_count,
                "filterby": filterby,
                "searchbar_filters": searchbar_filters,
            }
        )
        return request.render("wexplay_portal.portal_my_repairs", values)

    @http.route(
        ["/my/repairs/<int:repair_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_repair_page(self, repair_id, **kw):
        repair = self._get_portal_repair_or_404(repair_id)
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "repair_detail",
                "repair": repair,
            }
        )
        return request.render("wexplay_portal.portal_repair_page", values)

    @http.route(
        ["/my/it-maintenance"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_it_maintenance_page(self, **kw):
        if not self._is_it_maintenance_customer():
            raise NotFound()

        values = self._prepare_portal_layout_values()
        values.update({"page_name": "it_maintenance"})
        return request.render("wexplay_portal.portal_it_maintenance_page", values)

    @http.route(
        ["/my/repairs/<int:repair_id>/images/<int:image_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_repair_image(self, repair_id, image_id, download=False, **kw):
        _repair, image = self._get_portal_repair_image_or_404(repair_id, image_id)
        dms_file = image.sudo().dms_file_id
        if not dms_file:
            raise NotFound()

        binary = dms_file.image_1920 or dms_file.content
        if not binary:
            raise NotFound()

        filename = image.dms_file_name or image.name or f"repair-image-{image.id}"
        headers = [("Content-Type", dms_file.mimetype or "application/octet-stream")]
        if str(download).lower() in ("1", "true", "yes"):
            headers.append(("Content-Disposition", f'attachment; filename="{filename}"'))
        return request.make_response(base64.b64decode(binary), headers)
