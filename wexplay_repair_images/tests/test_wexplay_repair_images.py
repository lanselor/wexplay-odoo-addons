# -*- coding: utf-8 -*-

import base64
import os
import subprocess
import tempfile
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestWexplayRepairImages(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.storage = cls.env["dms.storage"].create(
            {
                "name": "Repair Images Test Storage",
                "save_type": "database",
            }
        )
        cls.company = cls.env.company
        cls.company.x_wex_consent_dms_storage_id = cls.storage
        cls.partner = cls.env["res.partner"].create({"name": "Cliente SAT"})
        cls.product = cls.env["product.product"].create({"name": "Equipo SAT"})
        cls.repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
            }
        )

    def test_upload_wizard_creates_image_and_sat_images_directory(self):
        tag = self.env["wex.image.tag"].search([("code", "=", "entrada")], limit=1)
        wizard = self.env["wex.repair.image.upload.wizard"].create(
            {
                "repair_order_id": self.repair.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "filename": "entrada-1.png",
                            "description": "Foto de entrada",
                            "tag_ids": [(6, 0, tag.ids)],
                            "image_file": "ZmFrZV9pbWFnZQ==",
                        },
                    )
                ],
            }
        )

        wizard.action_upload_images()

        image = self.env["wex.image.record"].search(
            [("repair_order_id", "=", self.repair.id)],
            limit=1,
        )
        self.assertTrue(image)
        self.assertEqual(image.dms_file_id.directory_id.name, "IMAGES")
        self.assertEqual(image.dms_file_id.directory_id.parent_id.name, self.repair.name)
        self.assertEqual(image.dms_file_id.directory_id.parent_id.parent_id.name, "SAT")

        chatter_values = self.repair.get_repair_images_chatter_values()
        chatter_image = chatter_values["images"][0]
        self.assertEqual(chatter_image["preview_url"], image.preview_url)
        self.assertEqual(chatter_image["file_size_human"], image.file_size_human)

    def test_upload_images_after_signed_document_reuses_sat_tree_without_blocking(self):
        document = self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "reception"
        )
        document.write(
            {
                "pdf_file": base64.b64encode(b"%PDF-1.4 signed test"),
                "pdf_filename": "reception-signed-test.pdf",
            }
        )
        signed_file = document._store_pdf_in_dms()

        tag = self.env["wex.image.tag"].search([("code", "=", "entrada")], limit=1)
        wizard = self.env["wex.repair.image.upload.wizard"].create(
            {
                "repair_order_id": self.repair.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "filename": "entrada-despues-firma.png",
                            "description": "Foto tras generar documento firmado",
                            "tag_ids": [(6, 0, tag.ids)],
                            "image_file": "ZmFrZV9pbWFnZQ==",
                        },
                    )
                ],
            }
        )

        wizard.action_upload_images()

        image = self.env["wex.image.record"].search(
            [("repair_order_id", "=", self.repair.id)],
            limit=1,
        )
        self.assertTrue(signed_file)
        self.assertTrue(image)
        self.assertEqual(signed_file.directory_id.name, "SIGNATURES")
        self.assertEqual(image.dms_file_id.directory_id.name, "IMAGES")
        self.assertEqual(image.dms_file_id.directory_id.parent_id.id, signed_file.directory_id.parent_id.id)
        self.assertEqual(image.dms_file_id.directory_id.parent_id.parent_id.name, "SAT")

    def test_video_upload_creates_queued_processing_job(self):
        job = self.repair.create_video_processing_job("diagnostico.mp4", b"video source")

        self.assertEqual(job.repair_order_id, self.repair)
        self.assertEqual(job.state, "queued")
        self.assertEqual(job.source_filename, "diagnostico.mp4")
        self.assertTrue(job.source_attachment_id)
        queue_job = self.env["queue.job"].search([("uuid", "=", job.queue_job_uuid)])
        self.assertTrue(queue_job)
        self.assertEqual(queue_job.channel, "root.sat_video")

    def test_video_job_can_run_synchronously_in_queue_job_test_mode(self):
        attachment = self.env["ir.attachment"].create({
            "name": "diagnostico.mp4",
            "raw": b"video source",
            "res_model": "wex.repair.media.process.job",
            "res_id": 0,
            "mimetype": "video/mp4",
        })
        job = self.env["wex.repair.media.process.job"].create({
            "repair_order_id": self.repair.id,
            "source_attachment_id": attachment.id,
            "source_filename": "diagnostico.mp4",
        })

        with patch.object(type(job), "_process_job") as process_job:
            job.with_context(queue_job__no_delay=True).enqueue_processing()

        process_job.assert_called_once()
        self.assertEqual(job.state, "processing")

    def test_video_job_processes_a_real_short_video_in_queue_job_test_mode(self):
        ffmpeg_path = self.env["ir.config_parameter"].get_param(
            "wexplay_repair_images.ffmpeg_path", "ffmpeg"
        )
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_file:
            video_path = video_file.name
        try:
            try:
                subprocess.run(
                    [
                        ffmpeg_path,
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-f",
                        "lavfi",
                        "-i",
                        "color=c=black:s=320x240:d=1",
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        "-y",
                        video_path,
                    ],
                    check=True,
                    timeout=30,
                )
            except FileNotFoundError:
                self.skipTest("FFmpeg no está disponible para ejecutar la prueba multimedia.")
            with open(video_path, "rb") as source:
                content = source.read()
        finally:
            if os.path.exists(video_path):
                os.unlink(video_path)

        attachment = self.env["ir.attachment"].create({
            "name": "diagnostico.mp4",
            "raw": content,
            "res_model": "wex.repair.media.process.job",
            "res_id": 0,
            "mimetype": "video/mp4",
        })
        job = self.env["wex.repair.media.process.job"].create({
            "repair_order_id": self.repair.id,
            "source_attachment_id": attachment.id,
            "source_filename": "diagnostico.mp4",
        })

        job.with_context(queue_job__no_delay=True).enqueue_processing()

        self.assertEqual(job.state, "done")
        self.assertTrue(job.media_id)
        self.assertFalse(job.source_attachment_id)

    def test_cancelling_queued_video_removes_its_temporary_attachment(self):
        job = self.repair.create_video_processing_job("diagnostico.mp4", b"video source")
        attachment = job.source_attachment_id

        job.action_cancel()

        self.assertEqual(job.state, "cancelled")
        self.assertFalse(job.source_attachment_id)
        self.assertFalse(attachment.exists())

    def test_reupload_after_deleting_image_record_uses_new_unique_dms_filename(self):
        tag = self.env["wex.image.tag"].search([("code", "=", "entrada")], limit=1)

        wizard_first = self.env["wex.repair.image.upload.wizard"].create(
            {
                "repair_order_id": self.repair.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "filename": "entrada-1.png",
                            "description": "Primera foto",
                            "tag_ids": [(6, 0, tag.ids)],
                            "image_file": "ZmFrZV9pbWFnZQ==",
                        },
                    )
                ],
            }
        )
        wizard_first.action_upload_images()

        first_image = self.env["wex.image.record"].search(
            [("repair_order_id", "=", self.repair.id)],
            limit=1,
        )
        first_dms_file_name = first_image.dms_file_name
        first_image.unlink()

        wizard_second = self.env["wex.repair.image.upload.wizard"].create(
            {
                "repair_order_id": self.repair.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "filename": "entrada-2.png",
                            "description": "Segunda foto",
                            "tag_ids": [(6, 0, tag.ids)],
                            "image_file": "ZmFrZV9pbWFnZQ==",
                        },
                    )
                ],
            }
        )
        wizard_second.action_upload_images()

        second_image = self.env["wex.image.record"].search(
            [("repair_order_id", "=", self.repair.id)],
            limit=1,
        )
        self.assertTrue(first_dms_file_name)
        self.assertTrue(second_image)
        self.assertNotEqual(second_image.dms_file_name, first_dms_file_name)
