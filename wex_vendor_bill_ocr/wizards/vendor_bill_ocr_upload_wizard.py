from odoo import _, fields, models
from odoo.exceptions import UserError


class WexVendorBillOcrUploadWizard(models.TransientModel):
    _name = "wex.vendor.bill.ocr.upload.wizard"
    _description = "Upload Vendor Bill OCR PDF"

    purchase_order_id = fields.Many2one(
        "purchase.order",
        required=True,
        readonly=True,
    )
    pdf_file = fields.Binary(required=True, attachment=False)
    filename = fields.Char(required=True)

    def action_upload_and_enqueue(self):
        self.ensure_one()
        if not self.pdf_file:
            raise UserError(_("A PDF file is required."))
        if not (self.filename or "").lower().endswith(".pdf"):
            raise UserError(_("Only PDF files are supported in phase 1."))
        if self.purchase_order_id.state not in ("purchase", "done"):
            raise UserError(
                _("The purchase order must be confirmed before processing the vendor bill.")
            )
        attachment = self.env["ir.attachment"].create(
            {
                "name": self.filename,
                "type": "binary",
                "datas": self.pdf_file,
                "mimetype": "application/pdf",
                "res_model": "purchase.order",
                "res_id": self.purchase_order_id.id,
            }
        )
        job = self.env["wex.vendor.bill.ocr.job"].create(
            {
                "purchase_order_id": self.purchase_order_id.id,
                "attachment_id": attachment.id,
                "queued_at": fields.Datetime.now(),
                "progress_message": _("Queued"),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": job.name,
            "res_model": "wex.vendor.bill.ocr.job",
            "res_id": job.id,
            "view_mode": "form",
            "target": "current",
        }
