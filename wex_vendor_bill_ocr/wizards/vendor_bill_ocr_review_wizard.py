import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class WexVendorBillOcrReviewWizard(models.TransientModel):
    _name = "wex.vendor.bill.ocr.review.wizard"
    _description = "Review Vendor Bill OCR"

    job_id = fields.Many2one(
        "wex.vendor.bill.ocr.job",
        required=True,
        readonly=True,
    )
    purchase_order_id = fields.Many2one(
        "purchase.order",
        related="job_id.purchase_order_id",
        readonly=True,
    )
    supplier_id = fields.Many2one(
        "res.partner",
        required=True,
    )
    invoice_number = fields.Char(required=True)
    invoice_date = fields.Date(required=True)
    external_ref = fields.Char()
    untaxed_amount = fields.Monetary(currency_field="currency_id")
    tax_amount = fields.Monetary(currency_field="currency_id")
    total_amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        related="job_id.currency_id",
        readonly=True,
    )
    raw_text_preview = fields.Text(readonly=True)
    serial_line_ids = fields.One2many(
        "wex.vendor.bill.ocr.review.serial.line",
        "wizard_id",
        string="Serial Inputs",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        job = self.env["wex.vendor.bill.ocr.job"].browse(
            self.env.context.get("default_job_id")
        )
        if not job:
            return values
        values.update(
            {
                "job_id": job.id,
                "supplier_id": job.purchase_order_id.partner_id.id,
                "invoice_number": job.parsed_invoice_number,
                "invoice_date": job.parsed_invoice_date,
                "external_ref": job.parsed_external_ref,
                "untaxed_amount": job.parsed_untaxed_amount,
                "tax_amount": job.parsed_tax_amount,
                "total_amount": job.parsed_total_amount,
                "raw_text_preview": job.raw_text,
                "serial_line_ids": [
                    (
                        0,
                        0,
                        {
                            "move_id": requirement["move_id"],
                            "product_id": requirement["product_id"],
                            "description": requirement["description"],
                            "qty_required": requirement["qty_required"],
                        },
                    )
                    for requirement in job._get_pending_serial_requirements()
                ],
            }
        )
        return values

    def action_confirm(self):
        self.ensure_one()
        move = self.job_id.action_apply_review(self)
        return {
            "type": "ir.actions.act_window",
            "name": move.display_name,
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }

    def _split_serials(self, value):
        serials = [
            item.strip()
            for item in re.split(r"[\n,;]+", value or "")
            if item.strip()
        ]
        return serials

    def _get_serial_map(self):
        self.ensure_one()
        return {
            line.move_id.id: self._split_serials(line.serial_input)
            for line in self.serial_line_ids
            if line.move_id
        }

    def _check_serial_inputs(self):
        self.ensure_one()
        seen_pairs = set()
        lot_model = self.env["stock.lot"]
        for line in self.serial_line_ids:
            serials = self._split_serials(line.serial_input)
            if len(serials) != int(line.qty_required):
                raise ValidationError(
                    _("Serial count for %s must be exactly %s.")
                    % (line.product_id.display_name, int(line.qty_required))
                )
            if len(set(serials)) != len(serials):
                raise ValidationError(
                    _("Serials for %s contain duplicates.")
                    % line.product_id.display_name
                )
            for serial in serials:
                key = (line.product_id.id, serial.upper())
                if key in seen_pairs:
                    raise ValidationError(
                        _("The serial %s is repeated in the wizard.") % serial
                    )
                seen_pairs.add(key)
                existing_lot = lot_model.search(
                    [
                        ("product_id", "=", line.product_id.id),
                        ("company_id", "in", [False, self.purchase_order_id.company_id.id]),
                        ("name", "=", serial),
                    ],
                    limit=1,
                )
                if existing_lot:
                    raise ValidationError(
                        _("The serial %s already exists for product %s.")
                        % (serial, line.product_id.display_name)
                    )
        return True


class WexVendorBillOcrReviewSerialLine(models.TransientModel):
    _name = "wex.vendor.bill.ocr.review.serial.line"
    _description = "Vendor Bill OCR Review Serial Line"

    wizard_id = fields.Many2one(
        "wex.vendor.bill.ocr.review.wizard",
        required=True,
        ondelete="cascade",
    )
    move_id = fields.Many2one(
        "stock.move",
        required=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        "product.product",
        required=True,
        readonly=True,
    )
    description = fields.Char(readonly=True)
    qty_required = fields.Integer(required=True, readonly=True)
    serial_input = fields.Text(
        string="Serials",
        help="One serial per line. Commas and semicolons are also accepted.",
    )
