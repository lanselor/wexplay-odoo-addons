# -*- coding: utf-8 -*-

import base64
import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class WexConsentDocument(models.Model):
    _name = "wex.consent.document"
    _description = "Documento de consentimiento"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    repair_order_id = fields.Many2one(
        comodel_name="repair.order",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    company_id = fields.Many2one(
        related="repair_order_id.company_id",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        related="repair_order_id.partner_id",
        store=True,
        readonly=True,
    )
    partner_vat = fields.Char(
        related="partner_id.vat",
        store=True,
        readonly=True,
    )
    document_type = fields.Selection(
        [
            ("reception", "Recepción"),
            ("delivery", "Entrega"),
        ],
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("pending_signature", "Pendiente de firma"),
            ("signed", "Firmado"),
            ("cancelled", "Cancelado"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    request_ids = fields.One2many(
        comodel_name="wex.consent.request",
        inverse_name="document_id",
        string="Solicitudes",
    )
    active_request_id = fields.Many2one(
        comodel_name="wex.consent.request",
        compute="_compute_active_request_id",
        store=False,
    )
    request_count = fields.Integer(compute="_compute_request_count", store=False)
    signed_at = fields.Datetime(readonly=True, tracking=True)
    signer_name = fields.Char(readonly=True, tracking=True)
    signer_vat = fields.Char(readonly=True, tracking=True)
    signature_image = fields.Image(copy=False)
    confirmation_ok = fields.Boolean(
        string="Confirmado por el cliente",
        copy=False,
    )
    pdf_filename = fields.Char(readonly=True, copy=False)
    pdf_file = fields.Binary(readonly=True, attachment=True, copy=False)
    dms_file_id = fields.Many2one(
        comodel_name="dms.file",
        string="Archivo DMS",
        readonly=True,
        copy=False,
    )
    dms_directory_id = fields.Many2one(
        comodel_name="dms.directory",
        string="Directorio DMS",
        readonly=True,
        copy=False,
    )
    snapshot_json = fields.Text(copy=False)
    snapshot_text = fields.Text(
        compute="_compute_snapshot_text",
        store=False,
    )
    legal_text = fields.Text()
    legal_data_protection = fields.Boolean(default=True)
    allow_email_non_commercial = fields.Boolean()
    allow_email_commercial = fields.Boolean()
    allow_whatsapp_non_commercial = fields.Boolean()
    allow_whatsapp_commercial = fields.Boolean()
    warranty_conditions_accepted = fields.Boolean()
    issue_description = fields.Text()
    device_description = fields.Text()
    repair_notes = fields.Text()
    customer_review_statement = fields.Text(
        default="He revisado el dispositivo y todo está bien.",
    )

    _sql_constraints = [
        (
            "wex_consent_document_unique_type_per_repair",
            "unique(repair_order_id, document_type)",
            "Solo puede existir un documento activo por tipo y reparación.",
        ),
    ]

    @api.model
    def _check_kiosk_access(self):
        if not (
            self.env.user.has_group("wex_consent.group_wex_consent_kiosk")
            or self.env.user.has_group("wex_consent.group_wex_consent_manager")
        ):
            raise AccessError(_("No tienes permisos para operar el modo kiosko."))

    @api.model
    def _validate_signature_image(self, signature_image):
        if not signature_image:
            raise UserError(_("La firma está vacía."))
        try:
            signature_binary = base64.b64decode(signature_image, validate=True)
        except Exception as error:
            raise UserError(_("El formato de la firma no es válido.")) from error
        if len(signature_binary) > 2 * 1024 * 1024:
            raise UserError(_("La firma es demasiado grande."))
        return signature_image

    @api.model
    def _get_default_reception_legal_text(self):
        return (
            self.env["ir.config_parameter"].sudo().get_param(
                "wex_consent.reception_legal_text"
            )
            or (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
                "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
                "nisi ut aliquip ex ea commodo consequat."
            )
        )

    @api.depends("request_ids.state")
    def _compute_active_request_id(self):
        for rec in self:
            rec.active_request_id = rec.request_ids.filtered(
                lambda request: request.state in ("queued", "presented")
            )[:1]

    @api.depends("request_ids")
    def _compute_request_count(self):
        for rec in self:
            rec.request_count = len(rec.request_ids)

    @api.depends("snapshot_json")
    def _compute_snapshot_text(self):
        for rec in self:
            if not rec.snapshot_json:
                rec.snapshot_text = False
                continue
            try:
                payload = json.loads(rec.snapshot_json)
            except json.JSONDecodeError:
                rec.snapshot_text = rec.snapshot_json
                continue
            lines = []
            for key, value in payload.items():
                if value in (False, None, ""):
                    continue
                lines.append(f"{key}: {value}")
            rec.snapshot_text = "\n".join(lines)

    @api.model
    def _get_document_type_label(self, document_type):
        return dict(self._fields["document_type"].selection).get(
            document_type, document_type
        )

    @api.model
    def _build_document_name(self, repair, document_type):
        return "%s - %s" % (
            repair.name or _("Reparación"),
            self._get_document_type_label(document_type),
        )

    @api.model
    def _prepare_reception_snapshot(self, repair):
        return {
            "repair_name": repair.name,
            "customer_name": repair.partner_id.name,
            "customer_vat": repair.partner_id.vat,
            "device_description": repair.x_device_description,
            "issue_description": repair.x_reported_issue,
            "product_name": repair.product_id.display_name,
            "serial_number": repair.x_imei,
            "accessories": repair.x_accessories,
        }

    @api.model
    def _prepare_delivery_snapshot(self, repair):
        return {
            "repair_name": repair.name,
            "customer_name": repair.partner_id.name,
            "customer_vat": repair.partner_id.vat,
            "device_description": repair.x_device_description,
            "issue_description": repair.x_reported_issue,
            "repair_notes": repair.internal_notes or repair.x_internal_notes,
            "product_name": repair.product_id.display_name,
            "serial_number": repair.x_imei,
        }

    def _build_snapshot_for_document(self):
        self.ensure_one()
        repair = self.repair_order_id
        if self.document_type == "reception":
            return self._prepare_reception_snapshot(repair)
        return self._prepare_delivery_snapshot(repair)

    def action_refresh_from_repair(self):
        for rec in self:
            if rec.state == "signed":
                continue
            snapshot = rec._build_snapshot_for_document()
            values = {
                "snapshot_json": json.dumps(snapshot, ensure_ascii=True, indent=2),
                "issue_description": snapshot.get("issue_description"),
                "device_description": snapshot.get("device_description"),
                "repair_notes": snapshot.get("repair_notes"),
                "signer_name": rec.signer_name or rec.partner_id.name,
                "signer_vat": rec.signer_vat or rec.partner_vat,
            }
            if rec.document_type == "reception":
                if rec.state == "draft" and not rec.request_ids:
                    values.update(
                        {
                            "allow_email_non_commercial": True,
                            "allow_email_commercial": True,
                            "allow_whatsapp_non_commercial": True,
                            "allow_whatsapp_commercial": True,
                            "warranty_conditions_accepted": True,
                        }
                    )
                values["legal_text"] = rec.legal_text or rec._get_default_reception_legal_text()
            rec.write(values)
        return True

    def _message_repair_order(self, body):
        self.ensure_one()
        self.message_post(body=body)
        if hasattr(self.repair_order_id, "message_post"):
            self.repair_order_id.message_post(body=body)
        return True

    @api.model
    def get_or_create_from_repair(self, repair, document_type):
        document = self.search(
            [
                ("repair_order_id", "=", repair.id),
                ("document_type", "=", document_type),
            ],
            limit=1,
        )
        if not document:
            document = self.create(
                {
                    "name": self._build_document_name(repair, document_type),
                    "repair_order_id": repair.id,
                    "document_type": document_type,
                }
            )
        document.action_refresh_from_repair()
        return document

    def _get_report_xmlid(self):
        self.ensure_one()
        mapping = {
            "reception": "wex_consent.action_report_wex_consent_reception",
            "delivery": "wex_consent.action_report_wex_consent_delivery",
        }
        return mapping[self.document_type]

    def _get_signed_filename(self):
        self.ensure_one()
        suffix = "reception" if self.document_type == "reception" else "delivery"
        return "%s-%s-signed.pdf" % (self._get_dms_safe_repair_name(), suffix)

    @api.model
    def _sanitize_dms_name(self, name, fallback="ITEM"):
        sanitized = (name or "").strip()
        if not sanitized:
            sanitized = fallback
        sanitized = re.sub(r'[<>:"/\\\\|?*]+', "-", sanitized)
        sanitized = re.sub(r"[\x00-\x1f]", "", sanitized)
        sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
        if not sanitized:
            sanitized = fallback
        return sanitized[:120]

    def _get_dms_safe_repair_name(self):
        self.ensure_one()
        return self._sanitize_dms_name(
            self.repair_order_id.name,
            fallback="REPAIR-%s" % self.repair_order_id.id,
        )

    def _get_or_create_dms_root_directory(self):
        self.ensure_one()
        company = self.company_id
        root_directory = company.x_wex_consent_dms_root_directory_id
        if root_directory and root_directory.exists():
            return root_directory

        storage = company.x_wex_consent_dms_storage_id
        if not storage:
            raise UserError(
                _("Configura primero el almacenamiento DMS para consentimientos en Ajustes.")
            )

        root_directory = self.env["dms.directory"].search(
            [
                ("is_root_directory", "=", True),
                ("storage_id", "=", storage.id),
                ("name", "=", "SAT"),
            ],
            limit=1,
        )
        if not root_directory:
            root_directory = self.env["dms.directory"].create(
                {
                    "name": "SAT",
                    "is_root_directory": True,
                    "storage_id": storage.id,
                }
            )
        company.x_wex_consent_dms_root_directory_id = root_directory
        return root_directory

    def _get_or_create_directory(self, parent_directory, name):
        self.ensure_one()
        directory = self.env["dms.directory"].search(
            [
                ("parent_id", "=", parent_directory.id),
                ("name", "=", name),
            ],
            limit=1,
        )
        if not directory:
            directory = self.env["dms.directory"].create(
                {
                    "name": name,
                    "parent_id": parent_directory.id,
                }
            )
        return directory

    def _get_or_create_signature_directory(self):
        self.ensure_one()
        root = self._get_or_create_dms_root_directory()
        repair_folder = self._get_or_create_directory(
            root, self._get_dms_safe_repair_name()
        )
        self._get_or_create_directory(repair_folder, "IMAGES")
        self._get_or_create_directory(repair_folder, "DOCUMENTS")
        return self._get_or_create_directory(repair_folder, "SIGNATURES")

    def _store_pdf_in_dms(self):
        self.ensure_one()
        if not self.pdf_file:
            return False
        directory = self._get_or_create_signature_directory()
        filename = self._get_signed_filename()
        existing = self.env["dms.file"].search(
            [
                ("directory_id", "=", directory.id),
                ("name", "=", filename),
            ],
            limit=1,
        )
        values = {
            "directory_id": directory.id,
            "name": filename,
            "content": self.pdf_file,
        }
        if existing:
            existing.write({"content": self.pdf_file})
            dms_file = existing
        else:
            dms_file = self.env["dms.file"].create(values)
        self.write(
            {
                "dms_file_id": dms_file.id,
                "dms_directory_id": directory.id,
            }
        )
        return dms_file

    def action_generate_signed_pdf(self):
        for rec in self:
            if not rec.signature_image:
                raise UserError(_("No se puede generar el PDF sin una firma capturada."))
            if rec.pdf_file and not self.env.context.get("force_regenerate_consent_pdf"):
                raise UserError(
                    _("El PDF firmado ya fue generado y no debe regenerarse desde la interfaz.")
                )
            report = self.env.ref(rec._get_report_xmlid())
            pdf_binary, _rendered_format = self.env["ir.actions.report"]._render_qweb_pdf(
                report.report_name,
                res_ids=rec.ids,
            )
            rec.write(
                {
                    "pdf_file": base64.b64encode(pdf_binary),
                    "pdf_filename": rec._get_signed_filename(),
                }
            )
            rec._store_pdf_in_dms()
            rec._message_repair_order(
                _("Documento de %(doc_type)s firmado y archivado en DMS.")
                % {"doc_type": rec._get_document_type_label(rec.document_type)}
            )
        return True

    def action_register_signature(
        self,
        signer_name,
        signature_image,
        confirmation_ok=False,
        signer_vat=False,
        consent_values=None,
        request=False,
    ):
        for rec in self:
            signature_image = rec._validate_signature_image(signature_image)
            if False:
                raise UserError(_("La firma está vacía."))
            values = {
                "signer_name": signer_name or rec.partner_id.name,
                "signer_vat": signer_vat or rec.partner_vat,
                "signature_image": signature_image,
                "signed_at": fields.Datetime.now(),
                "confirmation_ok": confirmation_ok,
                "state": "signed",
            }
            if consent_values:
                values.update(consent_values)
            rec.write(values)
            rec.action_generate_signed_pdf()
            rec._message_repair_order(
                _(
                    "Firma completada para %(doc_type)s. Firmante: %(signer)s (%(vat)s)."
                )
                % {
                    "doc_type": rec._get_document_type_label(rec.document_type),
                    "signer": values["signer_name"],
                    "vat": values.get("signer_vat") or _("Sin DNI"),
                }
            )
        return True

    def _sync_state_from_requests(self):
        for rec in self:
            if rec.state == "signed":
                continue
            active_requests = rec.request_ids.filtered(
                lambda request: request.state in ("queued", "presented")
            )
            if active_requests:
                rec.state = "pending_signature"
            elif rec.request_ids and all(
                request.state == "cancelled" for request in rec.request_ids
            ):
                rec.state = "cancelled"
            else:
                rec.state = "draft"

    def action_request_signature(self):
        self.ensure_one()
        if self.state == "signed":
            raise UserError(
                _("Este documento ya está firmado. No se puede reenviar una firma ya cerrada.")
            )
        self.action_refresh_from_repair()
        active_request = self.request_ids.filtered(
            lambda request: request.state in ("queued", "presented")
        )[:1]
        if active_request:
            return active_request
        request = self.env["wex.consent.request"].create(
            {
                "name": _("Solicitud %s") % self.name,
                "document_id": self.id,
            }
        )
        self.write({"state": "pending_signature"})
        self._message_repair_order(
            _(
                "Solicitud de firma creada para %(doc_type)s por %(user)s. Referencia: %(request)s."
            )
            % {
                "doc_type": self._get_document_type_label(self.document_type),
                "user": self.env.user.display_name,
                "request": request.name,
            }
        )
        return request

    def action_open_request_modal_for_request(self, request):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "wex_consent.open_signature_request",
            "name": _("Solicitud de firma"),
            "target": "new",
            "params": {
                "requestId": request.id,
                "documentId": self.id,
            },
        }

    def action_open_request_modal(self):
        self.ensure_one()
        request = self.action_request_signature()
        return self.action_open_request_modal_for_request(request)

    def action_open_pdf(self):
        self.ensure_one()
        if self.dms_file_id:
            return {
                "type": "ir.actions.act_window",
                "name": _("PDF firmado"),
                "res_model": "dms.file",
                "res_id": self.dms_file_id.id,
                "view_mode": "form",
                "target": "current",
            }
        if self.pdf_file:
            return {
                "type": "ir.actions.act_url",
                "url": "/web/content/%s/%s/pdf_file/%s?download=true"
                % (
                    self._name,
                    self.id,
                    self.pdf_filename or self._get_signed_filename(),
                ),
                "target": "self",
            }
        raise UserError(_("Este documento todavía no tiene PDF generado."))

    @api.model
    def kiosk_pull_next_request(self, session_id):
        self._check_kiosk_access()
        session = self.env["wex.consent.kiosk.session"].browse(session_id).exists()
        if not session:
            return False
        if session.active_request_id and session.active_request_id.state == "presented":
            session.touch(active_request_id=session.active_request_id.id)
            return session.active_request_id.id
        next_request = self.env["wex.consent.request"].search(
            [
                ("company_id", "=", session.company_id.id),
                ("state", "=", "queued"),
            ],
            order="queued_at asc, id asc",
            limit=1,
        )
        if not next_request:
            session.touch(active_request_id=False)
            return False
        next_request.action_mark_presented(session)
        return next_request.id
