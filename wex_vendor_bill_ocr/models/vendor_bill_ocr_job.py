import base64
import io
import logging
import re
from datetime import datetime
from difflib import SequenceMatcher

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - depends on server setup
    try:
        from PyPDF2 import PdfReader
    except ImportError:  # pragma: no cover - depends on server setup
        PdfReader = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - depends on server setup
    pytesseract = None

try:
    from pdf2image import convert_from_bytes
except ImportError:  # pragma: no cover - depends on server setup
    convert_from_bytes = None


_logger = logging.getLogger(__name__)

STATE_SELECTION = [
    ("draft", "Draft"),
    ("processing", "Processing"),
    ("review", "Review"),
    ("done", "Done"),
    ("error", "Error"),
]

METHOD_SELECTION = [
    ("pdf_text", "PDF Text"),
    ("ocr", "OCR"),
]


class WexVendorBillOcrJob(models.Model):
    _name = "wex.vendor.bill.ocr.job"
    _description = "Vendor Bill OCR Job"
    _order = "create_date desc, id desc"

    name = fields.Char(
        default=lambda self: self.env["ir.sequence"].next_by_code(
            "wex.vendor.bill.ocr.job"
        )
        or _("New"),
        readonly=True,
        copy=False,
    )
    purchase_order_id = fields.Many2one(
        "purchase.order",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        related="purchase_order_id.company_id",
        store=True,
        readonly=True,
    )
    attachment_id = fields.Many2one(
        "ir.attachment",
        string="PDF Attachment",
        required=True,
        ondelete="restrict",
    )
    attachment_name = fields.Char(related="attachment_id.name", readonly=True)
    state = fields.Selection(
        selection=STATE_SELECTION,
        default="draft",
        required=True,
        index=True,
    )
    method_used = fields.Selection(selection=METHOD_SELECTION, readonly=True)
    raw_text = fields.Text(readonly=True)
    parsed_supplier_name = fields.Char(readonly=True)
    parsed_supplier_vat = fields.Char(readonly=True)
    parsed_invoice_number = fields.Char(readonly=True)
    parsed_invoice_date = fields.Date(readonly=True)
    parsed_external_ref = fields.Char(readonly=True)
    parsed_untaxed_amount = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
    )
    parsed_tax_amount = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
    )
    parsed_total_amount = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
    )
    confidence_score = fields.Float(readonly=True)
    result_move_id = fields.Many2one(
        "account.move",
        string="Vendor Bill",
        readonly=True,
        ondelete="set null",
    )
    error_message = fields.Text(readonly=True)
    currency_id = fields.Many2one(
        "res.currency",
        related="purchase_order_id.currency_id",
        readonly=True,
    )
    queued_at = fields.Datetime(readonly=True)
    started_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(readonly=True)
    progress_percent = fields.Integer(default=0, readonly=True)
    progress_message = fields.Char(readonly=True)
    needs_serials = fields.Boolean(
        compute="_compute_flags",
        string="Needs Serials",
    )
    is_ready_to_apply = fields.Boolean(
        compute="_compute_flags",
        string="Ready To Apply",
    )
    has_pending_receipt = fields.Boolean(
        compute="_compute_flags",
        string="Has Pending Receipt",
    )
    has_vendor_bill = fields.Boolean(
        compute="_compute_flags",
        string="Has Vendor Bill",
    )

    @api.depends("purchase_order_id", "state", "result_move_id")
    def _compute_flags(self):
        for job in self:
            pending_serials = bool(job._get_pending_serial_requirements())
            job.needs_serials = pending_serials
            job.has_pending_receipt = bool(job._get_pending_incoming_pickings())
            job.has_vendor_bill = bool(job._get_existing_vendor_bills())
            job.is_ready_to_apply = (
                job.state == "review"
                and not job.result_move_id
                and not job.has_vendor_bill
            )

    def action_open_review_wizard(self):
        self.ensure_one()
        if self.state != "review":
            raise UserError(
                _("The job is not ready for review yet.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": "Review OCR Result",
            "res_model": "wex.vendor.bill.ocr.review.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_job_id": self.id,
            },
        }

    def action_refresh_view(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_requeue(self):
        for job in self:
            if job.state not in ("error", "draft"):
                raise UserError(_("Only draft or error jobs can be requeued."))
            job.write(
                {
                    "state": "draft",
                    "error_message": False,
                    "queued_at": fields.Datetime.now(),
                    "started_at": False,
                    "finished_at": False,
                    "progress_percent": 0,
                    "progress_message": _("Queued"),
                }
            )
        return True

    @api.model
    def _cron_process_queue(self):
        job = self._claim_next_job_for_processing()
        if job:
            job._process_job()
        return True

    @api.model
    def _claim_next_job_for_processing(self):
        self.env.cr.execute(
            """
                SELECT id
                  FROM wex_vendor_bill_ocr_job
                 WHERE state = 'draft'
                 ORDER BY queued_at NULLS FIRST, id
                 LIMIT 1
                 FOR UPDATE SKIP LOCKED
            """
        )
        row = self.env.cr.fetchone()
        if not row:
            return self.browse()
        job = self.browse(row[0])
        job.write(
            {
                "state": "processing",
                "started_at": fields.Datetime.now(),
                "progress_percent": 10,
                "progress_message": _("Attachment stored"),
                "error_message": False,
            }
        )
        self.env.cr.commit()
        return job

    def _process_job(self):
        self.ensure_one()
        try:
            self._check_processing_preconditions()
            self._set_progress(30, _("Extracting PDF text"))
            raw_text, method = self._extract_text()
            self._set_progress(90, _("Parsing invoice data"))
            parsed_vals = self._parse_extracted_text(raw_text)
            self.write(
                {
                    "state": "review",
                    "method_used": method,
                    "raw_text": raw_text,
                    "finished_at": fields.Datetime.now(),
                    "progress_percent": 100,
                    "progress_message": _("Ready for review"),
                    **parsed_vals,
                }
            )
            self.env.cr.commit()
        except Exception as exc:  # pragma: no cover - defensive flow
            _logger.exception("Vendor bill OCR processing failed for job %s", self.id)
            self.write(
                {
                    "state": "error",
                    "error_message": str(exc),
                    "finished_at": fields.Datetime.now(),
                    "progress_message": _("Processing failed"),
                }
            )
            self.env.cr.commit()

    def _check_processing_preconditions(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_("A PDF attachment is required."))
        if self.purchase_order_id.state not in ("purchase", "done"):
            raise UserError(
                _("The purchase order must be confirmed before processing the vendor bill.")
            )
        if self.attachment_id.mimetype and self.attachment_id.mimetype != "application/pdf":
            raise UserError(_("Only PDF files are supported in phase 1."))

    def _set_progress(self, percent, message):
        self.write(
            {
                "progress_percent": percent,
                "progress_message": message,
            }
        )
        self.env.cr.commit()

    def _extract_text(self):
        try:
            pdf_text = self._extract_pdf_text()
        except Exception as exc:  # pragma: no cover - graceful fallback
            _logger.info("Direct PDF text extraction failed for job %s: %s", self.id, exc)
            pdf_text = ""
        if self._is_text_useful(pdf_text):
            return pdf_text, "pdf_text"
        self._set_progress(70, _("Running OCR fallback"))
        ocr_text = self._extract_ocr_text()
        if self._is_text_useful(ocr_text):
            return ocr_text, "ocr"
        raise UserError(_("No useful text could be extracted from the PDF."))

    def _extract_pdf_text(self):
        if not PdfReader:
            raise UserError(
                _(
                    "Missing PDF extraction dependency. Install pypdf or PyPDF2 on the Odoo server."
                )
            )
        reader = PdfReader(io.BytesIO(self._get_attachment_bytes()))
        chunks = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks).strip()

    def _extract_ocr_text(self):
        if not pytesseract or not convert_from_bytes:
            raise UserError(
                _(
                    "Missing OCR dependencies: pytesseract and pdf2image are required on the Odoo server."
                )
            )
        images = convert_from_bytes(self._get_attachment_bytes(), dpi=200)
        chunks = []
        for image in images:
            chunks.append(pytesseract.image_to_string(image) or "")
        return "\n".join(chunks).strip()

    def _get_attachment_bytes(self):
        self.ensure_one()
        datas = self.attachment_id.datas
        if not datas:
            raise UserError(_("The selected attachment has no binary content."))
        if isinstance(datas, str):
            datas = datas.encode()
        return base64.b64decode(datas)

    def _is_text_useful(self, text):
        normalized = re.sub(r"\s+", " ", text or "").strip()
        alpha_count = len(re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", normalized))
        return len(normalized) >= 40 and alpha_count >= 20

    def _parse_extracted_text(self, raw_text):
        partner = self.purchase_order_id.partner_id.commercial_partner_id
        parsed_vals = {
            "parsed_supplier_name": self._guess_supplier_name(raw_text),
            "parsed_supplier_vat": self._find_supplier_vat(raw_text),
            "parsed_invoice_number": self._find_invoice_number(raw_text),
            "parsed_invoice_date": self._find_invoice_date(raw_text),
            "parsed_external_ref": self._find_external_ref(raw_text),
            "parsed_untaxed_amount": self._find_amount(
                raw_text,
                [
                    "total base imponible",
                    "base imponible total",
                    "base imponible",
                    "subtotal",
                ],
            ),
            "parsed_tax_amount": self._find_amount(
                raw_text,
                [
                    "total iva",
                    "importe iva",
                    "iva total",
                    "iva",
                    "impuesto",
                    "tax",
                ],
            ),
            "parsed_total_amount": self._find_amount(
                raw_text,
                [
                    "total factura",
                    "importe total",
                    "total a pagar",
                    "total eur",
                    "total",
                ],
            ),
        }
        parsed_vals = self._resolve_with_purchase_context(parsed_vals, raw_text)
        match_count = sum(
            bool(value)
            for value in [
                parsed_vals["parsed_supplier_name"],
                parsed_vals["parsed_supplier_vat"],
                parsed_vals["parsed_invoice_number"],
                parsed_vals["parsed_invoice_date"],
                parsed_vals["parsed_untaxed_amount"],
                parsed_vals["parsed_tax_amount"],
                parsed_vals["parsed_total_amount"],
            ]
        )
        confidence = round((match_count / 7.0) * 100.0, 2)
        if self._text_contains_partner(raw_text, partner):
            confidence = min(100.0, confidence + 10.0)
        parsed_vals["confidence_score"] = confidence
        return parsed_vals

    def _resolve_with_purchase_context(self, parsed_vals, raw_text):
        resolved = dict(parsed_vals)
        purchase = self.purchase_order_id
        partner = purchase.partner_id.commercial_partner_id
        expected_amounts = self._get_purchase_expected_amounts()
        all_amounts = self._extract_amount_candidates(raw_text)

        resolved["parsed_supplier_name"] = partner.name or resolved["parsed_supplier_name"]
        resolved["parsed_supplier_vat"] = partner.vat or resolved["parsed_supplier_vat"]

        resolved["parsed_external_ref"] = self._resolve_external_ref_with_purchase_context(
            resolved["parsed_external_ref"],
            raw_text,
        )
        resolved["parsed_untaxed_amount"] = self._resolve_amount_with_purchase_context(
            raw_text,
            resolved["parsed_untaxed_amount"],
            expected_amounts["untaxed"],
            all_amounts,
            prefer_labels=[
                "total base imponible",
                "base imponible total",
                "base imponible",
                "subtotal",
            ],
        )
        resolved["parsed_tax_amount"] = self._resolve_amount_with_purchase_context(
            raw_text,
            resolved["parsed_tax_amount"],
            expected_amounts["tax"],
            all_amounts,
            prefer_labels=[
                "total iva",
                "importe iva",
                "iva total",
                "iva",
                "impuesto",
                "tax",
            ],
        )
        resolved["parsed_total_amount"] = self._resolve_amount_with_purchase_context(
            raw_text,
            resolved["parsed_total_amount"],
            expected_amounts["total"],
            all_amounts,
            prefer_labels=[
                "total factura",
                "importe total",
                "total a pagar",
                "total factura euros",
                "total eur",
                "total",
            ],
        )
        resolved = self._normalize_resolved_amounts(resolved, expected_amounts, all_amounts)
        return resolved

    def _get_purchase_expected_amounts(self):
        purchase = self.purchase_order_id
        return {
            "untaxed": purchase.amount_untaxed,
            "tax": purchase.amount_tax,
            "total": purchase.amount_total,
        }

    def _resolve_external_ref_with_purchase_context(self, parsed_value, raw_text):
        candidates = []
        purchase = self.purchase_order_id
        for value in [
            parsed_value,
            purchase.partner_ref,
            purchase.origin,
            purchase.name,
        ]:
            if value:
                candidates.append(str(value).strip())
        normalized_text = self._normalize_text(raw_text)
        for candidate in candidates:
            normalized_candidate = self._normalize_text(candidate)
            if normalized_candidate and normalized_candidate in normalized_text:
                return candidate
        return parsed_value

    def _resolve_amount_with_purchase_context(
        self,
        raw_text,
        parsed_value,
        expected_value,
        all_amounts,
        prefer_labels=None,
    ):
        candidates = []
        if parsed_value not in (False, None):
            candidates.append(parsed_value)
        for label in prefer_labels or []:
            amount = self._find_amount(raw_text, [label])
            if amount not in (False, None):
                candidates.append(amount)
        for amount in all_amounts:
            if amount not in candidates:
                candidates.append(amount)
        if not candidates:
            return parsed_value
        return self._pick_best_amount_candidate(candidates, expected_value)

    def _pick_best_amount_candidate(self, candidates, expected_value):
        cleaned = []
        for candidate in candidates:
            if candidate in (False, None):
                continue
            if candidate < 0:
                continue
            if candidate not in cleaned:
                cleaned.append(candidate)
        if not cleaned:
            return False
        if expected_value in (False, None):
            return cleaned[0]
        tolerance = max(abs(expected_value) * 0.20, 5.0)
        matching = [
            amount for amount in cleaned if abs(amount - expected_value) <= tolerance
        ]
        if matching:
            return min(matching, key=lambda amount: abs(amount - expected_value))
        return min(cleaned, key=lambda amount: abs(amount - expected_value))

    def _normalize_resolved_amounts(self, resolved, expected_amounts, all_amounts):
        untaxed = resolved.get("parsed_untaxed_amount")
        tax = resolved.get("parsed_tax_amount")
        total = resolved.get("parsed_total_amount")

        if (
            untaxed not in (False, None)
            and tax not in (False, None)
            and total not in (False, None)
            and abs((untaxed + tax) - total) <= 0.05
        ):
            return resolved

        expected_total = expected_amounts["total"]
        expected_untaxed = expected_amounts["untaxed"]
        expected_tax = expected_amounts["tax"]

        if total in (False, None) or (
            expected_total not in (False, None)
            and abs(total - expected_total) > max(abs(expected_total) * 0.20, 5.0)
        ):
            resolved["parsed_total_amount"] = self._pick_best_amount_candidate(
                all_amounts,
                expected_total,
            )
            total = resolved["parsed_total_amount"]

        if untaxed in (False, None) or (
            expected_untaxed not in (False, None)
            and abs(untaxed - expected_untaxed) > max(abs(expected_untaxed) * 0.20, 5.0)
        ):
            resolved["parsed_untaxed_amount"] = self._pick_best_amount_candidate(
                all_amounts,
                expected_untaxed,
            )
            untaxed = resolved["parsed_untaxed_amount"]

        if tax in (False, None) or (
            expected_tax not in (False, None)
            and abs(tax - expected_tax) > max(abs(expected_tax) * 0.20, 5.0)
        ):
            resolved["parsed_tax_amount"] = self._pick_best_amount_candidate(
                all_amounts,
                expected_tax,
            )
            tax = resolved["parsed_tax_amount"]

        if untaxed not in (False, None) and total not in (False, None):
            computed_tax = round(total - untaxed, 2)
            if computed_tax >= 0 and (
                tax in (False, None) or abs(computed_tax - tax) > 0.05
            ):
                resolved["parsed_tax_amount"] = computed_tax

        if untaxed not in (False, None) and tax not in (False, None):
            computed_total = round(untaxed + tax, 2)
            if total in (False, None) or abs(computed_total - total) > 0.05:
                if expected_total not in (False, None) and abs(computed_total - expected_total) <= max(abs(expected_total) * 0.20, 5.0):
                    resolved["parsed_total_amount"] = computed_total

        return resolved

    def _guess_supplier_name(self, raw_text):
        lines = [
            line.strip()
            for line in (raw_text or "").splitlines()
            if len(line.strip()) >= 5
        ]
        for line in lines[:8]:
            if any(char.isalpha() for char in line) and len(line.split()) <= 8:
                return line[:128]
        return False

    def _find_supplier_vat(self, raw_text):
        matches = re.findall(
            r"\b([A-Z]\d{7,8}[A-Z0-9]|\d{8}[A-Z]|[A-Z]{2}\d{8,12})\b",
            raw_text or "",
            flags=re.IGNORECASE,
        )
        return matches[0].upper() if matches else False

    def _find_invoice_number(self, raw_text):
        labels = [
            "factura",
            "invoice number",
            "invoice no",
            "invoice",
            "número factura",
            "numero factura",
            "ref factura",
            "referencia factura",
        ]
        for line in self._get_text_lines(raw_text):
            lowered = line.lower()
            if not any(label in lowered for label in labels):
                continue
            if "total factura" in lowered or "importe total" in lowered:
                continue
            token = self._extract_invoice_number_from_line(line)
            if token:
                return token
        patterns = [
            r"(?:^|\n)\s*(?:invoice|factura)\s*(?:number|no|n[oº]|num|n[uú]mero)?\s*[:#-]?\s*([A-Z0-9\/\.-]{3,40})",
            r"(?:^|\n)\s*(?:n[uú]mero factura|ref(?:erencia)? factura)\s*[:#-]?\s*([A-Z0-9\/\.-]{3,40})",
        ]
        candidate = self._find_first_regex_group(raw_text, patterns)
        return candidate if candidate and not self._looks_like_amount_token(candidate) else False

    def _find_external_ref(self, raw_text):
        patterns = [
            r"(?:^|\n)\s*(?:n[ºo°]?\s*pedido|pedido|order|po)\s*(?:number|no|n[oº])?\s*[:#-]?\s*([A-Z0-9\/\.-]{4,40})",
            r"(?:^|\n)\s*(?:su pedido n[ºo°]?|your order no)\s*[:#-]?\s*([A-Z0-9\/\.-]{4,40})",
            r"(?:^|\n)\s*(?:albar[aá]n|delivery note)\s*[:#-]?\s*([A-Z0-9\/\.-]{4,40})",
        ]
        candidate = self._find_first_regex_group(raw_text, patterns)
        if not candidate:
            return False
        candidate = candidate.strip().upper()
        if self._looks_like_amount_token(candidate):
            return False
        if len(candidate) < 5:
            return False
        if not re.search(r"\d", candidate):
            return False
        return candidate

    def _find_invoice_date(self, raw_text):
        patterns = [
            r"(?:fecha|date|invoice date)\s*[:#-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"(?:fecha|date|invoice date)\s*[:#-]?\s*(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",
        ]
        value = self._find_first_regex_group(raw_text, patterns)
        return self._parse_date(value) if value else False

    def _find_first_regex_group(self, raw_text, patterns):
        text = raw_text or ""
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return False

    def _find_amount(self, raw_text, labels):
        for line in self._get_text_lines(raw_text):
            lowered = line.lower()
            if not any(label in lowered for label in labels):
                continue
            amounts = self._extract_amount_candidates_from_line(line, labels)
            if amounts:
                return amounts[0]
        text = raw_text or ""
        for label in labels:
            match = re.search(
                rf"{re.escape(label)}\s*[:#-]?\s*([-+]?\d[\d\.\,\s]{{0,20}})",
                text,
                flags=re.IGNORECASE,
            )
            if match:
                amount = self._parse_amount(match.group(1))
                if amount is not False:
                    return amount
        return False

    def _get_text_lines(self, raw_text):
        return [
            line.strip()
            for line in (raw_text or "").splitlines()
            if line and line.strip()
        ]

    def _extract_invoice_number_from_line(self, line):
        match = re.search(
            r"(?:invoice|factura|n[uú]mero factura|numero factura|ref(?:erencia)? factura)"
            r"\s*(?:number|no|n[oº]|num|n[uú]mero)?\s*[:#-]?\s*([A-Z0-9\/\.-]{3,40})",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            return False
        candidate = match.group(1).strip(" .:-")
        if self._looks_like_amount_token(candidate):
            return False
        return candidate

    def _looks_like_amount_token(self, value):
        token = (value or "").strip()
        if not token:
            return False
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})", token):
            return True
        if re.fullmatch(r"\d+[.,]\d{2}", token):
            return True
        return False

    def _extract_amount_candidates(self, text):
        matches = re.finditer(
            r"[-+]?\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d{2})|[-+]?\d+[.,]\d{2}|[-+]?\d+",
            text or "",
        )
        amounts = []
        for match in matches:
            end = match.end()
            if end < len(text) and text[end] == "%":
                continue
            amount = self._parse_amount(match.group(0))
            if amount is not False:
                amounts.append(amount)
        return amounts

    def _extract_amount_candidates_from_line(self, line, labels):
        lower_line = (line or "").lower()
        label_positions = [
            lower_line.find(label)
            for label in labels
            if label in lower_line
        ]
        if not label_positions:
            return self._extract_amount_candidates(line)
        start_index = min(label_positions)
        scoped_line = line[start_index:]
        return self._extract_amount_candidates(scoped_line)

    def _parse_amount(self, value):
        cleaned = (value or "").strip().replace(" ", "")
        if not cleaned:
            return False
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif cleaned.count(",") == 1:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return False

    def _parse_date(self, value):
        if not value:
            return False
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d", "%d/%m/%y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return False

    def _text_contains_partner(self, raw_text, partner):
        normalized_text = self._normalize_text(raw_text)
        partner_name = self._normalize_text(partner.name)
        partner_vat = self._normalize_vat(partner.vat)
        return bool(
            (partner_name and partner_name in normalized_text)
            or (partner_vat and partner_vat in normalized_text)
        )

    def _normalize_text(self, value):
        return re.sub(r"[^a-z0-9]", "", (value or "").lower())

    def _normalize_vat(self, value):
        return re.sub(r"[^A-Z0-9]", "", (value or "").upper())

    def _get_existing_vendor_bills(self):
        self.ensure_one()
        return self.purchase_order_id.invoice_ids.filtered(
            lambda move: move.move_type == "in_invoice" and move.state != "cancel"
        )

    def _get_pending_incoming_pickings(self):
        self.ensure_one()
        return self.purchase_order_id.picking_ids.filtered(
            lambda picking: picking.state not in ("done", "cancel")
            and picking.picking_type_code == "incoming"
        )

    def _get_pending_serial_requirements(self):
        self.ensure_one()
        requirements = []
        for picking in self._get_pending_incoming_pickings():
            for move in picking.move_ids.filtered(
                lambda move: move.product_id.tracking == "serial"
            ):
                required_qty = int(round(move.product_qty))
                if required_qty <= 0:
                    continue
                requirements.append(
                    {
                        "picking_id": picking.id,
                        "move_id": move.id,
                        "product_id": move.product_id.id,
                        "description": move.description_picking or move.product_id.display_name,
                        "qty_required": required_qty,
                    }
                )
        return requirements

    def action_apply_review(self, wizard):
        self.ensure_one()
        self._check_apply_preconditions(wizard)
        self._apply_receipt(wizard)
        move = self._create_vendor_bill_from_purchase(wizard)
        self._attach_pdf_to_move(move)
        self.write(
            {
                "state": "done",
                "result_move_id": move.id,
                "finished_at": fields.Datetime.now(),
                "progress_percent": 100,
                "progress_message": _("Vendor bill created"),
                "error_message": False,
            }
        )
        return move

    def _check_apply_preconditions(self, wizard):
        self.ensure_one()
        purchase = self.purchase_order_id
        if self.state != "review":
            raise UserError(_("Only jobs in review can be applied."))
        if self.result_move_id:
            raise UserError(_("This OCR job already created a vendor bill."))
        if purchase.state not in ("purchase", "done"):
            raise UserError(_("The purchase order is not ready for reception."))
        if not wizard.invoice_number:
            raise UserError(_("Invoice number is required."))
        if not wizard.invoice_date:
            raise UserError(_("Invoice date is required."))
        if wizard.supplier_id.commercial_partner_id != purchase.partner_id.commercial_partner_id:
            raise UserError(
                _("The supplier must match the supplier of the purchase order.")
            )
        if self._get_existing_vendor_bills():
            raise UserError(
                _("This purchase order already has a non-cancelled vendor bill.")
            )
        duplicate = self.env["account.move"].search(
            [
                ("move_type", "=", "in_invoice"),
                ("company_id", "=", purchase.company_id.id),
                ("partner_id", "child_of", purchase.partner_id.commercial_partner_id.id),
                ("ref", "=", wizard.invoice_number.strip()),
                ("state", "!=", "cancel"),
            ],
            limit=1,
        )
        if duplicate:
            raise UserError(
                _("A vendor bill with the same invoice number already exists for this supplier.")
            )
        self._check_amounts(wizard)
        self._check_supplier_match(wizard)
        wizard._check_serial_inputs()

    def _check_amounts(self, wizard):
        values = [
            wizard.untaxed_amount,
            wizard.tax_amount,
            wizard.total_amount,
        ]
        if any(amount is not False and amount < 0 for amount in values if amount is not None):
            raise UserError(_("Invoice amounts cannot be negative."))
        if (
            wizard.untaxed_amount is not None
            and wizard.tax_amount is not None
            and wizard.total_amount is not None
        ):
            expected_total = wizard.untaxed_amount + wizard.tax_amount
            if abs(expected_total - wizard.total_amount) > 0.05:
                raise UserError(
                    _("The total amount does not match untaxed amount plus taxes.")
                )

    def _check_supplier_match(self, wizard):
        partner = self.purchase_order_id.partner_id.commercial_partner_id
        if self.parsed_supplier_vat:
            parsed_vat = self._normalize_vat(self.parsed_supplier_vat)
            partner_vat = self._normalize_vat(partner.vat)
            if partner_vat and parsed_vat and parsed_vat != partner_vat:
                raise UserError(
                    _("The VAT detected in the PDF does not match the purchase order supplier.")
                )
        if self.parsed_supplier_name and self.parsed_supplier_vat:
            score = SequenceMatcher(
                None,
                self._normalize_text(self.parsed_supplier_name),
                self._normalize_text(partner.name),
            ).ratio()
            if score < 0.30:
                raise UserError(
                    _("The supplier detected in the PDF does not match the purchase order supplier.")
                )

    def _apply_receipt(self, wizard):
        pickings = self._get_pending_incoming_pickings()
        if not pickings:
            raise UserError(_("There are no pending incoming receipts for this purchase order."))
        serial_map = wizard._get_serial_map()
        for picking in pickings:
            for move in picking.move_ids.filtered(lambda move: move.state not in ("done", "cancel")):
                move.quantity = move.product_qty
                if move.product_id.tracking == "serial":
                    serials = serial_map.get(move.id, [])
                    if len(serials) != int(round(move.product_qty)):
                        raise UserError(
                            _("Serial count does not match required quantity for %s.")
                            % move.product_id.display_name
                        )
                    move.move_line_ids.unlink()
                    move.move_line_ids = [
                        Command.create(
                            {
                                "product_id": move.product_id.id,
                                "lot_name": serial,
                                "quantity": 1.0,
                                "picked": True,
                            }
                        )
                        for serial in serials
                    ]
                else:
                    continue
            self._validate_picking(picking)

    def _validate_picking(self, picking):
        result = picking.with_context(
            button_validate_picking_ids=picking.ids
        ).button_validate()
        if isinstance(result, dict):
            res_model = result.get("res_model")
            res_id = result.get("res_id")
            if res_model == "stock.immediate.transfer":
                self.env[res_model].browse(res_id).process()
            elif res_model == "stock.backorder.confirmation":
                self.env[res_model].browse(res_id).process()
        return True

    def _create_vendor_bill_from_purchase(self, wizard):
        purchase = self.purchase_order_id
        existing_ids = set(purchase.invoice_ids.ids)
        purchase.action_create_invoice()
        new_move = (purchase.invoice_ids - self.env["account.move"].browse(list(existing_ids))).filtered(
            lambda move: move.move_type == "in_invoice"
        )[:1]
        if not new_move:
            raise UserError(_("Odoo did not create a new vendor bill from this purchase order."))
        vals = {
            "invoice_date": wizard.invoice_date,
            "ref": wizard.invoice_number.strip(),
        }
        if wizard.external_ref and "payment_reference" in new_move._fields:
            vals["payment_reference"] = wizard.external_ref.strip()
        new_move.write(vals)
        return new_move

    def _attach_pdf_to_move(self, move):
        self.ensure_one()
        self.attachment_id.copy(
            {
                "res_model": "account.move",
                "res_id": move.id,
            }
        )
