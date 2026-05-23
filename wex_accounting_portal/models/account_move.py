import json
from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, MissingError
from odoo.osv import expression
from odoo.tools import format_amount

_WEX_PORTAL_SCOPE_MOVE_TYPES = {
    "sale": ("out_invoice", "out_refund"),
    "purchase": ("in_invoice", "in_refund"),
}
_WEX_PORTAL_EXCLUDED_STATES = ("cancel",)
_WEX_PORTAL_BASE_URL = "/my/accounting"


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_wex_accounting_portal_scope(self, scope=None):
        return scope if scope in _WEX_PORTAL_SCOPE_MOVE_TYPES else "sale"

    @api.model
    def _get_wex_accounting_portal_move_types(self, scope=None):
        return _WEX_PORTAL_SCOPE_MOVE_TYPES[self._get_wex_accounting_portal_scope(scope)]

    def _check_wex_accounting_portal_access(self, user):
        self.ensure_one()
        if not self._can_user_access_wex_accounting_portal_record(user):
            raise AccessError(_("You cannot access this invoice from the Wex accounting portal."))

    @api.model
    def _get_wex_accounting_portal_period_domain(self, start_date=None, end_date=None):
        domain = []
        if start_date:
            domain.append(("invoice_date", ">=", start_date))
        if end_date:
            domain.append(("invoice_date", "<=", end_date))
        return domain

    @api.model
    def _get_wex_accounting_portal_company_ids(self, user, company_ids=None):
        allowed_company_ids = user.company_ids.ids or [user.company_id.id]
        if company_ids:
            return [company_id for company_id in company_ids if company_id in allowed_company_ids]
        return allowed_company_ids

    @api.model
    def _get_wex_accounting_portal_search_domain(self, search_in=None, search=None):
        search = (search or "").strip()
        if not search:
            return []

        search_domains = {
            "number": [[("name", "ilike", search)], [("payment_reference", "ilike", search)], [("ref", "ilike", search)]],
            "partner": [[("partner_id.name", "ilike", search)]],
            "vat": [[("partner_id.vat", "ilike", search)]],
        }
        if search_in == "number":
            return expression.OR(search_domains["number"])
        if search_in == "partner":
            return search_domains["partner"][0]
        if search_in == "vat":
            return search_domains["vat"][0]
        return expression.OR(
            search_domains["number"] + search_domains["partner"] + search_domains["vat"]
        )

    @api.model
    def _get_wex_accounting_portal_domain(
        self,
        user,
        start_date=None,
        end_date=None,
        search_in=None,
        search=None,
        company_ids=None,
        scope=None,
        move_types=None,
    ):
        company_ids = self._get_wex_accounting_portal_company_ids(user, company_ids=company_ids)
        move_types = move_types or self._get_wex_accounting_portal_move_types(scope)
        return [
            ("company_id", "in", company_ids),
            ("move_type", "in", move_types),
            ("state", "not in", _WEX_PORTAL_EXCLUDED_STATES),
        ] + self._get_wex_accounting_portal_period_domain(
            start_date=start_date,
            end_date=end_date,
        ) + self._get_wex_accounting_portal_search_domain(search_in=search_in, search=search)

    @api.model
    def _get_wex_accounting_portal_order(self):
        return "invoice_date desc, create_date desc, id desc"

    @api.model
    def _get_wex_accounting_portal_records(
        self,
        user,
        limit=None,
        offset=0,
        start_date=None,
        end_date=None,
        search_in=None,
        search=None,
        company_ids=None,
        scope=None,
        move_types=None,
    ):
        return self.sudo().search(
            self._get_wex_accounting_portal_domain(
                user,
                start_date=start_date,
                end_date=end_date,
                search_in=search_in,
                search=search,
                company_ids=company_ids,
                scope=scope,
                move_types=move_types,
            ),
            order=self._get_wex_accounting_portal_order(),
            limit=limit,
            offset=offset,
        )

    @api.model
    def _get_wex_accounting_portal_count(
        self,
        user,
        start_date=None,
        end_date=None,
        search_in=None,
        search=None,
        company_ids=None,
        scope=None,
        move_types=None,
    ):
        return self.sudo().search_count(
            self._get_wex_accounting_portal_domain(
                user,
                start_date=start_date,
                end_date=end_date,
                search_in=search_in,
                search=search,
                company_ids=company_ids,
                scope=scope,
                move_types=move_types,
            )
        )

    @api.model
    def _get_wex_accounting_portal_summary_values(
        self,
        user,
        start_date=None,
        end_date=None,
        search_in=None,
        search=None,
        company_ids=None,
        scope=None,
    ):
        scope = self._get_wex_accounting_portal_scope(scope)
        main_move_type, refund_move_type = self._get_wex_accounting_portal_move_types(scope)
        domain = self._get_wex_accounting_portal_domain(
            user,
            start_date=start_date,
            end_date=end_date,
            search_in=search_in,
            search=search,
            company_ids=company_ids,
            scope=scope,
        )
        grouped = self.sudo().read_group(
            domain,
            ["amount_untaxed:sum", "amount_tax:sum", "amount_total:sum"],
            ["move_type"],
            lazy=False,
        )
        values_by_type = {
            group["move_type"]: {
                "amount_untaxed": abs(group.get("amount_untaxed", 0.0)),
                "amount_tax": abs(group.get("amount_tax", 0.0)),
                "amount_total": abs(group.get("amount_total", 0.0)),
                "count": group.get("__count", 0),
            }
            for group in grouped
        }
        main_values = values_by_type.get(main_move_type, {})
        refund_values = values_by_type.get(refund_move_type, {})
        invoice_untaxed_total = main_values.get("amount_untaxed", 0.0)
        refund_untaxed_total = refund_values.get("amount_untaxed", 0.0)
        invoice_tax_total = main_values.get("amount_tax", 0.0)
        refund_tax_total = refund_values.get("amount_tax", 0.0)
        invoice_total = main_values.get("amount_total", 0.0)
        refund_total = refund_values.get("amount_total", 0.0)
        outstanding_records = self.sudo().search(
            domain
            + [
                ("state", "=", "posted"),
                ("move_type", "=", main_move_type),
                ("payment_state", "not in", ("paid", "reversed")),
            ]
        )
        overdue_records = outstanding_records.filtered(
            lambda move: move.invoice_date_due and move.invoice_date_due < fields.Date.today()
        )
        return {
            "invoice_untaxed_total": invoice_untaxed_total,
            "refund_untaxed_total": refund_untaxed_total,
            "net_untaxed_total": invoice_untaxed_total - refund_untaxed_total,
            "invoice_tax_total": invoice_tax_total,
            "refund_tax_total": refund_tax_total,
            "net_tax_total": invoice_tax_total - refund_tax_total,
            "invoice_total": invoice_total,
            "refund_total": refund_total,
            "net_invoiced_total": invoice_total - refund_total,
            "invoice_count": main_values.get("count", 0),
            "refund_count": refund_values.get("count", 0),
            "document_count": main_values.get("count", 0) + refund_values.get("count", 0),
            "outstanding_total": sum(abs(move.amount_residual) for move in outstanding_records),
            "overdue_total": sum(abs(move.amount_residual) for move in overdue_records),
        }

    def _can_user_access_wex_accounting_portal_record(self, user):
        self.ensure_one()
        scope = "purchase" if self.move_type in self._get_wex_accounting_portal_move_types("purchase") else "sale"
        domain = self._get_wex_accounting_portal_domain(user, scope=scope) + [("id", "=", self.id)]
        return bool(self.sudo().search_count(domain))

    def _get_wex_accounting_portal_sort_datetime(self):
        self.ensure_one()
        sort_date = self.invoice_date or fields.Date.to_date(self.create_date)
        if not sort_date:
            return datetime.min
        return datetime.combine(sort_date, time.max)

    def _get_wex_accounting_portal_line_values(self):
        self.ensure_one()
        line_values = []
        for line in self.sudo().invoice_line_ids.filtered(lambda rec: not rec.display_type):
            line_values.append(
                {
                    "name": line.name or line.product_id.display_name or "-",
                    "quantity": line.quantity,
                    "price_unit": line.price_unit,
                    "price_subtotal": line.price_subtotal,
                    "price_total": line.price_total,
                    "currency": line.currency_id,
                    "product_name": line.product_id.display_name or "",
                }
            )
        return line_values

    def _get_wex_accounting_portal_payment_method_labels(self):
        self.ensure_one()
        widget = self.sudo().invoice_payments_widget
        if not widget:
            return []
        if isinstance(widget, str):
            try:
                widget = json.loads(widget)
            except json.JSONDecodeError:
                return []
        labels = []
        for content_item in widget.get("content", []):
            label = content_item.get("journal_name") or content_item.get("name")
            if label and label not in labels:
                labels.append(label)
        return labels

    def _get_wex_accounting_portal_payment_status_values(self):
        self.ensure_one()
        today = fields.Date.today()
        if self.payment_state == "partial":
            return {"code": "partial", "label": _("Parcialmente pagada")}
        if self.payment_state in ("paid", "reversed", "in_payment"):
            return {"code": "paid", "label": _("Pagada")}
        if self.invoice_date_due and self.invoice_date_due < today and self.state == "posted":
            return {"code": "overdue", "label": _("Vencida")}
        return {"code": "pending", "label": _("Pendiente")}

    def _get_wex_accounting_portal_list_item(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        scope = "purchase" if self.move_type in self._get_wex_accounting_portal_move_types("purchase") else "sale"
        move_type_labels = dict(self._fields["move_type"].selection)
        payment_status = self._get_wex_accounting_portal_payment_status_values()
        payment_method_labels = self._get_wex_accounting_portal_payment_method_labels()
        detail_url = f"{_WEX_PORTAL_BASE_URL}/invoices/{self.id}"
        return {
            "kind": "invoice",
            "scope": scope,
            "kind_label": _("Factura proveedor") if scope == "purchase" else _("Factura"),
            "document_label": move_type_labels.get(self.move_type, self.move_type or ""),
            "id": self.id,
            "name": self.name or self.payment_reference or _("Draft invoice"),
            "partner_name": self.partner_id.display_name or "-",
            "partner_vat": self.partner_id.vat or "-",
            "company_name": self.company_id.display_name or "-",
            "date": self.invoice_date,
            "due_date": self.invoice_date_due,
            "sort_datetime": self._get_wex_accounting_portal_sort_datetime(),
            "amount_untaxed": self.amount_untaxed,
            "amount_tax": self.amount_tax,
            "amount_total": self.amount_total,
            "amount_total_signed": self.amount_total_signed,
            "amount_due": abs(self.amount_residual),
            "amount_total_label": format_amount(self.env, self.amount_total, currency),
            "currency": currency,
            "signed_currency": self.company_currency_id or currency,
            "state": self.state,
            "state_label": dict(self._fields["state"].selection).get(self.state, self.state or ""),
            "payment_state": payment_status["code"],
            "payment_state_label": payment_status["label"],
            "payment_registered": self.payment_state in ("paid", "in_payment", "partial", "reversed"),
            "payment_method_labels": payment_method_labels,
            "payment_methods_label": ", ".join(payment_method_labels) if payment_method_labels else "-",
            "detail_url": detail_url,
            "pdf_url": f"{detail_url}/pdf",
        }

    def _get_wex_accounting_portal_detail_values(self, show_lines=False):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        scope = "purchase" if self.move_type in self._get_wex_accounting_portal_move_types("purchase") else "sale"
        move_type_labels = dict(self._fields["move_type"].selection)
        payment_status = self._get_wex_accounting_portal_payment_status_values()
        payment_method_labels = self._get_wex_accounting_portal_payment_method_labels()
        detail_url = f"{_WEX_PORTAL_BASE_URL}/invoices/{self.id}"
        return {
            "id": self.id,
            "kind": "invoice",
            "scope": scope,
            "name": self.name or self.payment_reference or _("Draft invoice"),
            "move_type": self.move_type,
            "move_type_label": move_type_labels.get(self.move_type, self.move_type or ""),
            "state": self.state,
            "state_label": dict(self._fields["state"].selection).get(self.state, self.state or ""),
            "partner_name": self.partner_id.display_name or "-",
            "partner_vat": self.partner_id.vat or "-",
            "company_name": self.company_id.display_name or "-",
            "invoice_date": self.invoice_date,
            "invoice_date_due": self.invoice_date_due,
            "invoice_origin": self.invoice_origin or "",
            "ref": self.ref or "",
            "payment_reference": self.payment_reference or "",
            "currency": currency,
            "amount_untaxed": self.amount_untaxed,
            "amount_tax": self.amount_tax,
            "amount_total": self.amount_total,
            "amount_residual": abs(self.amount_residual),
            "amount_untaxed_label": format_amount(self.env, self.amount_untaxed, currency),
            "amount_tax_label": format_amount(self.env, self.amount_tax, currency),
            "amount_total_label": format_amount(self.env, self.amount_total, currency),
            "amount_residual_label": format_amount(self.env, abs(self.amount_residual), currency),
            "payment_state": payment_status["code"],
            "payment_state_label": payment_status["label"],
            "payment_methods_label": ", ".join(payment_method_labels) if payment_method_labels else "-",
            "line_values": self._get_wex_accounting_portal_line_values(),
            "pdf_url": f"{detail_url}/pdf",
            "show_lines_url": f"{detail_url}?show_lines=1",
            "hide_lines_url": detail_url,
        }

    def _get_wex_accounting_portal_pdf_report(self):
        self.ensure_one()
        return self.env.ref("account.account_invoices", raise_if_not_found=False) or self.env.ref(
            "account.account_invoices_without_payment", raise_if_not_found=False
        )

    def _get_wex_accounting_portal_pdf_response_values(self, user):
        self.ensure_one()
        self._check_wex_accounting_portal_access(user)
        report = self.sudo()._get_wex_accounting_portal_pdf_report()
        if not report:
            raise MissingError(_("No invoice PDF report is configured in account."))

        pdf_content, _content_type = report.sudo()._render_qweb_pdf(self.sudo().ids)
        filename = f"{self.name or 'invoice'}.pdf"
        return {
            "content": pdf_content,
            "filename": filename,
            "mimetype": "application/pdf",
        }
