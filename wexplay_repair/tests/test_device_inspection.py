from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDeviceInspection(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({"name": "Inspection test device"})
        cls.partner = cls.env["res.partner"].create({"name": "Inspection test customer"})
        cls.repair = cls.env["repair.order"].create({
            "product_id": cls.product.id,
            "partner_id": cls.partner.id,
        })
        cls.screen = cls.env.ref("wexplay_repair.device_condition_broken_screen")
        cls.hinges = cls.env.ref("wexplay_repair.device_condition_laptop_hinges")

    def _marks(self, device_type="mobile"):
        return {"device_type": device_type, "front": [[[0.1, 0.2], [0.3, 0.4]]], "back": []}

    def test_type_required_for_description_and_conditions(self):
        for values in (
            {"x_device_description": "Damaged frame"},
            {"x_device_condition_ids": [Command.set(self.screen.ids)]},
            {"x_device_inspection_marks": self._marks()},
        ):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self.repair.write(values)

    def test_valid_inspection_roundtrip_and_clear(self):
        self.repair.write({
            "x_device_type": "mobile",
            "x_device_description": "Black, 128 GB",
            "x_device_condition_ids": [Command.set(self.screen.ids)],
            "x_device_inspection_marks": self._marks(),
        })
        self.repair.invalidate_recordset()
        self.assertEqual(self.repair.x_device_inspection_marks, self._marks())
        self.assertEqual(self.repair.x_device_condition_ids, self.screen)
        self.assertEqual(self.repair.x_device_description, "Black, 128 GB")
        self.repair.write({"x_device_condition_ids": [Command.clear()], "x_device_inspection_marks": False})
        self.assertEqual(self.repair.x_device_description, "Black, 128 GB")

    def test_type_change_resets_evidence_and_preserves_description(self):
        self.repair.write({
            "x_device_type": "mobile", "x_device_inspection_marks": self._marks(),
            "x_device_description": "Black, 128 GB",
            "x_device_condition_ids": [Command.set(self.screen.ids)],
        })
        self.repair.x_device_type = "tablet"
        self.assertFalse(self.repair.x_device_inspection_marks)
        self.assertFalse(self.repair.x_device_condition_ids)
        self.assertEqual(self.repair.x_device_description, "Black, 128 GB")

    def test_same_type_preserves_evidence(self):
        self.repair.write({"x_device_type": "mobile", "x_device_inspection_marks": self._marks()})
        self.repair.write({"x_device_type": "mobile"})
        self.assertEqual(self.repair.x_device_inspection_marks, self._marks())

    def test_type_change_can_save_new_inspection_from_modal(self):
        self.repair.write({"x_device_type": "mobile", "x_device_inspection_marks": self._marks()})
        self.repair.write({
            "x_device_type": "laptop", "x_device_inspection_marks": self._marks("laptop"),
            "x_device_condition_ids": [Command.set(self.hinges.ids)],
        })
        self.assertEqual(self.repair.x_device_inspection_marks, self._marks("laptop"))
        self.assertEqual(self.repair.x_device_condition_ids, self.hinges)

    def test_multi_record_type_change_only_resets_changed_records(self):
        other = self.repair.copy({"x_device_type": "tablet"})
        self.repair.write({"x_device_type": "mobile", "x_device_inspection_marks": self._marks()})
        other.write({"x_device_inspection_marks": self._marks("tablet")})
        (self.repair | other).write({"x_device_type": "tablet"})
        self.assertFalse(self.repair.x_device_inspection_marks)
        self.assertEqual(other.x_device_inspection_marks, self._marks("tablet"))

    def test_specific_conditions_match_type(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.repair.write({"x_device_type": "mobile", "x_device_condition_ids": [Command.set(self.hinges.ids)]})
        self.repair.write({"x_device_type": "laptop", "x_device_condition_ids": [Command.set(self.hinges.ids)]})

    def test_invalid_coordinates_and_payloads_rejected(self):
        self.repair.x_device_type = "mobile"
        bad_payloads = [[[0, 0]], {"front": []}, {"device_type": "mobile", "front": [], "back": [], "svg": "markup"}]
        for point in ([2, 0], [True, 0], [float("inf"), 0], [0], "0,0"):
            bad_payloads.append({"device_type": "mobile", "front": [[point]], "back": []})
        bad_payloads.append({"device_type": "mobile", "front": [[]], "back": []})
        for payload in bad_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError), self.cr.savepoint():
                self.repair.x_device_inspection_marks = payload

    def test_historical_untyped_description_does_not_block_unrelated_write(self):
        # Simula datos previos sin imponer una migración que bloquee el trabajo diario.
        self.env.flush_all()
        self.cr.execute("UPDATE repair_order SET x_device_description = %s WHERE id = %s", ["Legacy text", self.repair.id])
        self.repair.invalidate_recordset()
        self.repair.x_accessories = "Charger"
        self.assertEqual(self.repair.x_device_description, "Legacy text")
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.repair.x_device_description = "Edited without type"

    def test_stroke_limits(self):
        self.repair.x_device_type = "mobile"
        for strokes in ([[[0.1, 0.1]]] * 501, [[[0.1, 0.1]] * 4001], [[[0.1, 0.1]] * 4000] * 6):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self.repair.x_device_inspection_marks = {
                    "device_type": "mobile", "front": strokes, "back": [],
                }

    def test_other_device_type_allows_text_without_diagram(self):
        self.repair.write({"x_device_type": "other", "x_device_description": "Case scratched"})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.repair.x_device_inspection_marks = self._marks("other")

    def test_console_formats_roundtrip(self):
        formats = self.env["repair.order"].get_device_inspection_diagrams()["console"]["formats"]
        self.assertEqual(len(formats), 3)
        for format_info in formats:
            with self.subTest(console_format=format_info["value"]):
                marks = self._marks("console")
                marks["console_format"] = format_info["value"]
                marks["back"] = [[[0.6, 0.5], [0.7, 0.6]]]
                self.repair.write({
                    "x_device_type": "console",
                    "x_device_description": "Console reception text",
                    "x_device_condition_ids": [Command.set(self.screen.ids)],
                    "x_device_inspection_marks": marks,
                })
                self.repair.invalidate_recordset()
                self.assertEqual(self.repair.x_device_type, "console")
                self.assertEqual(self.repair.x_device_inspection_marks, marks)
                self.assertEqual(self.repair.x_device_condition_ids, self.screen)

    def test_console_format_saved_without_strokes_and_reset_on_device_change(self):
        marks = {"device_type": "console", "console_format": "desktop", "front": [], "back": []}
        self.repair.write({"x_device_type": "console", "x_device_inspection_marks": marks})
        self.repair.invalidate_recordset()
        self.assertEqual(self.repair.x_device_inspection_marks, marks)
        self.repair.x_device_type = "mobile"
        self.assertFalse(self.repair.x_device_inspection_marks)

    def test_invalid_console_format_rejected(self):
        self.repair.x_device_type = "console"
        payloads = [self._marks("console")]
        for value in ("unknown", "", False, [], {}):
            marks = self._marks("console")
            marks["console_format"] = value
            payloads.append(marks)
        for marks in payloads:
            with self.subTest(payload=marks), self.assertRaises(ValidationError), self.cr.savepoint():
                self.repair.x_device_inspection_marks = marks
        mobile_marks = self._marks()
        mobile_marks["console_format"] = "desktop"
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.repair.write({"x_device_type": "mobile", "x_device_inspection_marks": mobile_marks})

    def test_console_format_change_preserves_text_and_tags(self):
        marks = self._marks("console")
        marks["console_format"] = "desktop"
        self.repair.write({
            "x_device_type": "console", "x_device_inspection_marks": marks,
            "x_device_condition_ids": [Command.set(self.screen.ids)],
            "x_device_description": "Keep reception text",
        })
        self.repair.x_device_inspection_marks = {
            "device_type": "console", "console_format": "handheld_pc", "front": [], "back": [],
        }
        self.assertEqual(self.repair.x_device_type, "console")
        self.assertEqual(self.repair.x_device_description, "Keep reception text")
        self.assertEqual(self.repair.x_device_condition_ids, self.screen)

    def test_additional_device_inspections_roundtrip(self):
        conditions = {
            "all_in_one": "device_condition_all_in_one_stand",
            "mini_pc": "device_condition_mini_pc_ports",
            "monitor": "device_condition_monitor_stand",
            "smartwatch": "device_condition_smartwatch_strap",
        }
        diagrams = self.env["repair.order"].get_device_inspection_diagrams()
        for device_type, xmlid in conditions.items():
            with self.subTest(device_type=device_type):
                condition = self.env.ref("wexplay_repair." + xmlid)
                marks = self._marks(device_type)
                marks["back"] = [[[0.6, 0.5], [0.7, 0.6]]]
                self.repair.write({
                    "x_device_type": device_type,
                    "x_device_description": "Inspection text",
                    "x_device_inspection_marks": marks,
                    "x_device_condition_ids": [Command.set(condition.ids)],
                })
                self.repair.invalidate_recordset()
                self.assertEqual(self.repair.x_device_inspection_marks, marks)
                self.assertEqual(self.repair.x_device_condition_ids, condition)
                self.assertEqual(self.repair.x_device_description, "Inspection text")
                self.assertEqual(set(diagrams[device_type]), {"front", "back"})

    def test_additional_device_conditions_reject_wrong_type(self):
        strap = self.env.ref("wexplay_repair.device_condition_smartwatch_strap")
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.repair.write({
                "x_device_type": "monitor",
                "x_device_condition_ids": [Command.set(strap.ids)],
            })

    def test_portal_has_no_access_to_inspection_or_catalog(self):
        portal = new_test_user(self.env, login="inspection_portal", groups="base.group_portal")
        with self.assertRaises(AccessError):
            self.screen.with_user(portal).read(["name"])
        with self.assertRaises(AccessError):
            self.repair.with_user(portal).read(["x_device_inspection_marks", "x_device_condition_ids"])
        with self.assertRaises(AccessError):
            self.env["repair.order"].with_user(portal).get_device_inspection_diagrams()

    def test_internal_user_cannot_edit_catalog(self):
        user = new_test_user(self.env, login="inspection_internal", groups="base.group_user")
        self.assertEqual(self.screen.with_user(user).read(["name"])[0]["id"], self.screen.id)
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.screen.with_user(user).write({"name": "Changed"})

    def test_repair_company_rule_covers_inspection(self):
        other_company = self.env["res.company"].create({"name": "Inspection other company"})
        user = new_test_user(
            self.env, login="inspection_technician", groups="stock.group_stock_user",
            company_id=other_company.id, company_ids=[Command.set(other_company.ids)],
        )
        with self.assertRaises(AccessError):
            self.repair.with_user(user).read(["x_device_inspection_marks"])
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.repair.with_user(user).write({"x_device_type": "mobile", "x_device_description": "Not allowed"})
