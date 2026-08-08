# -*- coding: utf-8 -*-

import json

from odoo import http
from odoo.http import request


class RepairMediaUploadController(http.Controller):
    @http.route("/wexplay/repair/media/upload", type="http", auth="user", methods=["POST"])
    def upload_repair_video(self, repair_id, **kwargs):
        repair = request.env["repair.order"].browse(int(repair_id)).exists()
        upload = request.httprequest.files.get("ufile")
        if not repair or not upload:
            return request.make_response(json.dumps({"error": "Invalid upload."}), status=400)
        try:
            job = repair.create_video_processing_job(upload.filename, upload.read())
        except Exception as exc:
            return request.make_response(json.dumps({"error": str(exc)}), status=400)
        return request.make_response(
            json.dumps({"job_id": job.id, "state": job.state}),
            headers=[("Content-Type", "application/json")],
        )
