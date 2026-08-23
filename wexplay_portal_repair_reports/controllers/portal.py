# -*- coding: utf-8 -*-

import base64
from urllib.parse import quote

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


class WexplayPortalRepairReports(http.Controller):
    def _get_portal_repair_or_404(self, repair_id):
        repair_model = request.env["repair.order"]
        repair = repair_model.search(
            repair_model._get_portal_visible_domain(request.env.user) + [("id", "=", repair_id)],
            limit=1,
        )
        if not repair:
            raise NotFound()
        return repair

    @http.route(
        ["/my/repairs/<int:repair_id>/service-report/<string:identity_mode>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_repair_service_report(self, repair_id, identity_mode, **kwargs):
        if identity_mode not in ("wexplay", "custom"):
            raise NotFound()
        repair = self._get_portal_repair_or_404(repair_id)
        pdf_bytes = repair._render_portal_sat_report_pdf(identity_mode)
        repair._log_portal_sat_report_download(identity_mode, user=request.env.user)
        filename = "informe-sat-%s.pdf" % (repair.name or repair.id)
        ascii_filename = filename.encode("ascii", "ignore").decode("ascii") or "informe-sat.pdf"
        headers = [
            ("Content-Type", "application/pdf"),
            ("Cache-Control", "private, no-store, max-age=0"),
            ("X-Content-Type-Options", "nosniff"),
            (
                "Content-Disposition",
                "attachment; filename=\"%s\"; filename*=UTF-8''%s"
                % (ascii_filename, quote(filename, safe="")),
            ),
        ]
        return request.make_response(pdf_bytes, headers)

    @http.route(["/my/repair-report-brand"], type="http", auth="user", website=True)
    def portal_repair_report_brand(self, **kwargs):
        brand_model = request.env["wex.portal.sat.report.brand"]
        brand = brand_model._get_or_create_portal_brand_for_user()
        brand._check_portal_manager()
        return request.render("wexplay_portal_repair_reports.portal_repair_report_brand", {
            "brand": brand,
            "error": kwargs.get("error"),
            "countries": request.env["res.country"].search([], order="name"),
        })

    @http.route(["/my/repair-report-brand/save"], type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def portal_repair_report_brand_save(self, **post):
        brand = request.env["wex.portal.sat.report.brand"]._get_or_create_portal_brand_for_user()
        brand._check_portal_manager()
        values = {
            "identity_source": post.get("identity_source") if post.get("identity_source") in ("billing", "custom") else "billing",
            "name": post.get("name", "").strip(),
            "vat": post.get("vat", "").strip(),
            "street": post.get("street", "").strip(),
            "street2": post.get("street2", "").strip(),
            "zip": post.get("zip", "").strip(),
            "city": post.get("city", "").strip(),
            "phone": post.get("phone", "").strip(),
            "email": post.get("email", "").strip(),
            "website": post.get("website", "").strip(),
            "primary_color": post.get("primary_color", "#7b68b5").strip(),
            "country_id": int(post["country_id"]) if post.get("country_id", "").isdigit() else False,
            "state_id": int(post["state_id"]) if post.get("state_id", "").isdigit() else False,
        }
        logo = request.httprequest.files.get("logo")
        if logo and logo.filename:
            values["logo"] = base64.b64encode(logo.read())
        try:
            brand.write(values)
        except ValidationError:
            return request.redirect("/my/repair-report-brand?error=invalid")
        return request.redirect("/my/repair-report-brand")
