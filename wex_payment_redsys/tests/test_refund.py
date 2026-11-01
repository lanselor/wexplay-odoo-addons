import base64
import json
from unittest.mock import Mock, patch
from contextlib import nullcontext

import requests

from odoo import Command
from odoo.exceptions import ValidationError, AccessError
from odoo.tests import tagged

from .test_redsys import RedsysCommon
from .. import const, utils


@tagged('post_install', '-at_install')
class TestRefund(RedsysCommon):
    def setUp(self):
        super().setUp()
        self.env.user.sudo().write({'groups_id': [Command.link(self.env.ref(
            'wex_payment_redsys.group_refund_operator').id)]})
        self.source = self._new_transaction()
        self.source._handle_notification_data(const.PROVIDER_CODE, self._notification(self.source))
        self.source._post_process()

    def _response(self, refund, code='0900', **changes):
        params = {'Ds_Order': self.source.reference, 'Ds_Amount': str(abs(int(refund._redsys_get_amount()))),
                  'Ds_Currency': '978', 'Ds_TransactionType': '3', 'Ds_Terminal': '001',
                  'Ds_MerchantCode': '999008881', 'Ds_Response': code, **changes}
        encoded = base64.b64encode(json.dumps(params).encode()).decode()
        return {'Ds_MerchantParameters': encoded, 'Ds_SignatureVersion': const.SIGNATURE_VERSION,
                'Ds_Signature': utils._sign_parameters(self.provider.redsys_secret_key, self.source.reference, encoded)}

    def test_partial_refund_and_remaining(self):
        refund = self.source._send_refund_request(30)
        self.assertEqual(refund.state, 'pending')
        payload = utils._decode_parameters(refund._redsys_refund_payload()['Ds_MerchantParameters'])
        self.assertEqual(payload['DS_MERCHANT_ORDER'], self.source.reference)
        self.assertEqual(payload['DS_MERCHANT_AMOUNT'], '3000')
        refund.sudo()._redsys_apply_refund_response(self._response(refund))
        with self.assertRaises(ValidationError):
            self.source._send_refund_request(10)
        refund._post_process()
        self.assertEqual(refund.payment_id.payment_type, 'outbound')
        self.assertEqual(refund.payment_id.source_payment_id, self.source.payment_id)
        self.source.payment_id.invalidate_recordset()
        self.assertAlmostEqual(self.source.payment_id.amount_available_for_refund, 93.45)
        second = self.source._send_refund_request(93.45)
        self.assertEqual(second.amount, -93.45)

    def test_pending_blocks_second_request(self):
        self.source._send_refund_request(10)
        with self.assertRaises(ValidationError):
            self.source._send_refund_request(10)

    def test_invalid_amounts(self):
        for amount in (0, -1, 124):
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                self.source._send_refund_request(amount)

    def test_environment_switch_blocks(self):
        self.provider.state = 'enabled'
        with self.assertRaises(ValidationError):
            self.source._send_refund_request(10)

    def test_forged_response_stays_pending(self):
        refund = self.source._send_refund_request(10)
        data = self._response(refund)
        data['Ds_Signature'] = base64.b64encode(bytes(32)).decode()
        with self.assertRaises(ValueError):
            refund.sudo()._redsys_apply_refund_response(data)
        self.assertEqual(refund.state, 'pending')

    def test_signed_mismatch_rejected(self):
        refund = self.source._send_refund_request(10)
        with self.assertRaises(ValueError):
            refund.sudo()._redsys_apply_refund_response(self._response(refund, Ds_Amount='1'))

    def test_refusal_no_payment(self):
        refund = self.source._send_refund_request(10)
        refund.sudo()._redsys_apply_refund_response(self._response(refund, code='0190'))
        self.assertEqual(refund.state, 'error')
        self.assertFalse(refund.payment_id)

    def test_resolution_requires_evidence(self):
        refund = self.source._send_refund_request(10)
        refund.sudo().redsys_refund_dispatch = 'sent'
        with self.assertRaises(ValidationError):
            refund.action_redsys_confirm_refund()
        refund.redsys_refund_evidence = 'Canales verification: refund executed, amount 10 EUR'
        refund.action_redsys_confirm_refund()
        self.assertEqual(refund.state, 'done')

    def test_without_group_denied(self):
        self.env.user.sudo().write({'groups_id': [Command.unlink(self.env.ref(
            'wex_payment_redsys.group_refund_operator').id)]})
        with self.assertRaises(AccessError):
            self.source._send_refund_request(10)

    def test_dispatch_timeout_is_not_retried(self):
        refund = self.source._send_refund_request(10)
        self.env.flush_all()
        # Compartir fixture no confirmada; comprobar las fronteras commit sin confirmar el test.
        with patch.object(type(self.env.registry), 'cursor', return_value=nullcontext(self.env.cr)), \
                patch.object(self.env.cr, 'commit', side_effect=self.env.flush_all) as commit, patch.object(self.env.cr, 'rollback'), \
                patch('odoo.addons.wex_payment_redsys.models.refund.requests.post',
                      side_effect=requests.Timeout()) as send:
            self.env['payment.transaction']._cron_redsys_refunds()
            self.env['payment.transaction']._cron_redsys_refunds()
            commit.assert_called_once()
        refund.invalidate_recordset()
        self.assertEqual(send.call_count, 1)
        self.assertEqual(refund.redsys_refund_dispatch, 'sent')
        self.assertEqual(refund.state, 'pending')
