# -*- coding: utf-8 -*-

import base64
from urllib.parse import quote

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class WexplayRepairSatReportController(http.Controller):
    @http.route(
        "/wexplay/repair/<int:repair_id>/sat-report/download",
        type="http",
        auth="user",
    )
    def download_sat_report(self, repair_id, **kwargs):
        repair = request.env["repair.order"].browse(repair_id).exists()
        if not repair:
            raise NotFound()
        repair._check_sat_report_access("download")
        dms_file = repair.sudo()._get_sat_report_dms_file()
        if not dms_file:
            raise NotFound()

        filename = repair._get_sat_report_dms_filename()
        ascii_filename = filename.encode("ascii", "ignore").decode("ascii") or "informe-sat.pdf"
        pdf_bytes = base64.b64decode(dms_file.content or b"")
        headers = [
            ("Content-Type", dms_file.mimetype or "application/pdf"),
            ("X-Content-Type-Options", "nosniff"),
            (
                "Content-Disposition",
                "attachment; filename=\"%s\"; filename*=UTF-8''%s"
                % (ascii_filename, quote(filename, safe="")),
            ),
        ]
        return request.make_response(pdf_bytes, headers)
