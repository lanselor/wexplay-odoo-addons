from odoo import fields, models, tools


class WexAccountingDashboardReport(models.Model):
    _name = "wex.accounting.dashboard.report"
    _description = "Wex Accounting Dashboard Report"
    _auto = False
    _rec_name = "name"
    _order = "document_date desc, id desc"

    name = fields.Char(readonly=True)
    source_kind = fields.Selection(
        [
            ("invoice", "Factura"),
            ("refund", "Abono"),
            ("pos", "POS"),
        ],
        readonly=True,
    )
    source_record_id = fields.Integer(readonly=True)
    move_id = fields.Many2one("account.move", readonly=True)
    pos_order_id = fields.Many2one("pos.order", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    partner_id = fields.Many2one("res.partner", readonly=True)
    user_id = fields.Many2one("res.users", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    company_currency_id = fields.Many2one("res.currency", readonly=True)
    partner_vat = fields.Char(readonly=True)
    document_date = fields.Date(readonly=True)
    due_date = fields.Date(readonly=True)
    state = fields.Char(readonly=True)
    payment_status = fields.Selection(
        [
            ("paid", "Pagada"),
            ("partial", "Parcialmente pagada"),
            ("pending", "Pendiente"),
            ("overdue", "Vencida"),
            ("invoiced", "Facturada"),
        ],
        readonly=True,
    )
    pos_invoice_status = fields.Selection(
        [
            ("uninvoiced", "POS no facturado"),
            ("invoiced", "POS facturado"),
        ],
        readonly=True,
    )
    amount_untaxed = fields.Monetary(currency_field="currency_id", readonly=True)
    amount_tax = fields.Monetary(currency_field="currency_id", readonly=True)
    amount_total = fields.Monetary(currency_field="currency_id", readonly=True)
    amount_total_signed = fields.Monetary(
        currency_field="company_currency_id",
        readonly=True,
    )
    operating_total_signed = fields.Monetary(
        currency_field="company_currency_id",
        readonly=True,
    )
    pos_uninvoiced_amount = fields.Monetary(
        currency_field="company_currency_id",
        readonly=True,
    )
    pos_invoiced_amount = fields.Monetary(
        currency_field="company_currency_id",
        readonly=True,
    )
    pending_amount = fields.Monetary(
        currency_field="company_currency_id",
        readonly=True,
    )
    overdue_amount = fields.Monetary(
        currency_field="company_currency_id",
        readonly=True,
    )
    taxable_base_amount = fields.Monetary(
        currency_field="company_currency_id",
        readonly=True,
    )
    vat_output_amount = fields.Monetary(
        currency_field="company_currency_id",
        readonly=True,
    )
    refund_vat_reduction_amount = fields.Monetary(
        currency_field="company_currency_id",
        readonly=True,
    )
    row_count = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    move.id AS id,
                    COALESCE(move.name, move.payment_reference, '/') AS name,
                    CASE
                        WHEN move.move_type = 'out_refund' THEN 'refund'
                        ELSE 'invoice'
                    END AS source_kind,
                    move.id AS source_record_id,
                    move.id AS move_id,
                    NULL::integer AS pos_order_id,
                    move.company_id AS company_id,
                    move.partner_id AS partner_id,
                    move.invoice_user_id AS user_id,
                    COALESCE(move.currency_id, company.currency_id) AS currency_id,
                    company.currency_id AS company_currency_id,
                    partner_commercial.vat AS partner_vat,
                    move.invoice_date AS document_date,
                    move.invoice_date_due AS due_date,
                    move.state AS state,
                    CASE
                        WHEN move.payment_state = 'partial' THEN 'partial'
                        WHEN move.payment_state IN ('paid', 'reversed', 'in_payment') THEN 'paid'
                        WHEN move.invoice_date_due IS NOT NULL
                             AND move.invoice_date_due < CURRENT_DATE
                             AND move.state = 'posted' THEN 'overdue'
                        ELSE 'pending'
                    END AS payment_status,
                    NULL::varchar AS pos_invoice_status,
                    ABS(COALESCE(move.amount_untaxed, 0.0)) AS amount_untaxed,
                    ABS(COALESCE(move.amount_tax, 0.0)) AS amount_tax,
                    ABS(COALESCE(move.amount_total, 0.0)) AS amount_total,
                    CASE
                        WHEN move.move_type = 'out_refund' THEN -ABS(COALESCE(move.amount_total_signed, move.amount_total, 0.0))
                        ELSE ABS(COALESCE(move.amount_total_signed, move.amount_total, 0.0))
                    END AS amount_total_signed,
                    CASE
                        WHEN move.move_type = 'out_refund' THEN -ABS(COALESCE(move.amount_total_signed, move.amount_total, 0.0))
                        ELSE ABS(COALESCE(move.amount_total_signed, move.amount_total, 0.0))
                    END AS operating_total_signed,
                    0.0 AS pos_uninvoiced_amount,
                    0.0 AS pos_invoiced_amount,
                    ABS(
                        CASE
                            WHEN move.payment_state NOT IN ('paid', 'reversed')
                            THEN COALESCE(move.amount_residual, 0.0)
                            ELSE 0.0
                        END
                    ) AS pending_amount,
                    ABS(
                        CASE
                            WHEN move.invoice_date_due IS NOT NULL
                                 AND move.invoice_date_due < CURRENT_DATE
                                 AND move.state = 'posted'
                                 AND move.payment_state NOT IN ('paid', 'reversed', 'in_payment')
                            THEN COALESCE(move.amount_residual, 0.0)
                            ELSE 0.0
                        END
                    ) AS overdue_amount,
                    CASE
                        WHEN move.move_type = 'out_refund' THEN -ABS(COALESCE(move.amount_untaxed_signed, move.amount_untaxed, 0.0))
                        ELSE ABS(COALESCE(move.amount_untaxed_signed, move.amount_untaxed, 0.0))
                    END AS taxable_base_amount,
                    CASE
                        WHEN move.move_type = 'out_refund' THEN -ABS(COALESCE(move.amount_tax_signed, move.amount_tax, 0.0))
                        ELSE ABS(COALESCE(move.amount_tax_signed, move.amount_tax, 0.0))
                    END AS vat_output_amount,
                    CASE
                        WHEN move.move_type = 'out_refund' THEN ABS(COALESCE(move.amount_tax_signed, move.amount_tax, 0.0))
                        ELSE 0.0
                    END AS refund_vat_reduction_amount,
                    1 AS row_count
                FROM account_move move
                JOIN res_company company ON company.id = move.company_id
                LEFT JOIN res_partner partner ON partner.id = move.partner_id
                LEFT JOIN res_partner partner_commercial ON partner_commercial.id = partner.commercial_partner_id
                WHERE move.move_type IN ('out_invoice', 'out_refund')
                  AND move.state != 'cancel'

                UNION ALL

                SELECT
                    1000000000 + pos.id AS id,
                    COALESCE(pos.pos_reference, pos.name, '/') AS name,
                    'pos' AS source_kind,
                    pos.id AS source_record_id,
                    NULL::integer AS move_id,
                    pos.id AS pos_order_id,
                    pos.company_id AS company_id,
                    pos.partner_id AS partner_id,
                    pos.user_id AS user_id,
                    company.currency_id AS currency_id,
                    company.currency_id AS company_currency_id,
                    partner_commercial.vat AS partner_vat,
                    pos.date_order::date AS document_date,
                    NULL::date AS due_date,
                    pos.state AS state,
                    CASE
                        WHEN pos.state = 'invoiced' THEN 'invoiced'
                        ELSE 'paid'
                    END AS payment_status,
                    CASE
                        WHEN pos.state = 'invoiced' THEN 'invoiced'
                        ELSE 'uninvoiced'
                    END AS pos_invoice_status,
                    COALESCE(pos.amount_total, 0.0) - COALESCE(pos.amount_tax, 0.0) AS amount_untaxed,
                    COALESCE(pos.amount_tax, 0.0) AS amount_tax,
                    COALESCE(pos.amount_total, 0.0) AS amount_total,
                    COALESCE(pos.amount_total, 0.0) AS amount_total_signed,
                    CASE
                        WHEN pos.state IN ('paid', 'done') THEN COALESCE(pos.amount_total, 0.0)
                        ELSE 0.0
                    END AS operating_total_signed,
                    CASE
                        WHEN pos.state IN ('paid', 'done') THEN COALESCE(pos.amount_total, 0.0)
                        ELSE 0.0
                    END AS pos_uninvoiced_amount,
                    CASE
                        WHEN pos.state = 'invoiced' THEN COALESCE(pos.amount_total, 0.0)
                        ELSE 0.0
                    END AS pos_invoiced_amount,
                    0.0 AS pending_amount,
                    0.0 AS overdue_amount,
                    0.0 AS taxable_base_amount,
                    0.0 AS vat_output_amount,
                    0.0 AS refund_vat_reduction_amount,
                    1 AS row_count
                FROM pos_order pos
                JOIN res_company company ON company.id = pos.company_id
                LEFT JOIN res_partner partner ON partner.id = pos.partner_id
                LEFT JOIN res_partner partner_commercial ON partner_commercial.id = partner.commercial_partner_id
                WHERE pos.state IN ('paid', 'done', 'invoiced')
            )
            """
        )
