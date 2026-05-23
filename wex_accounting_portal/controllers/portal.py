import csv
import io
import logging
from datetime import timedelta

from urllib.parse import urlencode

from openpyxl import Workbook
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http, _, fields
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request

_logger = logging.getLogger(__name__)

_EXPORT_RECORD_LIMIT = 5_000
_PERIOD_KEYS = ("all", "day", "month", "quarter", "year", "custom")
_SEARCH_KEYS = ("all", "number", "partner", "vat")
_SECTION_KEYS = ("sales", "purchases")
_MONTH_LABELS = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


class WexAccountingPortal(CustomerPortal):
    def _has_wex_accounting_portal_access(self, user=None):
        user = user or request.env.user
        return bool(
            user
            and not user._is_public()
            and not user._is_internal()
            and user.has_group("base.group_portal")
            and user.has_group("wex_accounting_portal.group_wex_accounting_portal")
            and user.partner_id._is_wex_accounting_portal_enabled_partner()
        )

    def _check_accounting_portal_access(self):
        if not self._has_wex_accounting_portal_access():
            user = request.env.user
            _logger.warning(
                "wex_accounting_portal: access denied for user %s (id=%s, login=%s)",
                user.name,
                user.id,
                user.login,
            )
            raise Forbidden()

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user
        if not self._has_wex_accounting_portal_access(user):
            values["wex_accounting_portal_enabled"] = False
            return values

        invoice_model = request.env["account.move"]
        pos_model = request.env["pos.order"]
        if "wex_accounting_count" in counters:
            values["wex_accounting_count"] = (
                invoice_model._get_wex_accounting_portal_count(user, scope="sale")
                + invoice_model._get_wex_accounting_portal_count(user, scope="purchase")
                + pos_model._get_wex_accounting_portal_count(user)
            )
        values["wex_accounting_portal_enabled"] = True
        return values

    def _get_accounting_sections(self):
        return {
            "sales": {"label": _("Ventas"), "description": _("Facturación de cliente y POS")},
            "purchases": {"label": _("Compras"), "description": _("Facturas y abonos de proveedor")},
        }

    def _get_accounting_default_section(self):
        return "sales"

    def _get_accounting_section(self, value):
        return value if value in _SECTION_KEYS else self._get_accounting_default_section()

    def _get_accounting_searchbar_filters(self, section="sales"):
        if section == "purchases":
            return {
                "all": {"label": _("Todo")},
                "bill": {"label": _("Facturas proveedor")},
                "refund": {"label": _("Abonos proveedor")},
            }
        return {
            "all": {"label": _("Todo")},
            "invoice": {"label": _("Facturas")},
            "pos": {"label": _("POS")},
        }

    def _get_accounting_period_filters(self):
        return {
            "all": {"label": _("Todo el tiempo")},
            "day": {"label": _("Día")},
            "month": {"label": _("Mes")},
            "quarter": {"label": _("Trimestre")},
            "year": {"label": _("Año")},
            "custom": {"label": _("Rango personalizado")},
        }

    def _get_accounting_searchbar_inputs(self, section="sales"):
        partner_label = _("Proveedor") if section == "purchases" else _("Cliente")
        return {
            "all": {"label": _("Todos los campos")},
            "number": {"label": _("Número")},
            "partner": {"label": partner_label},
            "vat": {"label": _("NIF")},
        }

    def _get_accounting_portal_base_url(self):
        return "/my/accounting"

    def _get_accounting_filter_url_args(self, filterby, section=None):
        return {
            "filterby": filterby,
            "section": self._get_accounting_section(section or self._get_accounting_default_section()),
        }

    def _sanitize_year(self, value, default):
        try:
            year = int(value)
        except (TypeError, ValueError):
            return default
        return max(default - 10, min(default + 1, year))

    def _sanitize_month(self, value, default):
        try:
            month = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, min(12, month))

    def _sanitize_quarter(self, value, default):
        try:
            quarter = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, min(4, quarter))

    def _sanitize_day(self, value, default):
        if not value:
            return default
        try:
            parsed_day = fields.Date.to_date(value)
        except Exception:
            return default
        return parsed_day or default

    def _sanitize_search_term(self, value):
        return (value or "").strip()

    def _sanitize_company_id(self, value, user):
        try:
            company_id = int(value)
        except (TypeError, ValueError):
            return False
        allowed_company_ids = user.company_ids.ids or [user.company_id.id]
        return company_id if company_id in allowed_company_ids else False

    def _get_accounting_search_values(self, kw):
        search_in = kw.get("search_in") or "all"
        search_in = search_in if search_in in _SEARCH_KEYS else "all"
        return {
            "search_in": search_in,
            "search": self._sanitize_search_term(kw.get("search")),
        }

    def _get_accounting_company_values(self, user, kw):
        allowed_companies = user.company_ids or user.company_id
        selected_company_id = self._sanitize_company_id(kw.get("company_id"), user)
        selected_company_ids = (
            [selected_company_id] if selected_company_id else allowed_companies.ids
        )
        selected_company = selected_company_id and request.env["res.company"].browse(
            selected_company_id
        )
        company_options = [{"value": "all", "label": _("Todas las compañías")}]
        company_options.extend(
            {"value": company.id, "label": company.display_name}
            for company in allowed_companies
        )
        return {
            "selected_company_id": selected_company_id,
            "selected_company_ids": selected_company_ids,
            "selected_company_label": (
                selected_company.display_name
                if selected_company
                else ", ".join(allowed_companies.mapped("display_name"))
            ),
            "company_options": company_options,
        }

    def _get_accounting_query_args(
        self,
        section,
        filterby,
        period_values,
        search_values=None,
        company_values=None,
    ):
        args = self._get_accounting_filter_url_args(filterby, section=section) | self._get_accounting_period_url_args(
            period_values
        )
        search_values = search_values or {}
        company_values = company_values or {}
        if search_values.get("search"):
            args["search"] = search_values["search"]
        if search_values.get("search_in") and search_values["search_in"] != "all":
            args["search_in"] = search_values["search_in"]
        if company_values.get("selected_company_id"):
            args["company_id"] = company_values["selected_company_id"]
        return args

    def _get_accounting_period_values(self, kw):
        today = fields.Date.today()
        current_year = today.year
        current_quarter = ((today.month - 1) // 3) + 1
        period = kw.get("period") or "all"
        period = period if period in _PERIOD_KEYS else "all"
        year = self._sanitize_year(kw.get("year"), current_year)
        month = self._sanitize_month(kw.get("month"), today.month)
        quarter = self._sanitize_quarter(kw.get("quarter"), current_quarter)
        day = self._sanitize_day(kw.get("day"), today)
        custom_start = self._sanitize_day(kw.get("date_from"), today)
        custom_end = self._sanitize_day(kw.get("date_to"), custom_start)

        start_date = False
        end_date = False
        label = _("Todo el tiempo")
        if period == "day":
            start_date = day
            end_date = day
            label = day.strftime("%d/%m/%Y")
        elif period == "month":
            start_date = day.replace(year=year, month=month, day=1)
            if month == 12:
                end_date = start_date.replace(year=year + 1, month=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=month + 1) - timedelta(days=1)
            label = f"{_MONTH_LABELS[month]} {year}"
        elif period == "quarter":
            first_month = ((quarter - 1) * 3) + 1
            start_date = day.replace(year=year, month=first_month, day=1)
            if quarter == 4:
                end_date = start_date.replace(year=year + 1, month=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=first_month + 3) - timedelta(days=1)
            label = f"T{quarter} {year}"
        elif period == "year":
            start_date = day.replace(year=year, month=1, day=1)
            end_date = day.replace(year=year, month=12, day=31)
            label = str(year)
        elif period == "custom":
            start_date = custom_start or today
            end_date = custom_end or start_date
            if end_date < start_date:
                start_date, end_date = end_date, start_date
            label = "%s - %s" % (
                fields.Date.to_string(start_date),
                fields.Date.to_string(end_date),
            )

        return {
            "period": period,
            "year": year,
            "month": month,
            "quarter": quarter,
            "day": day,
            "date_from": start_date if period == "custom" else custom_start,
            "date_to": end_date if period == "custom" else custom_end,
            "start_date": start_date,
            "end_date": end_date,
            "label": label,
        }

    def _get_accounting_period_url_args(self, period_values):
        period = period_values["period"]
        args = {"period": period}
        if period == "day":
            args["day"] = fields.Date.to_string(period_values["day"])
        elif period == "month":
            args["year"] = period_values["year"]
            args["month"] = period_values["month"]
        elif period == "quarter":
            args["year"] = period_values["year"]
            args["quarter"] = period_values["quarter"]
        elif period == "year":
            args["year"] = period_values["year"]
        elif period == "custom":
            args["date_from"] = fields.Date.to_string(period_values["date_from"])
            args["date_to"] = fields.Date.to_string(period_values["date_to"])
        return args

    def _get_accounting_period_choice_args(self, period_key, period_values):
        today = fields.Date.today()
        args = {"period": period_key}
        if period_key == "day":
            args["day"] = fields.Date.to_string(period_values["day"] or today)
        elif period_key == "month":
            args["year"] = period_values["year"]
            args["month"] = period_values["month"]
        elif period_key == "quarter":
            args["year"] = period_values["year"]
            args["quarter"] = period_values["quarter"]
        elif period_key == "year":
            args["year"] = period_values["year"]
        elif period_key == "custom":
            args["date_from"] = fields.Date.to_string(period_values["date_from"])
            args["date_to"] = fields.Date.to_string(period_values["date_to"])
        return args

    def _get_accounting_selector_values(self, period_values):
        current_year = fields.Date.today().year
        year_options = [
            {"value": year, "label": str(year)}
            for year in range(current_year, current_year - 6, -1)
        ]
        month_options = [
            {"value": month_number, "label": month_label}
            for month_number, month_label in _MONTH_LABELS.items()
        ]
        quarter_options = [
            {"value": quarter_number, "label": f"T{quarter_number}"}
            for quarter_number in range(1, 5)
        ]
        return {
            "year_options": year_options,
            "month_options": month_options,
            "quarter_options": quarter_options,
            "selected_year": period_values["year"],
            "selected_month": period_values["month"],
            "selected_quarter": period_values["quarter"],
            "selected_day": fields.Date.to_string(period_values["day"]),
            "selected_date_from": fields.Date.to_string(period_values["date_from"]),
            "selected_date_to": fields.Date.to_string(period_values["date_to"]),
        }

    def _get_accounting_sales_dashboard_values(
        self,
        user,
        period_values,
        search_values=None,
        company_values=None,
    ):
        search_values = search_values or {}
        company_values = company_values or {}
        invoice_summary = request.env["account.move"]._get_wex_accounting_portal_summary_values(
            user,
            start_date=period_values["start_date"],
            end_date=period_values["end_date"],
            search_in=search_values.get("search_in"),
            search=search_values.get("search"),
            company_ids=company_values.get("selected_company_ids"),
        )
        pos_summary = request.env["pos.order"]._get_wex_accounting_portal_summary_values(
            user,
            start_date=period_values["start_date"],
            end_date=period_values["end_date"],
            search_in=search_values.get("search_in"),
            search=search_values.get("search"),
            company_ids=company_values.get("selected_company_ids"),
        )
        currency = user.company_id.currency_id
        return {
            "currency": currency,
            "period_label": period_values["label"],
            "company_label": company_values.get("selected_company_label") or user.company_id.display_name,
            "search_label": search_values.get("search") or "",
            "invoice_untaxed_total": invoice_summary["invoice_untaxed_total"],
            "refund_untaxed_total": invoice_summary["refund_untaxed_total"],
            "net_untaxed_total": invoice_summary["net_untaxed_total"],
            "invoice_tax_total": invoice_summary["invoice_tax_total"],
            "refund_tax_total": invoice_summary["refund_tax_total"],
            "net_tax_total": invoice_summary["net_tax_total"],
            "invoice_total": invoice_summary["invoice_total"],
            "refund_total": invoice_summary["refund_total"],
            "net_invoiced_total": invoice_summary["net_invoiced_total"],
            "pos_total": pos_summary["pos_total"],
            "pos_untaxed_total": pos_summary["pos_untaxed_total"],
            "pos_tax_total": pos_summary["pos_tax_total"],
            "pos_uninvoiced_total": pos_summary["pos_uninvoiced_total"],
            "pos_uninvoiced_untaxed_total": pos_summary["pos_uninvoiced_untaxed_total"],
            "pos_uninvoiced_tax_total": pos_summary["pos_uninvoiced_tax_total"],
            "pos_invoiced_total": pos_summary["pos_invoiced_total"],
            "pos_invoiced_untaxed_total": pos_summary["pos_invoiced_untaxed_total"],
            "pos_invoiced_tax_total": pos_summary["pos_invoiced_tax_total"],
            "operating_untaxed_total": (
                invoice_summary["net_untaxed_total"] + pos_summary["pos_uninvoiced_untaxed_total"]
            ),
            "operating_tax_total": (
                invoice_summary["net_tax_total"] + pos_summary["pos_uninvoiced_tax_total"]
            ),
            "operating_total": (
                invoice_summary["net_invoiced_total"] + pos_summary["pos_uninvoiced_total"]
            ),
            "vat_output_total": invoice_summary["net_tax_total"],
            "taxable_base_total": invoice_summary["net_untaxed_total"],
            "refund_vat_reduction_total": invoice_summary["refund_tax_total"],
            "outstanding_total": invoice_summary["outstanding_total"],
            "overdue_total": invoice_summary["overdue_total"],
            "document_count": (
                invoice_summary["document_count"] + pos_summary["document_count"]
            ),
            "invoice_count": invoice_summary["invoice_count"],
            "refund_count": invoice_summary["refund_count"],
            "pos_count": pos_summary["document_count"],
            "pos_invoiced_count": pos_summary["pos_invoiced_count"],
        }

    def _get_accounting_purchase_dashboard_values(
        self,
        user,
        period_values,
        search_values=None,
        company_values=None,
    ):
        search_values = search_values or {}
        company_values = company_values or {}
        purchase_summary = request.env["account.move"]._get_wex_accounting_portal_summary_values(
            user,
            start_date=period_values["start_date"],
            end_date=period_values["end_date"],
            search_in=search_values.get("search_in"),
            search=search_values.get("search"),
            company_ids=company_values.get("selected_company_ids"),
            scope="purchase",
        )
        currency = user.company_id.currency_id
        return {
            "currency": currency,
            "period_label": period_values["label"],
            "company_label": company_values.get("selected_company_label") or user.company_id.display_name,
            "search_label": search_values.get("search") or "",
            "purchase_untaxed_total": purchase_summary["invoice_untaxed_total"],
            "purchase_refund_untaxed_total": purchase_summary["refund_untaxed_total"],
            "net_purchase_untaxed_total": purchase_summary["net_untaxed_total"],
            "purchase_tax_total": purchase_summary["invoice_tax_total"],
            "purchase_refund_tax_total": purchase_summary["refund_tax_total"],
            "net_purchase_tax_total": purchase_summary["net_tax_total"],
            "purchase_total": purchase_summary["invoice_total"],
            "purchase_refund_total": purchase_summary["refund_total"],
            "net_purchase_total": purchase_summary["net_invoiced_total"],
            "outstanding_total": purchase_summary["outstanding_total"],
            "overdue_total": purchase_summary["overdue_total"],
            "taxable_base_total": purchase_summary["net_untaxed_total"],
            "vat_input_total": purchase_summary["net_tax_total"],
            "refund_vat_reduction_total": purchase_summary["refund_tax_total"],
            "bill_count": purchase_summary["invoice_count"],
            "refund_count": purchase_summary["refund_count"],
            "document_count": purchase_summary["document_count"],
        }

    def _get_accounting_hero_values(self, user, period_values, search_values=None, company_values=None):
        sales = self._get_accounting_sales_dashboard_values(
            user, period_values, search_values=search_values, company_values=company_values
        )
        purchases = self._get_accounting_purchase_dashboard_values(
            user, period_values, search_values=search_values, company_values=company_values
        )
        return {
            "sales": {
                "label": _("Ventas"),
                "description": _("Clientes y POS"),
                "total": sales["operating_total"],
                "secondary_one": sales["outstanding_total"],
                "secondary_one_label": _("Pendiente de cobro"),
                "secondary_two": sales["pos_uninvoiced_total"],
                "secondary_two_label": _("POS no facturado"),
            },
            "purchases": {
                "label": _("Compras"),
                "description": _("Facturas y abonos de proveedor"),
                "total": purchases["net_purchase_total"],
                "secondary_one": purchases["outstanding_total"],
                "secondary_one_label": _("Pendiente de pago"),
                "secondary_two": purchases["overdue_total"],
                "secondary_two_label": _("Vencido"),
            },
        }

    def _get_accounting_item_sort_key(self, item):
        return (item["sort_datetime"], item["id"], item["kind"])

    def _get_accounting_invoice_scope(self, section):
        return "purchase" if section == "purchases" else "sale"

    def _get_accounting_invoice_filter_keys(self, section):
        return ("all", "bill", "refund") if section == "purchases" else ("all", "invoice")

    def _get_accounting_move_types_for_filter(self, section, filterby):
        if section != "purchases":
            return None
        if filterby == "bill":
            return ("in_invoice",)
        if filterby == "refund":
            return ("in_refund",)
        return None

    def _get_accounting_export_headers(self, section="sales"):
        partner_label = "Proveedor" if section == "purchases" else "Cliente"
        return [
            "Número",
            partner_label,
            "NIF",
            "Fecha factura",
            "Vencimiento",
            "Base imponible",
            "Impuestos",
            "Total",
            "Total en moneda firmada",
            "Estado de pago",
        ]

    def _build_xlsx_content(self, rows, section="sales"):
        wb = Workbook()
        ws = wb.active
        ws.title = "Accounting"
        ws.append(self._get_accounting_export_headers(section=section))
        for row in rows:
            ws.append(
                [
                    row["number"],
                    row["customer"],
                    row["vat"],
                    row["invoice_date"],
                    row["due_date"],
                    row["untaxed_amount"],
                    row["taxes"],
                    row["total"],
                    row["signed_total"],
                    row["payment_status"],
                ]
            )
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.read()

    def _get_accounting_portal_page_records(
        self,
        user,
        section,
        filterby,
        offset,
        limit,
        start_date=None,
        end_date=None,
        search_in=None,
        search=None,
        company_ids=None,
    ):
        valid_filters = self._get_accounting_searchbar_filters(section=section)
        filterby = filterby if filterby in valid_filters else "all"
        fetch_limit = offset + limit
        items = []
        invoice_filters = self._get_accounting_invoice_filter_keys(section)
        scope = self._get_accounting_invoice_scope(section)
        move_types = self._get_accounting_move_types_for_filter(section, filterby)
        if filterby in invoice_filters:
            invoices = request.env["account.move"]._get_wex_accounting_portal_records(
                user,
                limit=fetch_limit,
                start_date=start_date,
                end_date=end_date,
                search_in=search_in,
                search=search,
                company_ids=company_ids,
                scope=scope,
                move_types=move_types,
            )
            items.extend(invoice._get_wex_accounting_portal_list_item() for invoice in invoices)
        if section == "sales" and filterby in ("all", "pos"):
            pos_orders = request.env["pos.order"]._get_wex_accounting_portal_records(
                user,
                limit=fetch_limit,
                start_date=start_date,
                end_date=end_date,
                search_in=search_in,
                search=search,
                company_ids=company_ids,
            )
            items.extend(order._get_wex_accounting_portal_list_item() for order in pos_orders)

        items.sort(key=self._get_accounting_item_sort_key, reverse=True)
        return items[offset : offset + limit]

    def _get_accounting_portal_total(
        self,
        user,
        section,
        filterby,
        start_date=None,
        end_date=None,
        search_in=None,
        search=None,
        company_ids=None,
    ):
        total = 0
        invoice_filters = self._get_accounting_invoice_filter_keys(section)
        scope = self._get_accounting_invoice_scope(section)
        move_types = self._get_accounting_move_types_for_filter(section, filterby)
        if filterby in invoice_filters:
            total += request.env["account.move"]._get_wex_accounting_portal_count(
                user,
                start_date=start_date,
                end_date=end_date,
                search_in=search_in,
                search=search,
                company_ids=company_ids,
                scope=scope,
                move_types=move_types,
            )
        if section == "sales" and filterby in ("all", "pos"):
            total += request.env["pos.order"]._get_wex_accounting_portal_count(
                user,
                start_date=start_date,
                end_date=end_date,
                search_in=search_in,
                search=search,
                company_ids=company_ids,
            )
        return total

    def _build_accounting_export_rows(
        self,
        user,
        section,
        filterby,
        start_date=None,
        end_date=None,
        search_in=None,
        search=None,
        company_ids=None,
    ):
        rows = []
        invoice_filters = self._get_accounting_invoice_filter_keys(section)
        scope = self._get_accounting_invoice_scope(section)
        move_types = self._get_accounting_move_types_for_filter(section, filterby)
        if filterby in invoice_filters:
            for move in request.env["account.move"]._get_wex_accounting_portal_records(
                user,
                limit=_EXPORT_RECORD_LIMIT,
                start_date=start_date,
                end_date=end_date,
                search_in=search_in,
                search=search,
                company_ids=company_ids,
                scope=scope,
                move_types=move_types,
            ):
                item = move._get_wex_accounting_portal_list_item()
                rows.append(
                    {
                        "number": item["name"],
                        "customer": item["partner_name"],
                        "vat": item["partner_vat"],
                        "invoice_date": (
                            fields.Date.to_string(item["date"]) if item["date"] else ""
                        ),
                        "due_date": (
                            fields.Date.to_string(item["due_date"]) if item["due_date"] else ""
                        ),
                        "untaxed_amount": item["amount_untaxed"],
                        "taxes": item["amount_tax"],
                        "total": item["amount_total"],
                        "signed_total": item["amount_total_signed"],
                        "payment_status": item["payment_state_label"],
                    }
                )
        if section == "sales" and filterby in ("all", "pos"):
            for order in request.env["pos.order"]._get_wex_accounting_portal_records(
                user,
                limit=_EXPORT_RECORD_LIMIT,
                start_date=start_date,
                end_date=end_date,
                search_in=search_in,
                search=search,
                company_ids=company_ids,
            ):
                item = order._get_wex_accounting_portal_list_item()
                rows.append(
                    {
                        "number": item["name"],
                        "customer": item["partner_name"],
                        "vat": item["partner_vat"],
                        "invoice_date": (
                            fields.Datetime.to_string(item["date"]) if item["date"] else ""
                        ),
                        "due_date": "",
                        "untaxed_amount": item["amount_untaxed"],
                        "taxes": item["amount_tax"],
                        "total": item["amount_total"],
                        "signed_total": item["amount_total_signed"],
                        "payment_status": item["payment_state_label"],
                    }
                )
        rows.sort(key=lambda row: (row["invoice_date"], row["number"]), reverse=True)
        return rows

    def _get_invoice_or_404(self, move_id):
        invoice = request.env["account.move"].sudo().browse(move_id).exists()
        if not invoice:
            raise NotFound()
        try:
            invoice._check_wex_accounting_portal_access(request.env.user)
        except Exception:
            user = request.env.user
            _logger.warning(
                "wex_accounting_portal: user %s (id=%s) denied access to invoice id=%s",
                user.login,
                user.id,
                move_id,
            )
            raise
        return invoice

    def _get_pos_order_or_404(self, order_id):
        order = request.env["pos.order"].sudo().browse(order_id).exists()
        if not order:
            raise NotFound()
        try:
            order._check_wex_accounting_portal_access(request.env.user)
        except Exception:
            user = request.env.user
            _logger.warning(
                "wex_accounting_portal: user %s (id=%s) denied access to pos.order id=%s",
                user.login,
                user.id,
                order_id,
            )
            raise
        return order

    @http.route(
        ["/my/accounting", "/my/accounting/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_accounting(self, page=1, filterby="all", section="sales", **kw):
        self._check_accounting_portal_access()
        values = self._prepare_portal_layout_values()
        section = self._get_accounting_section(section or kw.get("section"))
        filters = self._get_accounting_searchbar_filters(section=section)
        sections = self._get_accounting_sections()
        searchbar_inputs = self._get_accounting_searchbar_inputs(section=section)
        period_filters = self._get_accounting_period_filters()
        period_values = self._get_accounting_period_values(kw)
        filterby = filterby if filterby in filters else "all"
        user = request.env.user
        search_values = self._get_accounting_search_values(kw)
        company_values = self._get_accounting_company_values(user, kw)
        selector_values = self._get_accounting_selector_values(period_values)
        base_url = self._get_accounting_portal_base_url()
        url_args = self._get_accounting_query_args(
            section,
            filterby,
            period_values,
            search_values=search_values,
            company_values=company_values,
        )

        for section_key, section_data in sections.items():
            section_data["url"] = "%s?%s" % (
                base_url,
                urlencode(
                    self._get_accounting_query_args(
                        section_key,
                        "all",
                        period_values,
                        search_values=search_values,
                        company_values=company_values,
                    )
                ),
            )

        for filter_key, filter_data in filters.items():
            filter_data["url"] = "%s?%s" % (
                base_url,
                urlencode(
                    self._get_accounting_query_args(
                        section,
                        filter_key,
                        period_values,
                        search_values=search_values,
                        company_values=company_values,
                    )
                ),
            )

        for period_key, period_data in period_filters.items():
            period_data["url"] = "%s?%s" % (
                base_url,
                urlencode(
                    self._get_accounting_filter_url_args(filterby, section=section)
                    | self._get_accounting_period_choice_args(period_key, period_values)
                    | (
                        {"search": search_values["search"]}
                        if search_values["search"]
                        else {}
                    )
                    | (
                        {"search_in": search_values["search_in"]}
                        if search_values["search_in"] != "all"
                        else {}
                    )
                    | (
                        {"company_id": company_values["selected_company_id"]}
                        if company_values["selected_company_id"]
                        else {}
                    )
                ),
            )

        total = self._get_accounting_portal_total(
            user,
            section,
            filterby,
            start_date=period_values["start_date"],
            end_date=period_values["end_date"],
            search_in=search_values["search_in"],
            search=search_values["search"],
            company_ids=company_values["selected_company_ids"],
        )
        pager = portal_pager(
            url=base_url,
            url_args=url_args,
            total=total,
            page=page,
            step=self._items_per_page,
        )
        items = self._get_accounting_portal_page_records(
            user=user,
            section=section,
            filterby=filterby,
            offset=pager["offset"],
            limit=self._items_per_page,
            start_date=period_values["start_date"],
            end_date=period_values["end_date"],
            search_in=search_values["search_in"],
            search=search_values["search"],
            company_ids=company_values["selected_company_ids"],
        )
        sales_dashboard = self._get_accounting_sales_dashboard_values(
            user, period_values, search_values=search_values, company_values=company_values
        )
        purchase_dashboard = self._get_accounting_purchase_dashboard_values(
            user, period_values, search_values=search_values, company_values=company_values
        )
        dashboard_values = sales_dashboard if section == "sales" else purchase_dashboard
        hero_values = self._get_accounting_hero_values(
            user, period_values, search_values=search_values, company_values=company_values
        )
        section_ui = {
            "partner_label": _("Proveedor") if section == "purchases" else _("Cliente"),
            "partner_plural_label": _("Proveedores") if section == "purchases" else _("Clientes"),
            "document_date_label": _("Fecha factura"),
            "payment_due_label": _("Pendiente de pago") if section == "purchases" else _("Pendiente de cobro"),
            "table_title": _("Detalle de compras") if section == "purchases" else _("Detalle de ventas"),
            "summary_title": _("Resumen de compras") if section == "purchases" else _("Resumen de ventas"),
        }
        values.update(
            {
                "page_name": "wex_accounting_portal",
                "accounting_portal_url": base_url,
                "default_url": base_url,
                "pager": pager,
                "items": items,
                "section": section,
                "sections": sections,
                "filterby": filterby,
                "searchbar_filters": filters,
                "searchbar_inputs": searchbar_inputs,
                "search_in": search_values["search_in"],
                "search": search_values["search"],
                "period_filters": period_filters,
                "period_values": period_values,
                "selector_values": selector_values,
                "company_values": company_values,
                "hero": hero_values,
                "dashboard": dashboard_values,
                "section_ui": section_ui,
                "period_form_url": base_url,
                "search_form_url": base_url,
                "csv_export_url": "/my/accounting/export/csv?%s" % urlencode(url_args),
                "xlsx_export_url": "/my/accounting/export/xlsx?%s" % urlencode(url_args),
            }
        )
        return request.render("wex_accounting_portal.portal_my_accounting", values)

    @http.route(
        ["/my/accounting/invoices/<int:move_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_accounting_invoice_detail(self, move_id, show_lines=0, **kw):
        self._check_accounting_portal_access()
        invoice = self._get_invoice_or_404(move_id)
        values = self._prepare_portal_layout_values()
        show = str(show_lines).lower() in ("1", "true", "yes")
        values.update(
            {
                "page_name": "wex_accounting_invoice_detail",
                "accounting_portal_url": self._get_accounting_portal_base_url(),
                "document": invoice._get_wex_accounting_portal_detail_values(show_lines=show),
                "show_lines": show,
            }
        )
        return request.render("wex_accounting_portal.portal_accounting_invoice_detail", values)

    @http.route(
        ["/my/accounting/pos/<int:order_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_accounting_pos_detail(self, order_id, show_lines=0, **kw):
        self._check_accounting_portal_access()
        order = self._get_pos_order_or_404(order_id)
        values = self._prepare_portal_layout_values()
        show = str(show_lines).lower() in ("1", "true", "yes")
        values.update(
            {
                "page_name": "wex_accounting_pos_detail",
                "accounting_portal_url": self._get_accounting_portal_base_url(),
                "document": order._get_wex_accounting_portal_detail_values(show_lines=show),
                "show_lines": show,
            }
        )
        return request.render("wex_accounting_portal.portal_accounting_pos_detail", values)

    @http.route(
        ["/my/accounting/invoices/<int:move_id>/pdf"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_accounting_invoice_pdf(self, move_id, **kw):
        self._check_accounting_portal_access()
        invoice = self._get_invoice_or_404(move_id)
        pdf_values = invoice._get_wex_accounting_portal_pdf_response_values(request.env.user)
        headers = [
            ("Content-Type", pdf_values["mimetype"]),
            ("Content-Disposition", f"attachment; filename=\"{pdf_values['filename']}\""),
            ("Cache-Control", "private, no-store, max-age=0"),
            ("X-Content-Type-Options", "nosniff"),
        ]
        return request.make_response(pdf_values["content"], headers=headers)

    @http.route(
        ["/my/accounting/export/csv"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_accounting_export_csv(self, filterby="all", **kw):
        self._check_accounting_portal_access()
        section = self._get_accounting_section(kw.get("section"))
        filterby = filterby if filterby in self._get_accounting_searchbar_filters(section=section) else "all"
        period_values = self._get_accounting_period_values(kw)
        search_values = self._get_accounting_search_values(kw)
        company_values = self._get_accounting_company_values(request.env.user, kw)
        rows = self._build_accounting_export_rows(
            request.env.user,
            section,
            filterby,
            start_date=period_values["start_date"],
            end_date=period_values["end_date"],
            search_in=search_values["search_in"],
            search=search_values["search"],
            company_ids=company_values["selected_company_ids"],
        )
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(self._get_accounting_export_headers(section=section))
        for row in rows:
            writer.writerow(
                [
                    row["number"],
                    row["customer"],
                    row["vat"],
                    row["invoice_date"],
                    row["due_date"],
                    row["untaxed_amount"],
                    row["taxes"],
                    row["total"],
                    row["signed_total"],
                    row["payment_status"],
                ]
            )
        headers = [
            ("Content-Type", "text/csv; charset=utf-8"),
            ("Content-Disposition", "attachment; filename=\"wex_accounting_portal.csv\""),
        ]
        return request.make_response(buffer.getvalue().encode("utf-8"), headers=headers)

    @http.route(
        ["/my/accounting/export/xlsx"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_accounting_export_xlsx(self, filterby="all", **kw):
        self._check_accounting_portal_access()
        section = self._get_accounting_section(kw.get("section"))
        filterby = filterby if filterby in self._get_accounting_searchbar_filters(section=section) else "all"
        period_values = self._get_accounting_period_values(kw)
        search_values = self._get_accounting_search_values(kw)
        company_values = self._get_accounting_company_values(request.env.user, kw)
        rows = self._build_accounting_export_rows(
            request.env.user,
            section,
            filterby,
            start_date=period_values["start_date"],
            end_date=period_values["end_date"],
            search_in=search_values["search_in"],
            search=search_values["search"],
            company_ids=company_values["selected_company_ids"],
        )
        xlsx_content = self._build_xlsx_content(rows, section=section)

        response_headers = [
            (
                "Content-Type",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            ("Content-Disposition", "attachment; filename=\"wex_accounting_portal.xlsx\""),
        ]
        return request.make_response(xlsx_content, headers=response_headers)
