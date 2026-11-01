import base64
import json
import re

import requests

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import AccessError, ValidationError

from .. import const, utils


class RefundProvider(models.Model):
    _inherit = 'payment.provider'

    @api.depends('code')
    def _compute_feature_support_fields(self):
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == const.PROVIDER_CODE).support_refund = 'partial'


class RefundTransaction(models.Model):
    _inherit = 'payment.transaction'

    redsys_environment = fields.Selection([('test', 'Test'), ('enabled', 'Production')], readonly=True, copy=False)
    redsys_original_merchant = fields.Char(readonly=True, copy=False)
    redsys_original_terminal = fields.Char(readonly=True, copy=False)
    redsys_refund_dispatch = fields.Selection([
        ('queued', 'Queued'), ('sent', 'Sent / check result'), ('resolved', 'Resolved'),
    ], readonly=True, copy=False)
    redsys_refund_evidence = fields.Text(string='Bank verification evidence', copy=False,
                                        groups='wex_payment_redsys.group_refund_operator')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            provider = self.env['payment.provider'].browse(vals.get('provider_id'))
            if provider.code == const.PROVIDER_CODE:
                if vals.get('operation') == 'refund':
                    self._redsys_check_refund_operator()
                    vals['redsys_refund_dispatch'] = False
                else:
                    vals['redsys_environment'] = provider.state if provider.state in ('test', 'enabled') else False
                    vals['redsys_original_merchant'] = provider.redsys_merchant_code
                    vals['redsys_original_terminal'] = provider.redsys_terminal
        return super().create(vals_list)

    def write(self, vals):
        if {'redsys_environment', 'redsys_original_merchant', 'redsys_original_terminal', 'redsys_refund_dispatch'} & vals.keys() and not self.env.su:
            raise AccessError(_('Redsys dispatch metadata cannot be edited manually.'))
        return super().write(vals)

    @api.constrains('operation', 'source_transaction_id', 'amount', 'currency_id', 'provider_id', 'partner_id')
    def _redsys_check_refund_source(self):
        for tx in self.filtered(lambda t: t.provider_code == const.PROVIDER_CODE and t.operation == 'refund'):
            source = tx.source_transaction_id
            if (not source or source.operation != 'online_redirect' or tx.amount >= 0 or
                    tx.currency_id != source.currency_id or tx.provider_id != source.provider_id or
                    tx.partner_id != source.partner_id):
                raise ValidationError(_('Invalid Redsys refund source or amount.'))

    def _redsys_check_refund_operator(self):
        if not (self.env.user.has_group('account.group_account_manager') and
                self.env.user.has_group('wex_payment_redsys.group_refund_operator')):
            raise AccessError(_('Accounting manager and Redsys refund permission are required.'))

    def _redsys_check_refund_allowed(self, amount):
        self.ensure_one()
        self._redsys_check_refund_operator()
        self.check_access('write')
        self.env.cr.execute('SELECT id FROM payment_transaction WHERE id = %s FOR UPDATE', [self.id])
        self.invalidate_recordset()
        if (self.state != 'done' or self.operation != 'online_redirect' or not self.payment_id
                or not self.redsys_environment or self.redsys_environment != self.provider_id.state):
            raise ValidationError(_('A confirmed payment in its verified original environment is required.'))
        if self.child_transaction_ids.filtered(lambda t: t.operation == 'refund' and (
                t.state in ('draft', 'pending', 'authorized') or (t.state == 'done' and not t.payment_id))):
            raise ValidationError(_('Resolve the pending refund before requesting another.'))
        self.payment_id.invalidate_recordset(['amount_available_for_refund'])
        available = self.payment_id.amount_available_for_refund
        if self.currency_id.compare_amounts(amount, 0) <= 0 or self.currency_id.compare_amounts(amount, available) > 0:
            raise ValidationError(_('Refund amount exceeds the available balance or is not positive.'))

    def _send_refund_request(self, amount_to_refund=None):
        if self.provider_code != const.PROVIDER_CODE:
            return super()._send_refund_request(amount_to_refund)
        amount = self.amount if amount_to_refund is None else amount_to_refund
        self._redsys_check_refund_allowed(amount)
        refund = super()._send_refund_request(amount)
        refund.sudo().write({'redsys_environment': self.redsys_environment, 'redsys_refund_dispatch': 'queued'})
        refund._set_pending(state_message=_('Refund queued; no bank request has been sent yet.'))
        self.env.ref('wex_payment_redsys.refund_cron').sudo()._trigger()
        return refund

    def _redsys_refund_payload(self):
        self.ensure_one()
        source = self.source_transaction_id
        provider = self.provider_id
        if (self.operation != 'refund' or not source or self.amount >= 0 or
                source.state != 'done' or self.redsys_environment != provider.state or
                source.redsys_original_merchant != provider.redsys_merchant_code or
                source.redsys_original_terminal != provider.redsys_terminal):
            raise ValidationError(_('Refund environment or source is invalid.'))
        params = {
            'DS_MERCHANT_ORDER': source.reference,
            'DS_MERCHANT_AMOUNT': str(abs(int(self._redsys_get_amount()))),
            'DS_MERCHANT_CURRENCY': '978', 'DS_MERCHANT_TRANSACTIONTYPE': '3',
            'DS_MERCHANT_MERCHANTCODE': provider.redsys_merchant_code,
            'DS_MERCHANT_TERMINAL': provider.redsys_terminal,
        }
        encoded = base64.b64encode(json.dumps(params, separators=(',', ':')).encode()).decode()
        return {'Ds_MerchantParameters': encoded, 'Ds_SignatureVersion': const.SIGNATURE_VERSION,
                'Ds_Signature': utils._sign_parameters(provider.sudo().redsys_secret_key, source.reference, encoded)}

    def _redsys_apply_refund_response(self, data):
        self.ensure_one()
        source = self.source_transaction_id
        encoded = data.get('Ds_MerchantParameters')
        params = utils._decode_parameters(encoded)
        if (data.get('Ds_SignatureVersion') != const.SIGNATURE_VERSION or not utils._verify_signature(
                self.provider_id.sudo().redsys_secret_key, source.reference, encoded, data.get('Ds_Signature'))):
            raise ValueError('Invalid refund signature')
        expected = {'Ds_Order': source.reference, 'Ds_Amount': str(abs(int(self._redsys_get_amount()))),
                    'Ds_Currency': '978', 'Ds_TransactionType': '3',
                    'Ds_MerchantCode': self.provider_id.redsys_merchant_code}
        if (any(params.get(k) != v for k, v in expected.items()) or
                params.get('Ds_Terminal', '').lstrip('0') != self.provider_id.redsys_terminal.lstrip('0') or
                not re.fullmatch(r'[0-9]{4}', params.get('Ds_Response', ''))):
            raise ValueError('Invalid refund result')
        if params['Ds_Response'] == '0900':
            self._set_done()
        else:
            self._set_error(_('Redsys rejected the refund (code %s).', params['Ds_Response']))
        self.redsys_refund_dispatch = 'resolved'
        self.env.ref('payment.cron_post_process_payment_tx')._trigger()

    @api.model
    def _cron_redsys_refunds(self):
        # Cursor propio: persistir el envío ANTES del efecto bancario irreversible.
        with self.env.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            cr.execute("SELECT id FROM payment_transaction WHERE redsys_refund_dispatch = 'queued' AND state = 'pending' ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1")
            row = cr.fetchone()
            if not row:
                return
            tx = env['payment.transaction'].browse(row[0])
            payload = tx._redsys_refund_payload()
            url = const.API_URLS[tx.redsys_environment].replace('/realizarPago', '/rest/trataPeticionREST')
            tx.redsys_refund_dispatch = 'sent'
            tx.state_message = _('Sent or uncertain. Do not resend; verify in Canales if no result arrives.')
            cr.commit()
            try:
                response = requests.post(url, json=payload, timeout=(5, 20), allow_redirects=False)
                response.raise_for_status()
                if len(response.content) > 24576:
                    raise ValueError('Oversized result')
                with cr.savepoint():
                    tx._redsys_apply_refund_response(response.json())
                cr.commit()
            except (requests.RequestException, ValueError, ValidationError):
                cr.rollback()
                # 'sent' ya está confirmado. Nunca volver a enviar por timeout/firma inválida.

    def action_redsys_verify_environment(self):
        self.ensure_one()
        self._redsys_check_refund_operator()
        self.check_access('write')
        if self.operation != 'online_redirect' or self.redsys_environment or not self.redsys_refund_evidence:
            raise ValidationError(_('For a legacy payment, record Canales evidence before verifying its environment.'))
        if self.provider_id.state not in ('test', 'enabled'):
            raise ValidationError(_('Select the verified provider environment first.'))
        self.sudo().write({'redsys_environment': self.provider_id.state,
                           'redsys_original_merchant': self.provider_id.redsys_merchant_code,
                           'redsys_original_terminal': self.provider_id.redsys_terminal})
        self._log_message_on_linked_documents(_('Original environment verified by %s: %s', self.env.user.name, self.redsys_refund_evidence))

    def _redsys_resolve_refund(self, successful):
        self.ensure_one()
        self._redsys_check_refund_operator()
        self.check_access('write')
        self.env.cr.execute('SELECT id FROM payment_transaction WHERE id = %s FOR UPDATE', [self.id])
        self.invalidate_recordset()
        if self.redsys_refund_dispatch != 'sent' or self.state != 'pending' or not self.redsys_refund_evidence:
            raise ValidationError(_('A pending sent refund and bank evidence are required.'))
        if successful:
            self._set_done()
        else:
            self._set_error(_('Bank verification confirmed no refund.'))
        self.sudo().redsys_refund_dispatch = 'resolved'
        self._log_message_on_linked_documents(_('Refund resolved by %s: %s', self.env.user.name, self.redsys_refund_evidence))
        self.env.ref('payment.cron_post_process_payment_tx').sudo()._trigger()

    def action_redsys_confirm_refund(self):
        self._redsys_resolve_refund(True)

    def action_redsys_reject_refund(self):
        self._redsys_resolve_refund(False)
