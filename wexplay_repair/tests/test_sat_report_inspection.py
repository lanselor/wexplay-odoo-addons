import base64

from lxml import etree, html

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSatReportInspection(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repair = cls.env["repair.order"].create({
            "partner_id": cls.env["res.partner"].create({"name": "Report inspection customer"}).id,
            "product_id": cls.env["product.product"].create({"name": "Report test device"}).id,
            "x_device_type": "mobile",
        })
        cls.condition = cls.env.ref("wexplay_repair.device_condition_broken_screen")

    def _svg(self, view):
        return etree.fromstring(base64.b64decode(view["src"].split(",", 1)[1]))

    def _red_paths(self, view):
        return self._svg(view).xpath("//*[local-name()='path' and @stroke='#d83a3a']")

    def _render(self):
        report = self.env.ref("wexplay_repair.action_report_sat_service")
        content, _ = self.env["ir.actions.report"]._render_qweb_html(
            report.report_name, self.repair.ids
        )
        return html.fromstring(content)

    def test_empty_inspection_omitted(self):
        self.assertFalse(self.repair._prepare_sat_report_inspection())
        self.assertFalse(self._render().xpath("//*[contains(@class, 'wex_report_inspection')]"))
        self.repair.x_device_description = "   "
        self.assertFalse(self.repair._prepare_sat_report_inspection())

    def test_text_and_tags_without_drawings(self):
        self.repair.write({
            "x_device_description": "Black <case> & screen\nSecond line",
            "x_device_condition_ids": [Command.set(self.condition.ids)],
        })
        data = self.repair._prepare_sat_report_inspection()
        self.assertEqual(data["conditions"], [self.condition.name])
        self.assertFalse(data["views"])
        section = self._render().xpath("//*[contains(@class, 'wex_report_inspection')]")[0]
        self.assertIn(self.repair.x_device_description, section.text_content())
        self.assertFalse(section.xpath(".//case"))
        self.assertFalse(section.xpath(".//img"))

    def test_tags_alone_create_section(self):
        self.repair.x_device_condition_ids = self.condition
        data = self.repair._prepare_sat_report_inspection()
        self.assertFalse(data["description"])
        self.assertEqual(data["conditions"], [self.condition.name])
        self.assertFalse(data["views"])

    def test_one_marked_face_includes_both_faces(self):
        for marked_side in ("front", "back"):
            marks = {"device_type": "mobile", "front": [], "back": []}
            marks[marked_side] = [[[0.1, 0.2], [0.3, 0.4]]]
            self.repair.x_device_inspection_marks = marks
            views = self.repair._prepare_sat_report_inspection()["views"]
            self.assertEqual(len(views), 2)
            self.assertEqual(len(self._red_paths(views[0])), int(marked_side == "front"))
            self.assertEqual(len(self._red_paths(views[1])), int(marked_side == "back"))
            path = self._red_paths(views[0 if marked_side == "front" else 1])[0]
            self.assertEqual(path.get("d"), "M 32.0,80.0 L 96.0,160.0")

    def test_all_diagrams_and_console_formats(self):
        diagrams = self.env["repair.order"].get_device_inspection_diagrams()
        for device_type, diagram in diagrams.items():
            formats = diagram.get("formats", [{"value": None}])
            for console_format in formats:
                with self.subTest(device_type=device_type, console_format=console_format):
                    marks = {"device_type": device_type, "front": [[[0.5, 0.5]]],
                             "back": [[[0.2, 0.8], [0.4, 0.9]]]}
                    if device_type == "console":
                        marks["console_format"] = console_format["value"]
                    self.repair.write({"x_device_type": device_type, "x_device_inspection_marks": marks})
                    views = self.repair._prepare_sat_report_inspection()["views"]
                    self.assertEqual([v["label"] for v in views], [diagram["front"], diagram["back"]])
                    for view in views:
                        self.assertEqual(self._svg(view).get("viewBox"), "0 0 320 400")
                        self.assertEqual(len(self._red_paths(view)), 1)
                    self.assertTrue(self._red_paths(views[0])[0].get("d").endswith(" l 0.1,0"))

    def test_console_metadata_only_omitted(self):
        self.repair.write({"x_device_type": "console", "x_device_inspection_marks": {
            "device_type": "console", "console_format": "desktop", "front": [], "back": [],
        }})
        self.assertFalse(self.repair._prepare_sat_report_inspection())
