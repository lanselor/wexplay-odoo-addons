# -*- coding: utf-8 -*-
import re
from urllib.parse import quote

from odoo import api, fields, models
from odoo.exceptions import UserError


class WhatsappComposeWizard(models.TransientModel):
    _name = "whatsapp.compose.wizard"
    _description = "Compose WhatsApp Message"

    # Document "type" for this wizard iteration.
    # NOTE: In later iterations (chatter integration), this will be driven by res_model/res_id context.
    res_model = fields.Selection(
        selection=[
            ("sale.order", "Sales: Quotation / Order"),
            ("account.move", "Accounting: Invoice"),
            ("repair.order", "Repairs: Repair Order"),
        ],
        string="Document Type",
        required=True,
        default="sale.order",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Recipient",
        required=True,
    )

    phone_source = fields.Selection(
        selection=[
            ("mobile", "Mobile"),
            ("phone", "Phone"),
            ("custom", "Custom"),
        ],
        string="Phone source",
        required=True,
        default="mobile",
    )

    # Required because opening WhatsApp (wa.me) needs a phone string.
    phone_number = fields.Char(string="Phone", required=True)

    template_id = fields.Many2one(
        "whatsapp.template",
        string="Template",
        domain="[('res_model', '=', res_model)]",
    )

    # Iteration 3: allow selecting a real document so we can generate a portal link.
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Quotation / Order",
    )

    account_move_id = fields.Many2one(
        "account.move",
        string="Invoice",
        # Critical: restrict to customer invoices/credit notes (out_*), and ignore canceled.
        domain="[('move_type', 'in', ('out_invoice','out_refund')), ('state', '!=', 'cancel')]",
    )

    # Computed portal URL. We make it absolute (base_url + relative) because WhatsApp needs a clickable URL.
    portal_url = fields.Char(
        string="Portal URL",
        compute="_compute_portal_url",
        store=False,
    )

    # Final message that will be URL-encoded into wa.me link.
    rendered_body = fields.Text(string="Message", required=True)

    @api.onchange("partner_id")
    def _onchange_partner_id_set_phone_defaults(self):
        for w in self:
            if not w.partner_id:
                continue
            # Critical UX: prefer mobile over phone. This aligns with WhatsApp expectations.
            if w.partner_id.mobile:
                w.phone_source = "mobile"
                w.phone_number = w.partner_id.mobile
            elif w.partner_id.phone:
                w.phone_source = "phone"
                w.phone_number = w.partner_id.phone

    @api.onchange("phone_source")
    def _onchange_phone_source(self):
        for w in self:
            if not w.partner_id:
                continue
            # We cannot use attrs/states in Odoo 18 views; so we drive behavior via onchange:
            # - "mobile" / "phone": override phone_number with partner's value
            # - "custom": keep what user typed
            if w.phone_source == "mobile":
                w.phone_number = w.partner_id.mobile or ""
            elif w.phone_source == "phone":
                w.phone_number = w.partner_id.phone or ""
            # custom: keep existing

    @api.onchange("template_id")
    def _onchange_template_id_set_body(self):
        for w in self:
            if w.template_id:
                # Iteration 2/3: copy raw template body.
                # Rendering variables safely requires a target record (res_id) and will be added later.
                w.rendered_body = w.template_id.body or ""

    @api.onchange("res_model")
    def _onchange_res_model_clear_document(self):
        for w in self:
            # Critical: avoid mixing a sale_order_id with account.move (and vice versa)
            # when the user switches the document type.
            w.sale_order_id = False
            w.account_move_id = False

    @api.depends("res_model", "sale_order_id", "account_move_id")
    def _compute_portal_url(self):
        # Critical: WhatsApp should receive absolute URLs. get_portal_url() can be relative.
        # We use web.base.url to build a full URL when needed.
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

            if not relative:
                continue

            # If Odoo already provides an absolute URL, keep it.
            if relative.startswith(("http://", "https://")):
                w.portal_url = relative
                continue

            # If base_url is missing (misconfiguration), fall back to relative.
            # This avoids producing an empty/invalid URL and keeps behavior predictable.
            if base_url:
                w.portal_url = f"{base_url}{relative}"
            else:
                w.portal_url = relative

    def _whatsapp_normalize_phone(self, phone):
        """
        wa.me expects an international phone number WITHOUT '+' and WITHOUT separators.

        Strategy:
        - Keep digits only
        - If it starts with '00' (international prefix), drop that prefix
        - Minimal ES heuristic: if company is ES and number has 9 digits, prefix '34'

        NOTE: This is intentionally minimal (no external libs). Full E.164 validation can be added later.
        """
        self.ensure_one()  # Critical: uses self.company_id for country heuristic.

        phone = (phone or "").strip()
        digits = re.sub(r"\D+", "", phone)

        if digits.startswith("00"):
            digits = digits[2:]

        # Minimal Spain heuristic:
        # If the user enters a local 9-digit number and the company is in Spain, prefix 34.
        # This prevents generating wa.me links that WhatsApp cannot resolve.
        if digits and len(digits) == 9:
            company_country = (self.company_id.country_id.code or "").upper()
            if company_country == "ES":
                digits = "34" + digits

        return digits

    def action_open_whatsapp(self):
        self.ensure_one()

        phone = self._whatsapp_normalize_phone(self.phone_number)
        if not phone:
            raise UserError("No hay teléfono válido para abrir WhatsApp.")

        message = (self.rendered_body or "").strip()
        if not message:
            raise UserError("El mensaje está vacío.")

        # Critical: must URL-encode message to preserve accents, newlines and punctuation safely.
        encoded = quote(message, safe="")
        url = f"https://wa.me/{phone}?text={encoded}"

        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def action_insert_portal_link(self):
        self.ensure_one()

        # Business rule: only Sales and Invoices have portal links in this phase.
        if self.res_model not in ("sale.order", "account.move"):
            raise UserError("Portal link is only available for Sales and Invoices.")

        if not self.portal_url:
            raise UserError("Select a document first to generate its portal link.")

        # Append link separated by a blank line to keep message readable in WhatsApp.
        msg = (self.rendered_body or "").rstrip()
        sep = "\n\n" if msg else ""
        self.rendered_body = f"{msg}{sep}{self.portal_url}"

        # Re-open the same wizard record (modal) so user sees the updated message immediately.
        return {
            "type": "ir.actions.act_window",
            "res_model": "whatsapp.compose.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
