import base64
import json
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged, JsonRpcException
from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon

from .. import const, utils


class RedsysCommon(AccountPaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env.ref("wex_payment_redsys.payment_provider_redsys").sudo()
        cls.provider.write({
            "company_id": cls.env.company.id,
            "redsys_merchant_code": "999008881",
            "redsys_terminal": "1",
            "redsys_secret_key": "sq7HjrUOBfKmC576ILgskD5srU870gJ7",
            "state": "test",
            "journal_id": cls.company_data["default_journal_bank"].id,
        })
        cls.provider.journal_id.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_provider_id == cls.provider
        ).payment_account_id = cls.inbound_payment_method_line.payment_account_id
        cls.card = cls.env.ref("payment.payment_method_card")
        cls.env["ir.config_parameter"].sudo().set_param("web.base.url", "https://payments.example.com")

    def _new_transaction(self, **values):
        return self.env["payment.transaction"].create({
            "provider_id": self.provider.id,
            "payment_method_id": self.card.id,
            "reference": self.env["payment.transaction"]._compute_reference(const.PROVIDER_CODE),
            "amount": 123.45,
            "currency_id": self.currency_euro.id,
            "partner_id": self.partner.id,
            "operation": "online_redirect",
            **values,
        })

    def _notification(self, tx, **changes):
        params = {
            "Ds_Order": tx.reference,
            "Ds_Amount": "12345",
            "Ds_Currency": "978",
            "Ds_MerchantCode": "999008881",
            "Ds_Terminal": "001",
            "Ds_TransactionType": "0",
            "Ds_Response": "0000",
            "Ds_AuthorisationCode": "123456",
            **changes,
        }
        encoded = base64.b64encode(json.dumps(params).encode()).decode()
        return {
            "Ds_MerchantParameters": encoded,
            "Ds_SignatureVersion": const.SIGNATURE_VERSION,
            "Ds_Signature": utils._sign_parameters(self.provider.redsys_secret_key, tx.reference, encoded),
        }


