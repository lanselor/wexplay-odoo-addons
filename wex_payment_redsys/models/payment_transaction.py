import base64
from decimal import Decimal
import json
import re

from werkzeug.urls import url_join

from odoo import _, api, models
from odoo.exceptions import ValidationError

from .. import const, utils


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator="-", **kwargs):
        if provider_code != const.PROVIDER_CODE:
            return super()._compute_reference(provider_code, prefix=prefix, separator=separator, **kwargs)
        reference = self.env["ir.sequence"].sudo().next_by_code("wex_payment_redsys.order")
        if not reference or not re.fullmatch(r"[0-9]{12}", reference):
            raise ValidationError(_("Redsys order sequence is missing or exhausted."))
        return reference

    @api.constrains("provider_id", "operation", "amount", "currency_id", "token_id", "tokenize")
    def _redsys_check_payment_flow(self):
        for tx in self.filtered(lambda t: t.provider_code == const.PROVIDER_CODE):
            if (tx.operation != "online_redirect" or tx.token_id or tx.tokenize
                    or tx.amount <= 0 or tx.currency_id.name != "EUR"):
                raise ValidationError(_("Redsys requires a positive EUR redirect payment without saved cards."))

    def _redsys_get_amount(self):
        self.ensure_one()
        return str(int(Decimal(str(self.currency_id.round(self.amount))) * 100))

    def _get_specific_rendering_values(self, processing_values):
        values = super()._get_specific_rendering_values(processing_values)
        if self.provider_code == const.PROVIDER_CODE:
            # Odoo registra este contexto; preparar el mensaje firmado solo al renderizar.
            return {"redsys_transaction": self}
        return values

    def _redsys_prepare_payment_parameters(self):
        self.ensure_one()
        self._redsys_check_payment_flow()
        provider = self.provider_id
        provider._redsys_check_configuration()
        base_url = provider.get_base_url()
        if not base_url.startswith("https://"):
            raise ValidationError(_("Configure a public HTTPS base URL before using Redsys."))
        params = {
            "DS_MERCHANT_AMOUNT": self._redsys_get_amount(),
            "DS_MERCHANT_ORDER": self.reference,
            "DS_MERCHANT_MERCHANTCODE": provider.redsys_merchant_code,
            "DS_MERCHANT_CURRENCY": "978",
            "DS_MERCHANT_TRANSACTIONTYPE": "0",
            "DS_MERCHANT_TERMINAL": provider.redsys_terminal,
            "DS_MERCHANT_MERCHANTURL": url_join(base_url, const.NOTIFICATION_URL),
            "DS_MERCHANT_URLOK": url_join(base_url, const.RETURN_URL),
            "DS_MERCHANT_URLKO": url_join(base_url, const.RETURN_URL),
            "DS_MERCHANT_PAYMETHODS": "T",
        }
        encoded = base64.b64encode(json.dumps(params, separators=(",", ":")).encode()).decode()
        return {
            "api_url": provider._redsys_get_api_url(),
            "parameters": encoded,
            "signature": utils._sign_parameters(provider.sudo().redsys_secret_key, self.reference, encoded),
            "version": const.SIGNATURE_VERSION,
        }

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        if provider_code != const.PROVIDER_CODE:
            return super()._get_tx_from_notification_data(provider_code, notification_data)
        try:
            params = utils._decode_parameters(notification_data.get("Ds_MerchantParameters"))
        except ValueError as error:
            raise ValidationError(_("Invalid Redsys notification.")) from error
        reference = params.get("Ds_Order", "")
        if not re.fullmatch(r"[0-9]{12}", reference):
            raise ValidationError(_("Invalid Redsys order reference."))
        tx = self.search([("provider_code", "=", provider_code), ("reference", "=", reference)], limit=2)
        if len(tx) != 1:
            raise ValidationError(_("Redsys transaction not found."))
        return tx

    def _redsys_check_notification(self, data):
        self.ensure_one()
        try:
            if data.get("Ds_SignatureVersion") != const.SIGNATURE_VERSION:
                raise ValueError()
            encoded = data.get("Ds_MerchantParameters")
            params = utils._decode_parameters(encoded)
            if not utils._verify_signature(
                self.provider_id.sudo().redsys_secret_key, self.reference, encoded, data.get("Ds_Signature")
            ):
                raise ValueError()
            expected = {
                "Ds_Order": self.reference,
                "Ds_Amount": self._redsys_get_amount(),
                "Ds_Currency": "978",
                "Ds_MerchantCode": self.provider_id.redsys_merchant_code,
                "Ds_TransactionType": "0",
            }
            if any(params.get(key) != value for key, value in expected.items()):
                raise ValueError()
            terminal = params.get("Ds_Terminal", "")
            if not re.fullmatch(r"[0-9]{1,3}", terminal) or int(terminal) != int(self.provider_id.redsys_terminal):
                raise ValueError()
            if not re.fullmatch(r"[0-9]{4}", params.get("Ds_Response", "")):
                raise ValueError()
            authorization = params.get("Ds_AuthorisationCode", "")
            if not re.fullmatch(r"[A-Za-z0-9]{1,12}", authorization) and int(params["Ds_Response"]) < 100:
                raise ValueError()
        except (ValueError, TypeError, UnicodeError) as error:
            raise ValidationError(_("Redsys notification could not be verified.")) from error
        return params

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != const.PROVIDER_CODE:
            return
        # Serializar notificaciones repetidas sin procesar contabilidad en esta ruta.
        self.env.cr.execute("SELECT id FROM payment_transaction WHERE id = %s FOR UPDATE", [self.id])
        self.invalidate_recordset()
        self._redsys_check_payment_flow()
        params = self._redsys_check_notification(notification_data)
        response = int(params["Ds_Response"])
        if self.state == "done":
            return
        if response < 100:
            self.provider_reference = params["Ds_AuthorisationCode"]
            self._set_done()
            self.env.ref("payment.cron_post_process_payment_tx")._trigger()
        elif response == 9915:
            self._set_canceled(state_message=_("Payment cancelled in Redsys."))
        else:
            self._set_error(_("Redsys declined the payment (code %s).", params["Ds_Response"]))
