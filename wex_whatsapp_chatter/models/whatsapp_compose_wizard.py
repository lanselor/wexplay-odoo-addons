# -*- coding: utf-8 -*-
import re
from urllib.parse import quote
from datetime import date, datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
from odoo.tools import format_date, format_datetime


RE_PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")


class WhatsappComposeWizard(models.TransientModel):
    _name = "whatsapp.compose.wizard"
    _description = "Compose WhatsApp Message"

    # ---------------------------------------------------------
    # Context document (from chatter)
    # ---------------------------------------------------------
    res_model_ctx = fields.Char(readonly=True)
    res_id_ctx = fields.Integer(readonly=True)

    res_model = fields.Selection(
        selection=[
            ("sale.order", "Sales: Quotation / Order"),
            ("account.move", "Accounting: Invoice"),
            ("repair.order", "Repairs: Repair Order"),
        ],
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
        domain="[('move_type','in',('out_invoice','out_refund')),('state','!=','cancel')]",
    )

    portal_url = fields.Char(compute="_compute_portal_url", store=False)
    rendered_body = fields.Text(required=True)

    # =========================================================
    # 7.1 SERVER-SIDE NORMALIZATION / GUARDRAILS
    # =========================================================
    def _is_from_repair_chatter(self, vals=None):
        """True if wizard is opened from chatter on repair.order."""
        self.ensure_one() if self else None
        ctx = self.env.context
        res_model = (vals or {}).get("res_model_ctx") or getattr(self, "res_model_ctx", False) or ctx.get("default_res_model")
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

        # Force wizard model when launched from chatter repair.order
        if ctx_res_model == "repair.order":
            vals["res_model"] = "repair.order"
            vals["res_model_ctx"] = "repair.order"
            if ctx_res_id and not vals.get("res_id_ctx"):
                vals["res_id_ctx"] = ctx_res_id

        # Validate template_id vs res_model (no cross templates)
        template_id = vals.get("template_id")
        res_model = vals.get("res_model") or ctx_res_model
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
        Post a note in the chatter of the originating record (repair/order/invoice),
        when we enforce/deny cross-model template usage.
        """
        self.ensure_one()
        obj = self._get_target_record()
        if not obj or not hasattr(obj, "message_post"):
            return

        body = _("WhatsApp (seguridad): %(action)s") % {"action": action}
        if details:
            body += "<br/>" + details

        # Try to post as internal note (comment)
        obj.message_post(
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    # ---------------------------------------------------------
    # Default get
    # ---------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        ctx = self.env.context

        res_model = ctx.get("default_res_model")
        res_id = ctx.get("default_res_id")

        if res_model and res_id:
            vals["res_model_ctx"] = res_model
            vals["res_id_ctx"] = res_id
            vals["res_model"] = res_model

            record = self.env[res_model].browse(res_id).exists()
            if record:
                if "partner_id" in record._fields and record.partner_id:
                    vals["partner_id"] = record.partner_id.id
                if "company_id" in record._fields and record.company_id:
                    vals["company_id"] = record.company_id.id

        # 7.1 enforce at default_get level
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

        # If we forced res_model due to repair chatter, log it once
        for w in records:
            ctx_res_model = w.res_model_ctx or w.env.context.get("default_res_model")
            if ctx_res_model == "repair.order" and w.res_model != "repair.order":
                # Should never happen due to enforcement, but keep for safety.
                w._post_guardrail_note(
                    action=_("Corrección automática de modelo"),
                    details=_("Se forzó res_model a repair.order por origen en SAT."),
                )
            elif ctx_res_model == "repair.order":
                # Log enforcement (optional but requested)
                w._post_guardrail_note(
                    action=_("Modelo normalizado"),
                    details=_("Origen SAT: el asistente solo permite plantillas de repair.order."),
                )

        return records

    def write(self, vals):
        # Before write: capture if this is repair chatter
        for w in self:
            incoming = dict(vals or {})
            merged = dict(incoming)
            # include current ctx fields so validator can compare
            if w.res_model_ctx and "res_model_ctx" not in merged:
                merged["res_model_ctx"] = w.res_model_ctx
            if w.res_id_ctx and "res_id_ctx" not in merged:
                merged["res_id_ctx"] = w.res_id_ctx
            if w.res_model and "res_model" not in merged:
                merged["res_model"] = w.res_model

            merged = w._normalize_and_validate_template(merged)

            # We only want to write the keys user intended + enforcement keys
            enforced_keys = set(merged.keys()) - set(incoming.keys())
            safe_vals = dict(incoming)
            # apply enforced keys too
            for k in enforced_keys:
                safe_vals[k] = merged[k]

            # If they tried to change to cross-model template, validator already raised.
            # If enforcement changed res_model back to repair.order, log it.
            if w._is_from_repair_chatter(safe_vals):
                # If user tried to switch model away from repair.order
                if "res_model" in incoming and incoming["res_model"] != "repair.order":
                    w._post_guardrail_note(
                        action=_("Bloqueado cambio de tipo de documento"),
                        details=_("Se intentó cambiar res_model a %(m)s; se mantuvo repair.order.") % {"m": incoming["res_model"]},
                    )
                # If user tried to apply template from other model (would have raised)
                if "template_id" in incoming:
                    tpl = w.env["whatsapp.template"].browse(incoming["template_id"]).exists()
                    if tpl and tpl.res_model != "repair.order":
                        # would not reach here due to raise, but keep belt+suspenders
                        w._post_guardrail_note(
                            action=_("Plantilla cruzada bloqueada"),
                            details=_("Plantilla %(t)s aplica a %(m)s.") % {"t": tpl.display_name, "m": tpl.res_model},
                        )

            super(WhatsappComposeWizard, w).write(safe_vals)

        return True

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def _get_target_record(self):
        self.ensure_one()

        if self.res_model_ctx and self.res_id_ctx:
            return self.env[self.res_model_ctx].browse(self.res_id_ctx).exists()

        if self.res_model == "sale.order" and self.sale_order_id:
            return self.sale_order_id

        if self.res_model == "account.move" and self.account_move_id:
            return self.account_move_id

        return self.env[self.res_model].browse()

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

    # ---------------------------------------------------------
    # ${dispositivo}
    # ---------------------------------------------------------
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
    # Renderer
    # ---------------------------------------------------------
    def _render_text(self, template_text):
        self.ensure_one()

        obj = self._get_target_record()
        partner = self.partner_id
        company = self.company_id or self.env.company
        user = self.env.user

        def repl(match):
            expr = (match.group(1) or "").strip()

            if expr == "portal_url":
                return self.portal_url or ""

            if expr == "dispositivo":
                return self._get_dispositivo(obj)

            if expr.startswith("company."):
                val = self._safe_getattr_path(company, expr.split(".", 1)[1])
                return self._format_value(company, val)

            if expr.startswith("user."):
                val = self._safe_getattr_path(user, expr.split(".", 1)[1])
                return self._format_value(user, val)

            if expr.startswith("object."):
                val = self._safe_getattr_path(obj, expr.split(".", 1)[1])
                return self._format_value(obj, val)

            if expr.startswith("partner."):
                val = self._safe_getattr_path(partner, expr.split(".", 1)[1])
                return self._format_value(partner, val)

            return ""

        return RE_PLACEHOLDER.sub(repl, template_text or "")

    def _apply_template(self):
        for w in self:
            if w.template_id:
                w.rendered_body = w._render_text(w.template_id.body or "")

    # ---------------------------------------------------------
    # Onchange logic
    # ---------------------------------------------------------
    @api.onchange("partner_id")
    def _onchange_partner(self):
        for w in self:
            if w.partner_id.mobile:
                w.phone_source = "mobile"
                w.phone_number = w.partner_id.mobile
            elif w.partner_id.phone:
                w.phone_source = "phone"
                w.phone_number = w.partner_id.phone
        self._apply_template()

    @api.onchange("template_id", "res_model", "sale_order_id", "account_move_id")
    def _onchange_template(self):
        self._apply_template()

    # ---------------------------------------------------------
    # Portal URL
    # ---------------------------------------------------------
    @api.depends("res_model", "sale_order_id", "account_move_id")
    def _compute_portal_url(self):
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "")
            .rstrip("/")
        )

        for w in self:
            w.portal_url = ""
            relative = ""

            if w.res_model == "sale.order" and w.sale_order_id:
                relative = w.sale_order_id.get_portal_url()
            elif w.res_model == "account.move" and w.account_move_id:
                relative = w.account_move_id.get_portal_url()

            if relative:
                if relative.startswith(("http://", "https://")):
                    w.portal_url = relative
                elif base_url:
                    w.portal_url = f"{base_url}{relative}"
                else:
                    w.portal_url = relative

    # ---------------------------------------------------------
    # WhatsApp logic
    # ---------------------------------------------------------
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

        encoded = quote(message, safe="")
        url = f"https://wa.me/{phone}?text={encoded}"

        return {"type": "ir.actions.act_url", "url": url, "target": "new"}

    def action_insert_portal_link(self):
        self.ensure_one()

        if self.res_model not in ("sale.order", "account.move"):
            raise UserError(_("Portal link is only available for Sales and Invoices."))

        if not self.portal_url:
            raise UserError(_("Select a document first."))

        msg = (self.rendered_body or "").rstrip()
        sep = "\n\n" if msg else ""
        self.rendered_body = f"{msg}{sep}{self.portal_url}"

        return {
            "type": "ir.actions.act_window",
            "res_model": "whatsapp.compose.wizard",
            "views": [[False, "form"]],
            "res_id": self.id,
            "target": "new",
        }