@tagged("post_install", "-at_install")
class TestRedsys(RedsysCommon):
    def test_signature_fixed_vector(self):
        # Vector cruzado con una implementación independiente de TripleDES (Cryptodome).
        encoded = "eyJEc19PcmRlciI6IjEyMzQ1Njc4OTAxMiJ9"
        self.assertEqual(
            utils._sign_parameters(self.provider.redsys_secret_key, "123456789012", encoded),
            "WZnKdCPpwx9C0I0d2wPskG8V+LmH03PIn9v4u80doDQ=",
        )

    def test_references_are_unique_and_numeric(self):
        first, second = self._new_transaction(), self._new_transaction()
        self.assertRegex(first.reference, r"^[0-9]{12}$")
        self.assertNotEqual(first.reference, second.reference)

    def test_signed_success_and_duplicate(self):
        tx = self._new_transaction()
        data = self._notification(tx)
        tx._handle_notification_data(const.PROVIDER_CODE, data)
        self.assertEqual(tx.state, "done")
        tx._handle_notification_data(const.PROVIDER_CODE, data)
        self.assertEqual(tx.provider_reference, "123456")
        self.assertFalse(tx.token_id)

    def test_invalid_signature_also_rejected_under_test_enable(self):
        tx = self._new_transaction()
        data = self._notification(tx)
        data["Ds_Signature"] = base64.b64encode(bytes(32)).decode()
        with self.assertRaises(ValidationError):
            tx._handle_notification_data(const.PROVIDER_CODE, data)
        self.assertEqual(tx.state, "draft")

    def test_mismatched_signed_fields(self):
        for key, value in {
            "Ds_Amount": "1", "Ds_Currency": "840", "Ds_MerchantCode": "111111111",
            "Ds_Terminal": "2", "Ds_TransactionType": "3", "Ds_Response": "oops",
        }.items():
            with self.subTest(key=key):
                tx = self._new_transaction()
                with self.assertRaises(ValidationError):
                    tx._handle_notification_data(const.PROVIDER_CODE, self._notification(tx, **{key: value}))
                self.assertEqual(tx.state, "draft")

    def test_decline_does_not_require_authorization_code(self):
        tx = self._new_transaction()
        tx._handle_notification_data(const.PROVIDER_CODE, self._notification(
            tx, Ds_Response="0190", Ds_AuthorisationCode=""
        ))
        self.assertEqual(tx.state, "error")
        self.assertFalse(tx.payment_id)

    def test_success_range_excludes_0100(self):
        tx = self._new_transaction()
        tx._handle_notification_data(const.PROVIDER_CODE, self._notification(tx, Ds_Response="0100"))
        self.assertEqual(tx.state, "error")

    def test_late_decline_cannot_regress_success(self):
        tx = self._new_transaction()
        tx._handle_notification_data(const.PROVIDER_CODE, self._notification(tx))
        tx._handle_notification_data(const.PROVIDER_CODE, self._notification(tx, Ds_Response="0190"))
        self.assertEqual(tx.state, "done")

    def test_malformed_and_duplicate_json(self):
        for encoded in ("%%%", "W10=", base64.b64encode(b'{"Ds_Order":"a","Ds_Order":"b"}').decode()):
            with self.subTest(encoded=encoded), self.assertRaises(ValueError):
                utils._decode_parameters(encoded)

    def test_tokenization_configuration_rejected(self):
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.provider.allow_tokenization = True

    def test_invalid_transaction_flows_rejected(self):
        for values in ({"amount": 0}, {"amount": -1}, {"tokenize": True},
                       {"operation": "online_direct"}, {"currency_id": self.currency_usd.id}):
            with self.subTest(values=values), self.assertRaises(ValidationError), self.env.cr.savepoint():
                self._new_transaction(**values)

    def test_secret_is_restricted(self):
        operator = self.env["res.users"].sudo().create({
            "name": "Payment operator", "login": "redsys_secret_test_operator",
            "company_id": self.env.company.id,
            "company_ids": [Command.set(self.env.company.ids)],
            "groups_id": [Command.set([
                self.env.ref("base.group_user").id,
                self.env.ref("account.group_account_invoice").id,
            ])],
        })
        self.assertFalse(operator.has_group("base.group_system"))
        with self.assertRaises(AccessError):
            self.provider.with_user(operator).read(["redsys_secret_key"])

    def test_redirect_form_without_signed_payload_in_logs(self):
        tx = self._new_transaction()
        with patch("odoo.addons.payment.models.payment_transaction._logger.info") as logger:
            values = tx._get_processing_values()
        form = values["redirect_form_html"]
        self.assertIn("Ds_Signature", form)
        self.assertIn(const.API_URLS["test"], form)
        self.assertNotIn(self.provider.redsys_secret_key, form)
        self.assertNotIn("DS_MERCHANT_PAN", form)
        self.assertNotIn("DS_MERCHANT_IDENTIFIER", form)
        self.assertNotIn("Ds_Signature", str(logger.call_args_list))

    def test_native_invoice_payment_and_duplicate_postprocessing(self):
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice", "partner_id": self.partner.id,
            "invoice_line_ids": [Command.create({
                "name": "Redsys integration test", "quantity": 1, "price_unit": 123.45,
                "account_id": self.company_data["default_account_revenue"].id,
                "tax_ids": [Command.clear()],
            })],
        })
        invoice.action_post()
        tx = self._new_transaction(invoice_ids=[Command.set(invoice.ids)])
        tx._handle_notification_data(const.PROVIDER_CODE, self._notification(tx))
        tx._post_process()
        payment = tx.payment_id
        self.assertTrue(payment)
        self.assertEqual(invoice.amount_residual, 0)
        self.assertFalse(payment.payment_token_id)
        tx._handle_notification_data(const.PROVIDER_CODE, self._notification(tx))
        tx._post_process()
        self.assertEqual(tx.payment_id, payment)
        self.assertEqual(self.env["account.payment"].search_count([
            ("payment_transaction_id", "=", tx.id)
        ]), 1)

    def test_notification_card_metadata_not_stored(self):
        tx = self._new_transaction()
        tx._handle_notification_data(const.PROVIDER_CODE, self._notification(
            tx, Ds_Card_Number="454881******0003", Ds_ExpiryDate="2712", Ds_Merchant_Identifier="not-to-store"
        ))
        self.assertEqual(tx.provider_reference, "123456")
        self.assertFalse(tx.token_id)


