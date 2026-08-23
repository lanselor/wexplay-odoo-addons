import base64

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestWexVendorBillOcr(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {
                "name": "Proveedor OCR Demo",
                "vat": "B12345678",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto OCR",
                "type": "consu",
                "purchase_ok": True,
            }
        )
        cls.purchase_order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": cls.product.display_name,
                            "product_id": cls.product.id,
                            "product_qty": 2.0,
                            "product_uom": cls.product.uom_po_id.id,
                            "price_unit": 50.0,
                            "date_planned": "2026-08-08 10:00:00",
                        },
                    )
                ],
            }
        )
        cls.purchase_order.button_confirm()

    @classmethod
    def _create_pdf_attachment(cls, name="vendor_bill.pdf", content=b"%PDF-1.4 test"):
        return cls.env["ir.attachment"].create(
            {
                "name": name,
                "type": "binary",
                "datas": base64.b64encode(content),
                "mimetype": "application/pdf",
                "res_model": "purchase.order",
                "res_id": cls.purchase_order.id,
            }
        )

    @classmethod
    def _create_job(cls, **extra_vals):
        vals = {
            "purchase_order_id": cls.purchase_order.id,
            "attachment_id": cls._create_pdf_attachment().id,
        }
        vals.update(extra_vals)
        return cls.env["wex.vendor.bill.ocr.job"].create(vals)

    def test_upload_wizard_creates_attachment_and_draft_job(self):
        wizard = self.env["wex.vendor.bill.ocr.upload.wizard"].create(
            {
                "purchase_order_id": self.purchase_order.id,
                "filename": "supplier_invoice.pdf",
                "pdf_file": base64.b64encode(b"%PDF-1.4 upload test"),
            }
        )

        action = wizard.action_upload_and_enqueue()
        job = self.env["wex.vendor.bill.ocr.job"].browse(action["res_id"])

        self.assertTrue(job.exists())
        self.assertEqual(job.purchase_order_id, self.purchase_order)
        self.assertEqual(job.state, "draft")
        self.assertEqual(job.progress_message, "Queued")
        self.assertEqual(job.attachment_id.res_model, "purchase.order")
        self.assertEqual(job.attachment_id.res_id, self.purchase_order.id)

    def test_upload_wizard_rejects_non_pdf_filename(self):
        wizard = self.env["wex.vendor.bill.ocr.upload.wizard"].create(
            {
                "purchase_order_id": self.purchase_order.id,
                "filename": "supplier_invoice.txt",
                "pdf_file": base64.b64encode(b"plain text"),
            }
        )

        with self.assertRaises(UserError):
            wizard.action_upload_and_enqueue()

    def test_parse_extracted_text_prefers_purchase_context_amounts(self):
        job = self._create_job()
        raw_text = """
            FACTURA FV-2026-0088
            Fecha: 08/08/2026
            Pedido WPO0001
            Base imponible 80,00
            IVA 21,00
            Total 101,00
            Total factura 121,00
        """

        parsed = job._parse_extracted_text(raw_text)

        self.assertEqual(parsed["parsed_supplier_name"], self.vendor.name)
        self.assertEqual(parsed["parsed_supplier_vat"], self.vendor.vat)
        self.assertEqual(parsed["parsed_invoice_number"], "FV-2026-0088")
        self.assertEqual(str(parsed["parsed_invoice_date"]), "2026-08-08")
        self.assertEqual(parsed["parsed_total_amount"], 121.0)
        self.assertEqual(parsed["parsed_untaxed_amount"], self.purchase_order.amount_untaxed)
        self.assertEqual(parsed["parsed_tax_amount"], self.purchase_order.amount_tax)
        self.assertGreater(parsed["confidence_score"], 0.0)

    def test_apply_preconditions_block_duplicate_supplier_invoice_number(self):
        job = self._create_job(
            state="review",
            parsed_supplier_name=self.vendor.name,
            parsed_supplier_vat=self.vendor.vat,
        )
        self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "company_id": self.purchase_order.company_id.id,
                "ref": "FAC-2026-001",
            }
        )
        wizard = self.env["wex.vendor.bill.ocr.review.wizard"].create(
            {
                "job_id": job.id,
                "supplier_id": self.vendor.id,
                "invoice_number": "FAC-2026-001",
                "invoice_date": "2026-08-08",
                "untaxed_amount": 100.0,
                "tax_amount": 21.0,
                "total_amount": 121.0,
            }
        )

        with self.assertRaises(UserError):
            job._check_apply_preconditions(wizard)

    def test_apply_preconditions_block_supplier_mismatch_detected_in_pdf(self):
        other_vendor = self.env["res.partner"].create(
            {
                "name": "Proveedor Extrano",
                "vat": "B87654321",
            }
        )
        job = self._create_job(
            state="review",
            parsed_supplier_name=other_vendor.name,
            parsed_supplier_vat=other_vendor.vat,
        )
        wizard = self.env["wex.vendor.bill.ocr.review.wizard"].create(
            {
                "job_id": job.id,
                "supplier_id": self.vendor.id,
                "invoice_number": "FAC-2026-002",
                "invoice_date": "2026-08-08",
                "untaxed_amount": 100.0,
                "tax_amount": 21.0,
                "total_amount": 121.0,
            }
        )

        with self.assertRaises(UserError):
            job._check_apply_preconditions(wizard)

    def test_review_wizard_rejects_duplicate_serials(self):
        serial_product = self.env["product.product"].create(
            {
                "name": "Producto Serie OCR",
                "type": "consu",
                "tracking": "serial",
                "purchase_ok": True,
            }
        )
        serial_purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": serial_product.display_name,
                            "product_id": serial_product.id,
                            "product_qty": 2.0,
                            "product_uom": serial_product.uom_po_id.id,
                            "price_unit": 10.0,
                            "date_planned": "2026-08-08 11:00:00",
                        },
                    )
                ],
            }
        )
        serial_purchase.button_confirm()
        move = serial_purchase.picking_ids.move_ids.filtered(
            lambda record: record.product_id == serial_product
        )[:1]
        wizard = self.env["wex.vendor.bill.ocr.review.wizard"].create(
            {
                "job_id": self._create_job(state="review").id,
                "supplier_id": self.vendor.id,
                "invoice_number": "FAC-2026-003",
                "invoice_date": "2026-08-08",
                "serial_line_ids": [
                    (
                        0,
                        0,
                        {
                            "move_id": move.id,
                            "product_id": serial_product.id,
                            "description": serial_product.display_name,
                            "qty_required": 2,
                            "serial_input": "SERIAL-01\nSERIAL-01",
                        },
                    )
                ],
            }
        )

        with self.assertRaises(ValidationError):
            wizard._check_serial_inputs()
