# -*- coding: utf-8 -*-

import base64
import io

from PIL import Image

from odoo.exceptions import ValidationError
from odoo.tests.common import SavepointCase

from odoo.addons.wexplay_portal_repair_reports.models.portal_sat_report_brand import (
    MAX_LOGO_UPLOAD_SIZE,
)


class TestPortalSatReportBrand(SavepointCase):
    def test_logo_upload_normalizes_to_report_bounds(self):
        payload = io.BytesIO()
        Image.new("RGB", (1600, 800), "white").save(payload, format="JPEG")

        result = self.env["wex.portal.sat.report.brand"]._prepare_portal_logo_upload(
            io.BytesIO(payload.getvalue())
        )

        with Image.open(io.BytesIO(base64.b64decode(result))) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (1024, 512))

    def test_logo_upload_rejects_non_image_content(self):
        with self.assertRaises(ValidationError):
            self.env["wex.portal.sat.report.brand"]._prepare_portal_logo_upload(
                io.BytesIO(b"not-an-image")
            )

    def test_logo_upload_rejects_files_larger_than_six_megabytes(self):
        with self.assertRaises(ValidationError):
            self.env["wex.portal.sat.report.brand"]._prepare_portal_logo_upload(
                io.BytesIO(b"x" * (MAX_LOGO_UPLOAD_SIZE + 1))
            )
