import json
from urllib.parse import quote

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wex_device_test_api_token = fields.Char(
        string="Device Test API Token",
        config_parameter="wex_device_test.api_token",
    )
    wex_device_test_public_base_url = fields.Char(
        string="Device Test Public Base URL",
        config_parameter="wex_device_test.public_base_url",
    )
    wex_device_test_effective_base_url = fields.Char(
        compute="_compute_wex_device_test_qr_data",
        string="Effective Device Test Base URL",
        readonly=True,
    )
    wex_device_test_config_qr_payload = fields.Text(
        compute="_compute_wex_device_test_qr_data",
        string="Device Test Config QR Payload",
        readonly=True,
    )
    wex_device_test_config_qr_url = fields.Char(
        compute="_compute_wex_device_test_qr_data",
        string="Device Test Config QR URL",
        readonly=True,
    )
    wex_device_test_config_qr_html = fields.Html(
        compute="_compute_wex_device_test_qr_data",
        string="Device Test Config QR",
        sanitize=False,
        readonly=True,
    )

    def _get_wex_device_test_effective_base_url(self):
        self.ensure_one()
        config = self.env["ir.config_parameter"].sudo()
        return (
            self.wex_device_test_public_base_url
            or config.get_param("wex_device_test.public_base_url")
            or config.get_param("web.base.url")
            or ""
        ).strip()

    def _get_wex_device_test_config_payload(self):
        self.ensure_one()
        if not self.wex_device_test_api_token:
            return False
        base_url = self._get_wex_device_test_effective_base_url()
        if not base_url:
            return False
        return json.dumps(
            {
                "type": "wex_device_test_config",
                "version": 1,
                "base_url": base_url,
                "api_token": self.wex_device_test_api_token,
            },
            separators=(",", ":"),
        )

    def _get_wex_device_test_qr_url(self, value, width=320, height=320):
        self.ensure_one()
        if not value:
            return False
        return "/report/barcode/QR/%s?width=%s&height=%s" % (
            quote(value, safe=""),
            width,
            height,
        )

    def _build_wex_device_test_qr_html(self, qr_url, alt_text):
        self.ensure_one()
        if not qr_url:
            return False
        return Markup(
            '<div class="text-center">'
            '<img src="%s" alt="%s" style="width:220px;height:220px;object-fit:contain;" class="img-fluid border rounded bg-white p-2"/>'
            "</div>"
        ) % (escape(qr_url), escape(alt_text))

    @api.depends("wex_device_test_api_token", "wex_device_test_public_base_url")
    def _compute_wex_device_test_qr_data(self):
        for record in self:
            payload = record._get_wex_device_test_config_payload()
            qr_url = record._get_wex_device_test_qr_url(payload)
            record.wex_device_test_effective_base_url = (
                record._get_wex_device_test_effective_base_url()
            )
            record.wex_device_test_config_qr_payload = payload
            record.wex_device_test_config_qr_url = qr_url
            record.wex_device_test_config_qr_html = record._build_wex_device_test_qr_html(
                qr_url,
                "Wex Device Test config QR",
            )

    def action_print_wex_device_test_config_qr(self):
        self.ensure_one()
        if not self.wex_device_test_api_token:
            raise UserError("Configura primero el bearer token de fase 1.")
        if not self._get_wex_device_test_effective_base_url():
            raise UserError("Configura una URL base pública o web.base.url antes de imprimir el QR.")
        return self.env.ref(
            "wex_device_test.action_report_wex_device_test_config_qr"
        ).report_action(self)
