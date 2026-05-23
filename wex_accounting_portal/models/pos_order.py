from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.osv import expression
from odoo.tools import format_amount

_WEX_PORTAL_POS_STATES = ("paid", "done", "invoiced")
_WEX_PORTAL_BASE_URL = "/my/accounting"


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _check_wex_accounting_portal_access(self, user):
        self.ensure_one()
        if not self._can_user_access_wex_accounting_portal_record(user):
            raise AccessError(_("You cannot access this POS order from the Wex accounting portal."))

    @api.model
    def _get_wex_accounting_portal_period_domain(self, start_date=None, end_date=None):
        domain = []
        if start_date:
            start_dt = datetime.combine(start_date, time.min)
            domain.append(("date_order", ">=", fields.Datetime.to_string(start_dt)))
        if end_date:
            next_day_dt = datetime.combine(end_date + timedelta(days=1), time.min)
            domain.append(("date_order", "<", fields.Datetime.to_string(next_day_dt)))
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
            "number": [[("pos_reference", "ilike", search)], [("name", "ilike", search)]],
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
    def _get_wex_accounting_portal_partner_domain(self, partner_ids=None):
        if not partner_ids:
            return []
        return [("partner_id", "child_of", partner_ids)]

    @api.model
    def _get_wex_accounting_portal_state_domain(self, filter_state=None):
        if filter_state == "paid":
            return [("state", "in", _WEX_PORTAL_POS_STATES)]
        if filter_state in ("pending", "overdue"):
            return [("id", "=", 0)]
        return []

    @api.model
    def _get_wex_accounting_portal_domain(
        self,
        user,
        start_date=None,
        end_date=None,
        search_in=None,
        search=None,
        company_ids=None,
        filter_state=None,
        partner_ids=None,
    ):
        company_ids = self._get_wex_accounting_portal_company_ids(user, company_ids=company_ids)
        return [
            ("company_id", "in", company_ids),
            ("state", "in", _WEX_PORTAL_POS_STATES),
        ] + self._get_wex_accounting_portal_period_domain(
            start_date=start_date,
            end_date=end_date,
        ) + self._get_wex_accounting_portal_search_domain(
            search_in=search_in, search=search
        ) + self._get_wex_accounting_portal_state_domain(
            filter_state=filter_state
        ) + self._get_wex_accounting_portal_partner_domain(partner_ids=partner_ids)

    @api.model
    def _get_wex_accounting_portal_order(self):
        return "date_order desc, id desc"

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
        filter_state=None,
        partner_ids=None,
    ):
        return self.sudo().search(
            self._get_wex_accounting_portal_domain(
                user,
                start_date=start_date,
                end_date=end_date,
                search_in=search_in,
                search=search,
                company_ids=company_ids,
                filter_state=filter_state,
                partner_ids=partner_ids,
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
        filter_state=None,
        partner_ids=None,
    ):
        return self.sudo().search_count(
            self._get_wex_accounting_portal_domain(
                user,
                start_date=start_date,
                end_date=end_date,
                search_in=search_in,
                search=search,
                company_ids=company_ids,
                filter_state=filter_state,
                partner_ids=partner_ids,
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
        filter_state=None,
        partner_ids=None,
    ):
        domain = self._get_wex_accounting_portal_domain(
            user,
            start_date=start_date,
            end_date=end_date,
            search_in=search_in,
            search=search,
            company_ids=company_ids,
            filter_state=filter_state,
            partner_ids=partner_ids,
        )
        grouped = self.sudo().read_group(
            domain,
            ["amount_total:sum", "amount_tax:sum"],
            ["state"],
            lazy=False,
        )
        values_by_state = {
            group["state"]: {
                "amount_total": group.get("amount_total", 0.0),
                "amount_tax": group.get("amount_tax", 0.0),
                "count": group.get("__count", 0),
            }
            for group in grouped
        }
        paid_values = values_by_state.get("paid", {})
        done_values = values_by_state.get("done", {})
        invoiced_values = values_by_state.get("invoiced", {})
        uninvoiced_total = paid_values.get("amount_total", 0.0) + done_values.get("amount_total", 0.0)
        invoiced_total = invoiced_values.get("amount_total", 0.0)
        paid_tax_total = paid_values.get("amount_tax", 0.0)
        done_tax_total = done_values.get("amount_tax", 0.0)
        invoiced_tax_total = invoiced_values.get("amount_tax", 0.0)
        uninvoiced_tax_total = paid_tax_total + done_tax_total
        invoiced_untaxed_total = invoiced_total - invoiced_tax_total
        uninvoiced_untaxed_total = uninvoiced_total - uninvoiced_tax_total
        return {
            "pos_total": uninvoiced_total + invoiced_total,
            "pos_untaxed_total": uninvoiced_untaxed_total + invoiced_untaxed_total,
            "pos_tax_total": uninvoiced_tax_total + invoiced_tax_total,
            "pos_uninvoiced_total": uninvoiced_total,
            "pos_uninvoiced_untaxed_total": uninvoiced_untaxed_total,
            "pos_uninvoiced_tax_total": uninvoiced_tax_total,
            "pos_invoiced_total": invoiced_total,
            "pos_invoiced_untaxed_total": invoiced_untaxed_total,
            "pos_invoiced_tax_total": invoiced_tax_total,
            "pos_paid_count": paid_values.get("count", 0),
            "pos_done_count": done_values.get("count", 0),
            "pos_invoiced_count": invoiced_values.get("count", 0),
            "document_count": (
                paid_values.get("count", 0)
                + done_values.get("count", 0)
                + invoiced_values.get("count", 0)
            ),
        }

    @api.model
    def _get_wex_accounting_portal_timeseries(
        self,
        user,
        start_date=None,
        end_date=None,
        search_in=None,
        search=None,
        company_ids=None,
        filter_state=None,
        partner_ids=None,
        bucket="month",
    ):
        bucket = "day" if bucket == "day" else "month"
        records = self._get_wex_accounting_portal_records(
            user,
            start_date=start_date,
            end_date=end_date,
            search_in=search_in,
            search=search,
            company_ids=company_ids,
            filter_state=filter_state,
            partner_ids=partner_ids,
        )
        series_by_key = {}
        for order in records:
            order_dt = fields.Datetime.to_datetime(order.date_order)
            if not order_dt:
                continue
            if bucket == "day":
                key = order_dt.strftime("%Y-%m-%d")
                label = order_dt.strftime("%d/%m")
            else:
                key = order_dt.strftime("%Y-%m")
                label = order_dt.strftime("%m/%Y")
            series_item = series_by_key.setdefault(
                key,
                {
                    "key": key,
                    "label": label,
                    "uninvoiced_amount": 0.0,
                    "invoiced_amount": 0.0,
                    "amount": 0.0,
                    "count": 0,
                },
            )
            series_item["amount"] += order.amount_total
            series_item["count"] += 1
            if order.state == "invoiced":
                series_item["invoiced_amount"] += order.amount_total
            else:
                series_item["uninvoiced_amount"] += order.amount_total
        return [series_by_key[key] for key in sorted(series_by_key)]

    def _can_user_access_wex_accounting_portal_record(self, user):
        self.ensure_one()
        domain = self._get_wex_accounting_portal_domain(user) + [("id", "=", self.id)]
        return bool(self.sudo().search_count(domain))

    def _get_wex_accounting_portal_payment_method_labels(self):
        self.ensure_one()
        labels = []
        for payment in self.sudo().payment_ids:
            label = payment.payment_method_id.name
            if label and label not in labels:
                labels.append(label)
        return labels

    def _get_wex_accounting_portal_line_values(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        line_values = []
        for line in self.sudo().lines.filtered(lambda rec: not getattr(rec, "display_type", False)):
            line_values.append(
                {
                    "name": line.full_product_name or line.product_id.display_name or "-",
                    "quantity": line.qty,
                    "price_unit": line.price_unit,
                    "price_subtotal": line.price_subtotal,
                    "price_subtotal_incl": line.price_subtotal_incl,
                    "currency": currency,
                    "product_name": line.product_id.display_name or "",
                }
            )
        return line_values

    def _get_wex_accounting_portal_list_item(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        detail_url = f"{_WEX_PORTAL_BASE_URL}/pos/{self.id}"
        amount_untaxed = self.amount_total - self.amount_tax
        payment_state_labels = {
            "paid": _("Cobrada"),
            "done": _("Cobrada"),
            "invoiced": _("Facturada"),
        }
        payment_method_labels = self._get_wex_accounting_portal_payment_method_labels()
        return {
            "kind": "pos",
            "kind_label": _("POS"),
            "document_label": _("POS Sale"),
            "id": self.id,
            "partner_id": self.partner_id.commercial_partner_id.id or self.partner_id.id,
            "name": self.pos_reference or self.name or _("POS Order"),
            "partner_name": self.partner_id.display_name or "-",
            "partner_vat": self.partner_id.vat or "-",
            "company_name": self.company_id.display_name or "-",
            "date": self.date_order,
            "due_date": False,
            "sort_datetime": self.date_order or fields.Datetime.now(),
            "amount_untaxed": amount_untaxed,
            "amount_tax": self.amount_tax,
            "amount_total": self.amount_total,
            "amount_total_signed": self.amount_total,
            "amount_due": 0.0,
            "amount_total_label": format_amount(self.env, self.amount_total, currency),
            "currency": currency,
            "signed_currency": currency,
            "state": self.state,
            "state_label": dict(self._fields["state"].selection).get(self.state, self.state or ""),
            "payment_state": self.state,
            "payment_state_label": payment_state_labels.get(self.state, self.state or ""),
            "payment_registered": True,
            "payment_method_labels": payment_method_labels,
            "payment_methods_label": ", ".join(payment_method_labels) if payment_method_labels else "-",
            "detail_url": detail_url,
            "pdf_url": False,
        }

    def _get_wex_accounting_portal_detail_values(self, show_lines=False):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        detail_url = f"{_WEX_PORTAL_BASE_URL}/pos/{self.id}"
        payment_method_labels = self._get_wex_accounting_portal_payment_method_labels()
        return {
            "id": self.id,
            "kind": "pos",
            "name": self.pos_reference or self.name or _("POS Order"),
            "state": self.state,
            "state_label": dict(self._fields["state"].selection).get(self.state, self.state or ""),
            "partner_name": self.partner_id.display_name or "-",
            "partner_vat": self.partner_id.vat or "-",
            "company_name": self.company_id.display_name or "-",
            "date_order": self.date_order,
            "session_name": self.session_id.display_name or "",
            "currency": currency,
            "amount_untaxed": self.amount_total - self.amount_tax,
            "amount_tax": self.amount_tax,
            "amount_total": self.amount_total,
            "amount_due": 0.0,
            "payment_state_label": _("Cobrada")
            if self.state in ("paid", "done")
            else _("Facturada"),
            "payment_methods_label": ", ".join(payment_method_labels) if payment_method_labels else "-",
            "amount_untaxed_label": format_amount(self.env, self.amount_total - self.amount_tax, currency),
            "amount_tax_label": format_amount(self.env, self.amount_tax, currency),
            "amount_total_label": format_amount(self.env, self.amount_total, currency),
            "line_values": self._get_wex_accounting_portal_line_values(),
            "show_lines_url": f"{detail_url}?show_lines=1",
            "hide_lines_url": detail_url,
        }
