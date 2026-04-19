# -*- coding: utf-8 -*-

import base64
from urllib.parse import urlencode

from werkzeug.exceptions import NotFound

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request
from odoo.osv import expression


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

    def _get_portal_repair_domain(self, filterby="active"):
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
            self._get_portal_repair_domain(filterby="all") + [("id", "=", repair_id)],
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

    def _get_repair_image_binary(self, dms_file, variant="preview", download=False):
        if download:
            return dms_file.content or dms_file.image_1920
        if variant == "thumb":
            return (
                getattr(dms_file, "image_512", False)
                or getattr(dms_file, "image_256", False)
                or getattr(dms_file, "image_128", False)
                or dms_file.image_1920
                or dms_file.content
            )
        return dms_file.image_1920 or dms_file.content

    def _get_repair_searchbar_filters(self):
        return {
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
            "all": {
                "label": _("All"),
                "domain": [],
            },
        }

    def _get_repair_searchbar_inputs(self):
        return {
            "imei": {"label": "IMEI / Serie"},
            "customer_reference": {"label": "Referencia cliente"},
            "equipment": {"label": "Equipo"},
            "issue": {"label": "Incidencia"},
            "sat_reference": {"label": "Referencia SAT"},
        }

    def _get_portal_repair_equipment_search_domain(self, search):
        repair_model = request.env["repair.order"]
        equipment_fields = [
            field_name
            for field_name in ("x_brand", "x_model")
            if field_name in repair_model._fields
        ]
        search_terms = [term for term in (search or "").split() if term]
        if not search_terms or not equipment_fields:
            return []

        domain = []
        for term in search_terms:
            term_domain_parts = [
                [(field_name, "ilike", term)] for field_name in equipment_fields
            ]
            term_domain = expression.OR(term_domain_parts)
            domain = expression.AND([domain, term_domain]) if domain else term_domain
        return domain

    def _get_portal_repair_search_domain(self, search_in, search):
        search = (search or "").strip()
        if not search:
            return []

        search_domains = {
            "imei": [("x_imei", "ilike", search)],
            "customer_reference": [("x_customer_reference", "ilike", search)],
            "issue": [("x_reported_issue", "ilike", search)],
            "sat_reference": [("name", "ilike", search)],
        }
        if search_in == "equipment":
            return []
        return search_domains.get(search_in, [("x_imei", "ilike", search)])

    def _match_portal_repair_equipment_search(self, repair, search):
        search_terms = [term.lower() for term in (search or "").split() if term]
        if not search_terms:
            return True

        searchable_chunks = [
            repair._get_portal_brand_label() or "",
            repair._get_portal_model_label() or "",
            repair._get_portal_product_label() or "",
            repair._get_portal_device_type_label() or "",
        ]
        searchable_text = " ".join(searchable_chunks).lower()
        return all(term in searchable_text for term in search_terms)

    @http.route(
        ["/my/repairs", "/my/repairs/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_repairs(self, page=1, filterby="active", **kw):
        values = self._prepare_portal_layout_values()
        repair_model = request.env["repair.order"]
        searchbar_filters = self._get_repair_searchbar_filters()
        searchbar_inputs = self._get_repair_searchbar_inputs()
        search = (kw.get("search") or "").strip()
        search_in = kw.get("search_in") or "imei"
        filterby = filterby if filterby in searchbar_filters else "active"
        search_in = search_in if search_in in searchbar_inputs else "imei"
        for filter_key, filter_data in searchbar_filters.items():
            url_args = {"filterby": filter_key}
            if search:
                url_args["search"] = search
                url_args["search_in"] = search_in
            filter_data["url"] = "/my/repairs?%s" % urlencode(url_args)
        base_domain = self._get_portal_repair_domain(filterby=filterby)
        search_domain = self._get_portal_repair_search_domain(search_in, search)
        url_args = {"filterby": filterby, "search": search, "search_in": search_in}

        if search and search_in == "equipment":
            visible_repairs = repair_model.search(
                base_domain,
                order="create_date desc, id desc",
            )
            filtered_repairs = visible_repairs.filtered(
                lambda repair: self._match_portal_repair_equipment_search(repair, search)
            )
            repairs_count = len(filtered_repairs)
            pager = portal_pager(
                url="/my/repairs",
                url_args=url_args,
                total=repairs_count,
                page=page,
                step=self._items_per_page,
            )
            repairs = filtered_repairs[pager["offset"] : pager["offset"] + self._items_per_page]
        else:
            domain = expression.AND([base_domain, search_domain])
            repairs_count = repair_model.search_count(domain)
            pager = portal_pager(
                url="/my/repairs",
                url_args=url_args,
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
                "searchbar_inputs": searchbar_inputs,
                "search": search,
                "search_in": search_in,
                "clear_search_url": "/my/repairs?filterby=active",
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
        image_tag = kw.get("image_tag") or ""
        image_filter_values = repair._get_portal_image_filter_values(selected_tag_code=image_tag)
        available_tag_codes = {value["code"] for value in image_filter_values if value["code"]}
        if image_tag and image_tag not in available_tag_codes:
            image_tag = ""
            image_filter_values = repair._get_portal_image_filter_values(selected_tag_code=image_tag)

        for value in image_filter_values:
            value["url"] = (
                "/my/repairs/%s?image_tag=%s" % (repair.id, value["code"])
                if value["code"]
                else "/my/repairs/%s" % repair.id
            )
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "repair_detail",
                "repair": repair,
                "image_tag": image_tag,
                "image_filter_values": image_filter_values,
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
    def portal_repair_image(self, repair_id, image_id, download=False, variant="preview", **kw):
        _repair, image = self._get_portal_repair_image_or_404(repair_id, image_id)
        dms_file = image.sudo().dms_file_id
        if not dms_file:
            raise NotFound()

        is_download = str(download).lower() in ("1", "true", "yes")
        variant = variant if variant in ("thumb", "preview") else "preview"
        binary = self._get_repair_image_binary(dms_file, variant=variant, download=is_download)
        if not binary:
            raise NotFound()

        filename = image.dms_file_name or image.name or f"repair-image-{image.id}"
        headers = [
            ("Content-Type", dms_file.mimetype or "application/octet-stream"),
            ("Cache-Control", "private, no-store, max-age=0" if is_download else "private, max-age=300, must-revalidate"),
            ("X-Content-Type-Options", "nosniff"),
        ]
        if is_download:
            headers.append(("Content-Disposition", f'attachment; filename="{filename}"'))
        else:
            headers.append(("Content-Disposition", f'inline; filename="{filename}"'))
        return request.make_response(base64.b64decode(binary), headers)
