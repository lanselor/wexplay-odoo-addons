import base64
from io import BytesIO
from unittest.mock import patch

from PIL import Image
from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tests import tagged, TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestTeardownLifecycle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.location = cls.env["stock.location"].create({
            "name": "Teardown destination", "usage": "internal", "company_id": cls.company.id,
        })
        cls.company.wex_teardown_default_location_id = cls.location
        cls.brand = cls.env["wex.repair.brand"].create({"name": "Teardown test brand"})
        cls.model = cls.env["wex.repair.device_model"].create({
            "name": "Teardown test model", "device_type": "mobile", "brand_id": cls.brand.id,
        })
        cls.category = cls.env["product.category"].create({"name": "Teardown test category"})
        cls.component = cls.env["wex.teardown.component.type"].create({
            "name": "Teardown test screen", "device_type": "mobile", "product_category_id": cls.category.id,
        })
        cls.template = cls.env["wex.teardown.template"].create({
            "name": "Teardown test template", "device_type": "mobile",
            "line_ids": [Command.create({"component_type_id": cls.component.id, "default_quantity": 1})],
        })
        buf = BytesIO()
        Image.new("RGB", (80, 80), "red").save(buf, format="PNG")
        cls.photo = base64.b64encode(buf.getvalue())
        cls.user = new_test_user(cls.env, login="teardown_operator", groups="wex_teardown.group_wex_teardown_user")

    def _batch(self, **values):
        vals = {"device_type": "mobile", "model_id": self.model.id, "template_id": self.template.id,
                "physical_identity_confirmed": True, "company_id": self.company.id}
        vals.update(values)
        batch = self.env["wex.teardown.batch"].create(vals)
        batch.action_load_template()
        batch.action_mark_review()
        line = batch.line_ids
        line.write({"part_number": "TD-001", "name_final": "Test teardown screen", "list_price": 20,
                    "standard_price": 5, "qc_state": "ok", "decision": "create_new", "tax_ids": [Command.clear()]})
        return batch, line

    def _prepare(self):
        batch, line = self._batch()
        batch.action_validate_teardown()
        line.action_prepare_product()
        return batch, line, line.product_tmpl_id.with_context(active_test=False)

    def test_prepare_archive_and_native_images_then_finalize(self):
        batch, line, product = self._prepare()
        self.assertFalse(product.active)
        self.assertFalse(line.stock_move_id)
        self.assertEqual(line.state, "product_prepared")
        line.action_prepare_product()
        self.assertEqual(line.product_tmpl_id, product)
        with self.assertRaises(UserError):
            line.action_finalize_piece()
        product.image_1920 = self.photo
        image = self.env["product.image"].create({"name": "Extra", "product_tmpl_id": product.id, "image_1920": self.photo})
        self.assertIn(image, product.product_template_image_ids)
        self.assertFalse(product.active)
        with self.assertRaises(UserError):
            product.write({"active": True})
        with self.assertRaises(UserError):
            product.product_variant_ids.write({"active": True})
        with self.assertRaises(UserError):
            product.write({"is_published": True})
        line.action_finalize_piece()
        self.assertTrue(product.active)
        self.assertFalse(product.is_published)
        self.assertEqual(line.stock_move_id.state, "done")
        self.assertEqual(batch.state, "done")
        move = line.stock_move_id
        line.action_finalize_piece()
        self.assertEqual(line.stock_move_id, move)
        self.assertEqual(product.product_variant_id.with_context(location=self.location.id).qty_available, 1)

    def test_stock_failure_rolls_back_activation(self):
        batch, line, product = self._prepare()
        product.image_1920 = self.photo
        with patch.object(type(line), "_create_stock_entry", side_effect=UserError("Simulated stock failure")):
            batch.action_finalize_ready_lines()
        self.assertFalse(product.active)
        self.assertFalse(line.stock_move_id)
        self.assertEqual(line.state, "product_prepared")
        self.assertIn("Simulated", line.validation_message)
        self.assertEqual(batch.error_count, 1)
        line.action_finalize_piece()
        self.assertEqual(line.state, "created")
        self.assertEqual(batch.error_count, 0)

    def test_pending_match_shared_and_cancellation(self):
        batch, line, product = self._prepare()
        other_batch, other = self._batch()
        self.assertIn(product, other._get_duplicate_candidates())
        other.action_choose_existing_product(product.id)
        other_batch.action_validate_teardown()
        other.action_prepare_product()
        batch.action_cancel()
        self.assertEqual(product.wex_teardown_origin_line_id, other)
        product.image_1920 = self.photo
        other.action_finalize_piece()
        self.assertTrue(product.active)
        self.assertFalse(line.stock_move_id)

    def test_new_product_changes_not_overwritten(self):
        batch, line, product = self._prepare()
        product.write({"list_price": 75, "image_1920": self.photo})
        line.action_finalize_piece()
        self.assertEqual(product.list_price, 75)
        with self.assertRaises(UserError):
            batch.action_cancel()
        with self.assertRaises(UserError):
            line.write({"quantity": 2})
        with self.assertRaises(UserError):
            batch.action_reset_to_review()

    def test_existing_changes_require_refresh(self):
        batch, line, product = self._prepare()
        product.image_1920 = self.photo
        line.action_finalize_piece()
        second_batch, second = self._batch()
        second.action_choose_existing_product(product.id)
        second_batch.action_validate_teardown()
        second.action_prepare_product()
        product.list_price = 80
        with self.assertRaises(UserError):
            second.action_finalize_piece()
        second.action_refresh_product_proposal()
        second.action_finalize_piece()
        self.assertEqual(product.list_price, 80)

    def test_duplicate_creation_rejected_after_stale_search(self):
        batch, line, product = self._prepare()
        other_batch, other = self._batch()
        other_batch.action_validate_teardown()
        with self.assertRaises(UserError):
            other.action_prepare_product()
        self.assertFalse(other.product_tmpl_id)

    def test_cancel_keeps_photos_and_no_reactivation(self):
        batch, line, product = self._prepare()
        product.image_1920 = self.photo
        batch.action_cancel()
        self.assertEqual(product.wex_teardown_preparation_state, "cancelled")
        self.assertTrue(product.image_1920)
        with self.assertRaises(UserError):
            line.action_finalize_piece()
        with self.assertRaises(UserError):
            product.write({"active": True})

    def test_identity_required_and_unique(self):
        with self.assertRaises(UserError):
            self._batch(physical_identity_confirmed=False)
        batch, line = self._batch(device_identifier_type="imei", device_identifier="123456789012345")
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._batch(device_identifier_type="imei", device_identifier="123456789012345")
        batch.action_cancel()
        other, _line = self._batch(device_identifier_type="imei", device_identifier="123456789012345")
        copied = other.copy()
        self.assertFalse(copied.device_identifier)
        self.assertFalse(copied.line_ids)

    def test_rpc_cannot_forge_execution(self):
        batch, line = self._batch()
        with self.assertRaises(UserError):
            line.write({"state": "created"})
        with self.assertRaises(UserError):
            batch.write({"state": "done"})
        with self.assertRaises(UserError):
            line.with_context(_teardown_token=True).write({"state": "created"})

    def test_operator_can_complete_native_media(self):
        batch, line = self._batch()
        batch = batch.with_user(self.user)
        line = line.with_user(self.user)
        batch.action_validate_teardown()
        line.action_prepare_product()
        product = line.product_tmpl_id.with_context(active_test=False)
        product.image_1920 = self.photo
        self.env["product.image"].with_user(self.user).create({
            "name": "Operator extra", "product_tmpl_id": product.id, "image_1920": self.photo,
        })
        line.action_finalize_piece()
        self.assertEqual(line.stock_move_id.state, "done")

    def test_missing_part_number_confirmation(self):
        batch, line = self._batch()
        line.write({"part_number": False, "missing_part_number_confirmed": True})
        batch.action_validate_teardown()
        line.action_prepare_product()
        self.assertEqual(line.state, "product_prepared")

    def test_tracking_not_supported_before_activation(self):
        batch, line, product = self._prepare()
        product.write({"image_1920": self.photo, "tracking": "serial"})
        with self.assertRaises(UserError):
            line.action_finalize_piece()
        self.assertFalse(product.active)

    def test_other_company_cannot_be_selected_or_edited(self):
        other_company = self.env["res.company"].create({"name": "Teardown other company"})
        product = self.env["product.template"].create({
            "name": "Other company part", "company_id": other_company.id, "wex_condition": "refurbished",
        })
        image = self.env["product.image"].create({"name": "Other company", "product_tmpl_id": product.id, "image_1920": self.photo})
        batch, line = self._batch()
        with self.assertRaises(AccessError):
            line.with_user(self.user).action_choose_existing_product(product.id)
        with self.assertRaises(AccessError):
            image.with_user(self.user).write({"name": "Forbidden"})

    def test_product_code_on_archived_product(self):
        sequence = self.env["ir.sequence"].create({"name": "Teardown codes", "padding": 4})
        self.env["wex.product.code.rule"].create({
            "categ_id": self.category.id, "company_id": self.company.id,
            "prefix": "TD", "sequence_id": sequence.id,
        })
        batch, line = self._batch()
        batch.with_user(self.user).action_validate_teardown()
        line.with_user(self.user).action_prepare_product()
        self.assertTrue(line.product_tmpl_id.with_context(active_test=False).default_code.startswith("TD-"))

    def test_historical_created_line_is_not_reprocessed(self):
        batch, line, product = self._prepare()
        product.image_1920 = self.photo
        line.action_finalize_piece()
        move = line.stock_move_id
        product.image_1920 = False
        line.action_finalize_piece()
        self.assertEqual(line.stock_move_id, move)
        self.assertEqual(batch.state, "done")

    def test_native_gallery_and_pending_views_for_operator(self):
        product_view = self.env["product.template"].with_user(self.user).get_view(
            self.env.ref("product.product_template_only_form_view").id, "form",
        )
        self.assertIn("product_template_image_ids", product_view["arch"])
        batch_view = self.env["wex.teardown.batch"].with_user(self.user).get_view(
            self.env.ref("wex_teardown.view_wex_teardown_batch_form").id, "form",
        )
        self.assertIn("action_finalize_ready_lines", batch_view["arch"])
        self.assertIn("prepared_line_ids", batch_view["arch"])

    def test_manager_can_recover_cancelled_preparation(self):
        manager = new_test_user(self.env, login="teardown_manager", groups="wex_teardown.group_wex_teardown_manager")
        batch, line, product = self._prepare()
        product.image_1920 = self.photo
        batch.action_cancel()
        other_batch, other = self._batch()
        other = other.with_user(manager)
        other.action_choose_existing_product(product.id)
        other_batch.with_user(manager).action_validate_teardown()
        other.action_prepare_product()
        self.assertEqual(product.wex_teardown_origin_line_id, other)
        other.action_finalize_piece()
        self.assertTrue(product.active)
    def test_zebra_batch_label_payload(self):
        batch, _line = self._batch()
        payload = batch.action_get_zebra_batch_label_payload()
        self.assertEqual(payload["document_code"], "teardown_batch_label_zebra")
        self.assertEqual(payload["reference"], batch.name)
        self.assertEqual(
            payload["report_name"],
            "wex_teardown.report_teardown_batch_label_zebra_76x25",
        )
