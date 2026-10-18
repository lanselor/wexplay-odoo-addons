from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .. import const, utils


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[(const.PROVIDER_CODE, "Redsys (Wexplay)")],
        ondelete={const.PROVIDER_CODE: "set default"},
    )
    redsys_merchant_code = fields.Char(string="Merchant code", required_if_provider=const.PROVIDER_CODE)
    redsys_terminal = fields.Char(string="Terminal", default="1", required_if_provider=const.PROVIDER_CODE)
    redsys_secret_key = fields.Char(
        string="Signing key", groups="base.group_system", copy=False,
        required_if_provider=const.PROVIDER_CODE,
    )

    @api.constrains("code", "state", "redsys_merchant_code", "redsys_terminal", "redsys_secret_key",
                    "allow_tokenization", "capture_manually", "allow_express_checkout")
    def _redsys_check_configuration(self):
        for provider in self.filtered(lambda p: p.code == const.PROVIDER_CODE):
            if provider.allow_tokenization or provider.capture_manually or provider.allow_express_checkout:
                raise ValidationError(_("Redsys only supports immediate redirect payments without saved cards."))
            if provider.state == "disabled":
                continue
            merchant = provider.redsys_merchant_code or ""
            terminal = provider.redsys_terminal or ""
            if not (merchant.isascii() and merchant.isdigit() and len(merchant) == 9
                    and terminal.isascii() and terminal.isdigit() and 1 <= len(terminal) <= 3
                    and int(terminal) > 0):
                raise ValidationError(_("Enter a nine-digit merchant code and a valid terminal."))
            try:
                key = utils._decode_base64(provider.sudo().redsys_secret_key)
                if len(key) != 24:
                    raise ValueError()
            except ValueError as error:
                raise ValidationError(_("Invalid Redsys SHA256 signing key.")) from error

    def _get_default_payment_method_codes(self):
        if self.code == const.PROVIDER_CODE:
            return {"card"}
        return super()._get_default_payment_method_codes()

    def _get_supported_currencies(self):
        currencies = super()._get_supported_currencies()
        return currencies.filtered(lambda c: c.name == "EUR") if self.code == const.PROVIDER_CODE else currencies

    def _redsys_get_api_url(self):
        self.ensure_one()
        if self.state not in const.API_URLS:
            raise ValidationError(_("The Redsys provider is disabled."))
        return const.API_URLS[self.state]
