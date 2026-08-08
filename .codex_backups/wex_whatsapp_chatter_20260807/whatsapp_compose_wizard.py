# -*- coding: utf-8 -*-

import re
from urllib.parse import quote
from datetime import date, datetime

from markupsafe import Markup, escape

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
from odoo.tools import format_date, format_datetime

RE_PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")
PORTAL_NATIVE_PLACEHOLDER = "${portal_url}"

SUPPORTED_RES_MODEL_SELECTION = [
    ("sale.order", "Sales: Quotation / Order"),
    ("account.move", "Accounting: Invoice"),
    ("repair.order", "Repairs: Repair Order"),
    ("res.partner", "Contacts: Contact"),
]


class WhatsappComposeWizard(models.TransientModel):
    _name = "whatsapp.compose.wizard"
    _description = "Compose WhatsApp Message"

    # ---------------------------------------------------------
    # Context document (from chatter)
    # ---------------------------------------------------------
    res_model_ctx = fields.Char(readonly=True)
    res_id_ctx = fields.Integer(readonly=True)

    res_model = fields.Selection(
        selection=SUPPORTED_RES_MODEL_SELECTION,
        required=True,
        default="sale.order",
    )

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )

    partner_id = fields.Many2one("res.partner", required=True)

    phone_source = fields.Selection(
        [
            ("mobile", "Mobile"),
            ("phone", "Phone"),
            ("custom", "Custom"),
        ],
        default="mobile",
        required=True,
    )

    phone_number = fields.Char(required=True)

    template_id = fields.Many2one(
        "whatsapp.template",
        domain="[('res_model', '=', res_model)]",
    )

    sale_order_id = fields.Many2one("sale.order")
    account_move_id = fields.Many2one(
        "account.move",
        domain="[('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '!=', 'cancel')]",
    )

    portal_link_type = fields.Selection(
        selection=[
            ("none", "Sin enlace"),
            ("current", "Documento actual"),
            ("sale_order", "Cotización / pedido del cliente"),
            ("account_move", "Factura del cliente"),
        ],
        default="none",
        required=True,
    )
    portal_commercial_partner_id = fields.Many2one(
        "res.partner",
        compute="_compute_portal_commercial_partner_id",
        store=False,
    )
    portal_link_status = fields.Char(compute="_compute_portal_link_status", store=False)
    portal_link_available = fields.Boolean(compute="_compute_portal_link_status", store=False)
    portal_url = fields.Char(compute="_compute_portal_url", store=False)
    rendered_body = fields.Text(required=True)
    rendered_body_preview_html = fields.Html(
        compute="_compute_rendered_body_preview_html",
        sanitize=False,
        store=False,
    )

    # =========================================================
    # 7.1 SERVER-SIDE NORMALIZATION / GUARDRAILS
    # =========================================================
    @api.model
    def _get_supported_res_models(self):
        return {model for model, _label in SUPPORTED_RES_MODEL_SELECTION}

    @api.model
    def _check_supported_res_model(self, res_model):
        if res_model and res_model not in self._get_supported_res_models():
            raise UserError(_(
                "WhatsApp no está disponible para este tipo de documento: %(model)s"
            ) % {"model": res_model})

    def _is_from_repair_chatter(self, vals=None):
        """True if wizard is opened from chatter on repair.order."""
        self.ensure_one() if self else None
        ctx = self.env.context
        res_model = (
            (vals or {}).get("res_model_ctx")
            or getattr(self, "res_model_ctx", False)
            or ctx.get("default_res_model")
        )
        return res_model == "repair.order"

    def _normalize_and_validate_template(self, vals):
        """
        Enforce:
        - If coming from repair.order chatter => res_model must be repair.order
        - template_id must match res_model (and for repair chatter: must be repair.order)
        """
        ctx = self.env.context
        ctx_res_model = vals.get("res_model_ctx") or ctx.get("default_res_model")
        ctx_res_id = vals.get("res_id_ctx") or ctx.get("default_res_id")
        res_model = vals.get("res_model") or ctx_res_model

        self._check_supported_res_model(ctx_res_model)
        self._check_supported_res_model(res_model)

        # Force wizard model when launched from chatter repair.order
        if ctx_res_model == "repair.order":
            vals["res_model"] = "repair.order"
            vals["res_model_ctx"] = "repair.order"
            if ctx_res_id and not vals.get("res_id_ctx"):
                vals["res_id_ctx"] = ctx_res_id

        # Validate template_id vs res_model (no cross templates)
        template_id = vals.get("template_id")
        if template_id:
            template = self.env["whatsapp.template"].browse(template_id).exists()
            if not template:
                raise UserError(_("La plantilla seleccionada no existe."))
            if template.res_model != res_model:
                raise UserError(_(
                    "Plantilla inválida para este documento.\n"
                    "Plantilla: %(tpl)s\n"
                    "Aplica a: %(tpl_model)s\n"
                    "Wizard: %(wiz_model)s"
                ) % {
                    "tpl": template.display_name,
                    "tpl_model": template.res_model,
                    "wiz_model": res_model,
                })

        return vals

    def _post_guardrail_note(self, action, details=None):
        """
        Post a note in the chatter of the originating record
        when we enforce/deny cross-model template usage.
        """
        self.ensure_one()
        obj = self._get_target_record()
        if not obj or not hasattr(obj, "message_post"):
            return

        body = _("WhatsApp (seguridad): %(action)s") % {"action": action}
        if details:
            body += "<br/>" + details

        obj.message_post(
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    # ---------------------------------------------------------
    # Default get
    # ---------------------------------------------------------
    @api.model
    def _get_default_phone_source(self, partner):
        if partner.mobile:
            return "mobile"
        if partner.phone:
            return "phone"
        return "custom"

    @api.model
    def _get_phone_number_for_source(self, partner, phone_source):
        if not partner:
            return ""
        if phone_source == "mobile":
            return partner.mobile or ""
        if phone_source == "phone":
            return partner.phone or ""
        return False

    @api.model
    def _prepare_origin_defaults(self, res_model, res_id):
        if not (res_model and res_id):
            return {}

        self._check_supported_res_model(res_model)

        vals = {
            "res_model_ctx": res_model,
            "res_id_ctx": res_id,
            "res_model": res_model,
        }

        record = self.env[res_model].browse(res_id).exists()
        if not record:
            return vals

        if "partner_id" in record._fields and record.partner_id:
            vals["partner_id"] = record.partner_id.id
        elif res_model == "res.partner":
            vals["partner_id"] = record.id

        if "company_id" in record._fields and record.company_id:
            vals["company_id"] = record.company_id.id

        return vals

    @api.model
    def _apply_partner_phone_defaults(self, vals):
        partner = self.env["res.partner"].browse(vals.get("partner_id")).exists()
        if partner and not vals.get("phone_number"):
            phone_source = vals.get("phone_source") or self._get_default_phone_source(partner)
            vals["phone_source"] = phone_source
            vals["phone_number"] = self._get_phone_number_for_source(partner, phone_source)
        return vals

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        ctx = self.env.context

        res_model = ctx.get("default_res_model")
        res_id = ctx.get("default_res_id")

        vals.update(self._prepare_origin_defaults(res_model, res_id))
        vals.setdefault("portal_link_type", self._get_default_portal_link_type(vals.get("res_model")))
        vals = self._apply_partner_phone_defaults(vals)
        vals = self._normalize_and_validate_template(vals)
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals in vals_list:
            vals = dict(vals or {})
            vals = self._normalize_and_validate_template(vals)
            new_vals_list.append(vals)

        records = super().create(new_vals_list)

        for w in records:
            ctx_res_model = w.res_model_ctx or w.env.context.get("default_res_model")
            if ctx_res_model == "repair.order" and w.res_model != "repair.order":
                w._post_guardrail_note(
                    action=_("Corrección automática de modelo"),
                    details=_("Se forzó res_model a repair.order por origen en SAT."),
                )
            elif ctx_res_model == "repair.order":
                w._post_guardrail_note(
                    action=_("Modelo normalizado"),
                    details=_("Origen SAT: el asistente solo permite plantillas de repair.order."),
                )

        return records

    def write(self, vals):
        for w in self:
            incoming = dict(vals or {})
            merged = dict(incoming)

            if w.res_model_ctx and "res_model_ctx" not in merged:
                merged["res_model_ctx"] = w.res_model_ctx
            if w.res_id_ctx and "res_id_ctx" not in merged:
                merged["res_id_ctx"] = w.res_id_ctx
            if w.res_model and "res_model" not in merged:
                merged["res_model"] = w.res_model

            merged = w._normalize_and_validate_template(merged)

            enforced_keys = set(merged.keys()) - set(incoming.keys())
            safe_vals = dict(incoming)
            for k in enforced_keys:
                safe_vals[k] = merged[k]

            if w._is_from_repair_chatter(safe_vals):
                if "res_model" in incoming and incoming["res_model"] != "repair.order":
                    w._post_guardrail_note(
                        action=_("Bloqueado cambio de tipo de documento"),
                        details=_("Se intentó cambiar res_model a %(m)s; se mantuvo repair.order.") % {
                            "m": incoming["res_model"]
                        },
                    )
                if "template_id" in incoming:
                    tpl = w.env["whatsapp.template"].browse(incoming["template_id"]).exists()
                    if tpl and tpl.res_model != "repair.order":
                        w._post_guardrail_note(
                            action=_("Plantilla cruzada bloqueada"),
                            details=_("Plantilla %(t)s aplica a %(m)s.") % {
                                "t": tpl.display_name,
                                "m": tpl.res_model,
                            },
                        )

            super(WhatsappComposeWizard, w).write(safe_vals)

        return True

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def _get_target_record_from_context(self):
        self.ensure_one()
        if self.res_model_ctx and self.res_id_ctx:
            return self.env[self.res_model_ctx].browse(self.res_id_ctx).exists()
        return self.env[self.res_model].browse()

    def _get_target_record_from_selected_document(self):
        self.ensure_one()

        if self.res_model == "sale.order" and self.sale_order_id:
            return self.sale_order_id

        if self.res_model == "account.move" and self.account_move_id:
            return self.account_move_id

        if self.res_model == "res.partner" and self.partner_id:
            return self.partner_id

        return self.env[self.res_model].browse()

    def _get_target_record(self):
        self.ensure_one()

        target = self._get_target_record_from_context()
        return target or self._get_target_record_from_selected_document()

    def _get_default_portal_link_type(self, res_model):
        if res_model in ("sale.order", "account.move"):
            return "current"
        return "none"

    def _get_partner_commercial_partner(self):
        self.ensure_one()
        return self.partner_id.commercial_partner_id if self.partner_id else self.env["res.partner"]

    def _check_record_belongs_to_partner(self, record):
        self.ensure_one()
        if not record:
            return False

        record_partner = getattr(record, "partner_id", False)
        if not record_partner or not self.partner_id:
            return False

        return record_partner.commercial_partner_id == self._get_partner_commercial_partner()

    def _get_current_document_portal_url(self):
        self.ensure_one()
        target = self._get_target_record()
        if not target or not hasattr(target, "get_portal_url"):
            return ""
        if self.res_model_ctx not in ("sale.order", "account.move"):
            return ""
        if not self._check_record_belongs_to_partner(target):
            return ""
        return target.get_portal_url() or ""

    def _get_sale_order_portal_url(self):
        self.ensure_one()
        if not self.sale_order_id:
            return ""
        if not self._check_record_belongs_to_partner(self.sale_order_id):
            return ""
        return self.sale_order_id.get_portal_url() or ""

    def _get_account_move_portal_url(self):
        self.ensure_one()
        if not self.account_move_id:
            return ""
        if not self._check_record_belongs_to_partner(self.account_move_id):
            return ""
        return self.account_move_id.get_portal_url() or ""

    def _get_portal_link_url(self):
        self.ensure_one()
        if self.portal_link_type == "current":
            return self._get_current_document_portal_url()
        if self.portal_link_type == "sale_order":
            return self._get_sale_order_portal_url()
        if self.portal_link_type == "account_move":
            return self._get_account_move_portal_url()
        return ""

    def _is_native_portal_link_type(self):
        self.ensure_one()
        return self.portal_link_type in ("current", "sale_order", "account_move")

    def _get_portal_link_status(self):
        self.ensure_one()
        if self.portal_link_type == "none":
            return _("No se insertará ningún enlace."), False
        if not self.partner_id:
            return _("Selecciona un cliente para filtrar documentos."), False
        if self.portal_link_type == "current":
            if self.res_model_ctx not in ("sale.order", "account.move"):
                return _("El documento actual no tiene enlace de portal nativo disponible."), False
            if self.portal_url:
                return _("Enlace nativo del documento actual disponible."), True
            return _("No se puede generar enlace para el documento actual."), False
        if self.portal_link_type == "sale_order":
            if self.portal_url:
                return _("Cotización/pedido del cliente listo para insertar."), True
            return _("Selecciona una cotización o pedido del cliente."), False
        if self.portal_link_type == "account_move":
            if self.portal_url:
                return _("Factura del cliente lista para insertar."), True
            return _("Selecciona una factura del cliente."), False
        return _("Tipo de enlace no soportado."), False

    def _safe_getattr_path(self, record, path, max_depth=6):
        if not record or not path:
            return None

        parts = [p for p in path.split(".") if p]
        if len(parts) > max_depth:
            return None

        current = record
        for part in parts:
            if not hasattr(current, "_fields"):
                return None
            if part not in current._fields:
                return None
            current = current[part]
            if not current:
                return None
        return current

    def _is_safe_getattr_path_supported(self, record, path, max_depth=6):
        if not record or not path or not hasattr(record, "_fields"):
            return False

        parts = [p for p in path.split(".") if p]
        if not parts or len(parts) > max_depth:
            return False

        current = record
        for part in parts:
            if not hasattr(current, "_fields") or part not in current._fields:
                return False
            field = current._fields[part]
            if field.type in ("many2one", "one2many", "many2many"):
                current = self.env[field.comodel_name]
            else:
                current = False
        return True

    def _format_value(self, obj, value):
        if value is None or value is False:
            return ""

        if hasattr(value, "exists") and hasattr(value, "display_name"):
            if len(value) == 1:
                return value.display_name or ""
            names = value.mapped("display_name")
            return ", ".join(names[:5]) if names else ""

        if isinstance(value, bool):
            return "Sí" if value else "No"

        if isinstance(value, datetime):
            return format_datetime(self.env, value)

        if isinstance(value, date):
            return format_date(self.env, value)

        if isinstance(value, (int, float)):
            currency = getattr(obj, "currency_id", False)
            return (
                formatLang(self.env, value, currency_obj=currency)
                if currency
                else formatLang(self.env, value)
            )

        return str(value)

    def _get_dispositivo(self, obj):
        if not obj or not hasattr(obj, "_fields"):
            return ""

        target_model = "wex.repair.device_model"

        device_model = None
        for fname, field in obj._fields.items():
            if field.type == "many2one" and field.comodel_name == target_model:
                if obj[fname]:
                    device_model = obj[fname]
                    break

        if not device_model:
            return ""

        dtype = ""
        if "device_type" in device_model._fields and device_model.device_type:
            sel = dict(device_model._fields["device_type"].selection or [])
            dtype = sel.get(device_model.device_type, device_model.device_type)

        brand = ""
        if "brand_id" in device_model._fields and device_model.brand_id:
            brand = device_model.brand_id.name or ""

        model = (device_model.name or "").strip()
        if not model:
            model = (device_model.display_name or "").strip()

        parts = [p for p in [dtype, brand, model] if p]
        return " · ".join(parts)

    # ---------------------------------------------------------
    # Chatter log (WhatsApp style)
    # ---------------------------------------------------------
    def _prepare_whatsapp_open_note_body(self, normalized_phone, message):
        self.ensure_one()

        template_name = self.template_id.display_name if self.template_id else _("Sin plantilla")
        partner_name = self.partner_id.display_name if self.partner_id else _("Sin contacto")
        user_name = self.env.user.display_name or _("Usuario desconocido")

        safe_phone = escape(normalized_phone or "")
        safe_template = escape(template_name)
        safe_partner = escape(partner_name)
        safe_user = escape(user_name)

        safe_message = escape(message or "")
        safe_message = safe_message.replace("\n", Markup("<br/>"))

        return Markup("""
            <div class="wex-wa-log">
                <div class="wex-wa-log__header">
                    <span class="wex-wa-log__badge">WhatsApp preparado</span>
                    <span class="wex-wa-log__title">WhatsApp preparado desde Odoo</span>
                    <span class="wex-wa-log__meta-note">
                        No confirma el envío final dentro de WhatsApp
                    </span>
                </div>

                <div class="wex-wa-log__chat-bg">
                    <div class="wex-wa-log__row wex-wa-log__row--out">
                        <div class="wex-wa-log__bubble">
                            <div class="wex-wa-log__text">%(message)s</div>
                            <div class="wex-wa-log__bubble-meta">
                                <span>Odoo</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="wex-wa-log__details">
                    <div><strong>Contacto:</strong> %(partner)s</div>
                    <div><strong>Teléfono:</strong> %(phone)s</div>
                    <div><strong>Plantilla:</strong> %(template)s</div>
                    <div><strong>Usuario:</strong> %(user)s</div>
                </div>
            </div>
        """) % {
            "partner": safe_partner,
            "phone": safe_phone,
            "template": safe_template,
            "user": safe_user,
            "message": safe_message,
        }

    def _post_whatsapp_open_note(self, normalized_phone, message):
        """
        Registra en el chatter que el usuario pulsó 'Abrir WhatsApp' desde Odoo.
        OJO: esto NO confirma que el usuario haya pulsado 'Enviar' dentro de WhatsApp.
        """
        self.ensure_one()

        target = self._get_target_record()
        if not target or not hasattr(target, "message_post"):
            return

        target.message_post(
            body=self._prepare_whatsapp_open_note_body(normalized_phone, message),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    # ---------------------------------------------------------
    # Renderer
    # ---------------------------------------------------------
    def _get_render_context(self):
        self.ensure_one()
        return {
            "object": self._get_target_record(),
            "partner": self.partner_id,
            "company": self.company_id or self.env.company,
            "user": self.env.user,
        }

    def _format_unresolved_placeholder(self, expr):
        return "${%s}" % (expr or "").strip()

    def _get_amount_value(self, obj):
        if not obj or not hasattr(obj, "_fields"):
            return None, obj
        if "x_sat_total_amount" in obj._fields:
            return obj.x_sat_total_amount, obj
        if "amount_total" in obj._fields:
            return obj.amount_total, obj
        return None, obj

    def _get_repair_notes(self, obj):
        if not obj or getattr(obj, "_name", "") != "repair.order":
            return ""
        if "internal_notes" not in obj._fields:
            return ""
        return tools.html2plaintext(obj.internal_notes or "").strip()

    def _render_placeholder(self, expr, render_context):
        self.ensure_one()
        expr = (expr or "").strip()

        if expr == "portal_url":
            if self._is_native_portal_link_type():
                return self.portal_url or self._format_unresolved_placeholder(expr)
            return self._format_unresolved_placeholder(expr)

        if expr == "dispositivo":
            return self._get_dispositivo(render_context["object"])

        if expr == "importe":
            value, currency_source = self._get_amount_value(render_context["object"])
            return self._format_value(currency_source, value)

        if expr == "referencia_cliente":
            val = self._safe_getattr_path(render_context["object"], "x_customer_reference")
            return self._format_value(render_context["object"], val)

        if expr == "notasreparacion":
            return self._get_repair_notes(render_context["object"])

        for prefix, record in render_context.items():
            prefix_dot = f"{prefix}."
            if expr.startswith(prefix_dot):
                path = expr.split(".", 1)[1]
                if not self._is_safe_getattr_path_supported(record, path):
                    return self._format_unresolved_placeholder(expr)
                val = self._safe_getattr_path(record, path)
                return self._format_value(record, val)

        return self._format_unresolved_placeholder(expr)

    def _render_text(self, template_text):
        self.ensure_one()
        render_context = self._get_render_context()

        def repl(match):
            return self._render_placeholder(match.group(1), render_context)

        return RE_PLACEHOLDER.sub(repl, template_text or "")

    def _get_unresolved_placeholders(self, message):
        placeholders = []
        for match in RE_PLACEHOLDER.finditer(message or ""):
            placeholder = self._format_unresolved_placeholder(match.group(1))
            if placeholder not in placeholders:
                placeholders.append(placeholder)
        return placeholders

    def _check_no_unresolved_placeholders(self, message):
        unresolved = self._get_unresolved_placeholders(message)
        if unresolved:
            raise UserError(_(
                "El mensaje contiene variables sin resolver:\n%(variables)s\n\n"
                "Revisa que estén bien escritas o elimínalas antes de abrir WhatsApp."
            ) % {"variables": "\n".join(unresolved)})

    def _apply_whatsapp_preview_formatting(self, safe_message):
        safe_message = re.sub(
            r"```([^`\n]+)```",
            r"<code>\1</code>",
            safe_message,
        )
        safe_message = re.sub(
            r"(?<!\w)\*([^*\n]+)\*(?!\w)",
            r"<strong>\1</strong>",
            safe_message,
        )
        safe_message = re.sub(
            r"(?<!\w)_([^_\n]+)_(?!\w)",
            r"<em>\1</em>",
            safe_message,
        )
        safe_message = re.sub(
            r"(?<!\w)~([^~\n]+)~(?!\w)",
            r"<s>\1</s>",
            safe_message,
        )
        return safe_message

    def _apply_template(self):
        for w in self:
            if w.template_id:
                w.rendered_body = w._render_text(w.template_id.body or "")

    @api.depends("rendered_body")
    def _compute_rendered_body_preview_html(self):
        for w in self:
            safe_message = str(escape(w.rendered_body or ""))
            safe_message = w._apply_whatsapp_preview_formatting(safe_message)
            safe_message = Markup(safe_message).replace("\n", Markup("<br/>"))
            w.rendered_body_preview_html = Markup("""
                <div class="wex-wa-preview">
                    <div class="wex-wa-preview__header">
                        <span class="wex-wa-preview__title">Previsualización WhatsApp</span>
                        <span class="wex-wa-preview__subtitle">Así se preparará el texto antes de abrir WhatsApp</span>
                    </div>
                    <div class="wex-wa-preview__chat">
                        <div class="wex-wa-preview__bubble">
                            <div class="wex-wa-preview__text">%(message)s</div>
                            <div class="wex-wa-preview__meta">Odoo</div>
                        </div>
                    </div>
                </div>
            """) % {"message": safe_message}

    # ---------------------------------------------------------
    # Onchange logic
    # ---------------------------------------------------------
    @api.onchange("partner_id")
    def _onchange_partner(self):
        for w in self:
            if not w.partner_id:
                w.phone_number = ""
                continue
            if w.phone_source == "custom" and w.phone_number:
                continue
            w.phone_source = w._get_default_phone_source(w.partner_id)
            w.phone_number = w._get_phone_number_for_source(w.partner_id, w.phone_source)
        self._apply_template()

    @api.onchange("phone_source")
    def _onchange_phone_source(self):
        for w in self:
            if w.phone_source == "custom":
                continue
            w.phone_number = w._get_phone_number_for_source(w.partner_id, w.phone_source)

    @api.onchange("partner_id", "portal_link_type")
    def _onchange_portal_link_context(self):
        for w in self:
            if w.portal_link_type != "sale_order":
                w.sale_order_id = False
            if w.portal_link_type != "account_move":
                w.account_move_id = False

    @api.onchange("template_id", "res_model")
    def _onchange_template(self):
        self._apply_template()

    # ---------------------------------------------------------
    # Portal URL
    # ---------------------------------------------------------
    @api.depends(
        "portal_link_type",
        "res_model_ctx",
        "res_id_ctx",
        "partner_id",
        "sale_order_id",
        "account_move_id",
    )
    def _compute_portal_url(self):
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "")
            .rstrip("/")
        )

        for w in self:
            relative = w._get_portal_link_url()
            if relative:
                if relative.startswith(("http://", "https://")):
                    w.portal_url = relative
                elif base_url:
                    w.portal_url = f"{base_url}{relative}"
                else:
                    w.portal_url = relative
            else:
                w.portal_url = ""

    @api.depends("partner_id")
    def _compute_portal_commercial_partner_id(self):
        for w in self:
            w.portal_commercial_partner_id = (
                w.partner_id.commercial_partner_id if w.partner_id else False
            )

    @api.depends("portal_link_type", "partner_id", "portal_url", "sale_order_id", "account_move_id")
    def _compute_portal_link_status(self):
        for w in self:
            status, is_available = w._get_portal_link_status()
            w.portal_link_status = status
            w.portal_link_available = is_available

    # ---------------------------------------------------------
    # WhatsApp logic
    # ---------------------------------------------------------
    def _prepare_whatsapp_url(self, phone, message):
        encoded = quote(message, safe="")
        return f"https://wa.me/{phone}?text={encoded}"

    def _whatsapp_normalize_phone(self, phone):
        self.ensure_one()
        phone = (phone or "").strip()
        digits = re.sub(r"\D+", "", phone)

        if digits.startswith("00"):
            digits = digits[2:]

        if digits and len(digits) == 9:
            if (self.company_id.country_id.code or "").upper() == "ES":
                digits = "34" + digits

        return digits

    def action_open_whatsapp(self):
        self.ensure_one()

        phone = self._whatsapp_normalize_phone(self.phone_number)
        if not phone:
            raise UserError(_("No hay teléfono válido para abrir WhatsApp."))

        message = (self.rendered_body or "").strip()
        if not message:
            raise UserError(_("El mensaje está vacío."))
        self._check_no_unresolved_placeholders(message)

        self._post_whatsapp_open_note(phone, message)

        return {
            "type": "ir.actions.client",
            "tag": "wex_whatsapp_chatter.open_whatsapp_and_reload",
            "params": {
                "url": self._prepare_whatsapp_url(phone, message),
            },
        }

    def action_insert_portal_link(self):
        self.ensure_one()

        if self.portal_link_type == "none":
            raise UserError(_("Selecciona un tipo de enlace antes de insertarlo."))

        if not self.portal_url:
            raise UserError(self.portal_link_status or _("No se puede generar el enlace seleccionado."))

        msg = (self.rendered_body or "").rstrip()
        placeholder = self._get_portal_link_placeholder()
        if placeholder and placeholder in msg:
            self.rendered_body = msg.replace(placeholder, self.portal_url)
        else:
            sep = "\n\n" if msg else ""
            self.rendered_body = f"{msg}{sep}{self.portal_url}"

        return {
            "type": "ir.actions.act_window",
            "res_model": "whatsapp.compose.wizard",
            "views": [[False, "form"]],
            "res_id": self.id,
            "target": "new",
        }

    def _get_portal_link_placeholder(self):
        self.ensure_one()
        if self._is_native_portal_link_type():
            return PORTAL_NATIVE_PLACEHOLDER
        return ""