@tagged("post_install", "-at_install")
class TestRedsysHttp(RedsysCommon, PaymentHttpCommon):
    def _invoice(self):
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice", "partner_id": self.partner.id,
            "currency_id": self.currency_euro.id,
            "invoice_line_ids": [Command.create({
                "name": "Payment", "quantity": 1, "price_unit": 123.45,
                "account_id": self.company_data["default_account_revenue"].id,
                "tax_ids": [Command.clear()],
            })],
        })
        invoice.action_post()
        return invoice

    def _pay_document(self, route, token):
        self.provider.is_published = True
        # El servidor HTTP de tests es local; la URL enviada a Redsys sigue siendo HTTPS.
        with patch.object(type(self.provider), "get_base_url", return_value="https://payments.example.com"):
            return self.make_jsonrpc_request(route, {
                "access_token": token,
                "provider_id": self.provider.id,
                "payment_method_id": self.card.id,
                "token_id": None,
                "amount": 123.45,
                "flow": "redirect",
                "tokenization_requested": False,
                "landing_route": "/payment/confirmation",
            })

    def test_native_invoice_token_and_signed_webhook(self):
        invoice = self._invoice()
        route = f"/invoice/transaction/{invoice.id}"
        values = self._pay_document(route, invoice._portal_ensure_token())
        tx = self.env["payment.transaction"].search([("reference", "=", values["reference"])])
        self.assertEqual(tx.invoice_ids, invoice)
        response = self._make_http_post_request(
            self._build_url(const.NOTIFICATION_URL), self._notification(tx)
        )
        self.assertEqual(response.status_code, 200)
        tx.invalidate_recordset()
        self.assertEqual(tx.state, "done")
        tx._post_process()
        invoice.invalidate_recordset()
        self.assertEqual(invoice.amount_residual, 0)

    def test_wrong_native_invoice_token_is_rejected(self):
        invoice = self._invoice()
        with self.assertRaises(JsonRpcException):
            self._pay_document(f"/invoice/transaction/{invoice.id}", "wrong-token")
        self.assertFalse(invoice.transaction_ids)

    def test_webhook_rejects_forgery_and_get(self):
        tx = self._new_transaction()
        data = self._notification(tx)
        data["Ds_Signature"] = base64.b64encode(bytes(32)).decode()
        response = self._make_http_post_request(self._build_url(const.NOTIFICATION_URL), data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._make_http_get_request(self._build_url(const.NOTIFICATION_URL)).status_code, 405)
        tx.invalidate_recordset()
        self.assertEqual(tx.state, "draft")

    def test_browser_return_does_not_confirm(self):
        tx = self._new_transaction()
        response = self._make_http_get_request(self._build_url(const.RETURN_URL), self._notification(tx))
        self.assertEqual(response.status_code, 200)
        tx.invalidate_recordset()
        self.assertEqual(tx.state, "draft")

    def test_native_sale_token_confirms_order(self):
        if "sale.order" not in self.env:
            self.skipTest("Sales is an optional integration; install sale to run this test")
        product = self.env["product.product"].create({
            "name": "Payment test service", "type": "service", "list_price": 123.45,
            "taxes_id": [Command.clear()],
        })
        pricelist = self.env["product.pricelist"].create({
            "name": "EUR payment test", "currency_id": self.currency_euro.id,
        })
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id, "require_payment": True, "prepayment_percent": 1,
            "pricelist_id": pricelist.id,
            "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1,
                                            "price_unit": 123.45, "tax_id": [Command.clear()]})],
        })
        values = self._pay_document(f"/my/orders/{order.id}/transaction", order._portal_ensure_token())
        tx = self.env["payment.transaction"].search([("reference", "=", values["reference"])])
        self.assertEqual(tx.sale_order_ids, order)
        response = self._make_http_post_request(self._build_url(const.NOTIFICATION_URL), self._notification(tx))
        self.assertEqual(response.status_code, 200)
        tx.invalidate_recordset()
        tx._post_process()
        order.invalidate_recordset()
        self.assertEqual(order.state, "sale")
        self.assertTrue(tx.payment_id)
