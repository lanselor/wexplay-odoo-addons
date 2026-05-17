# -*- coding: utf-8 -*-
import base64
import logging

from odoo import http
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WexQzCertificateController(http.Controller):

    @http.route("/wexplay/qz/certificate", type="http", auth="public", methods=["GET"], csrf=False)
    def qz_certificate(self):
        """Devuelve el certificado público para QZ Tray (texto plano)."""
        cert = http.request.env["ir.config_parameter"].sudo().get_param(
            "wex_print_core.qz_certificate", ""
        )
        return http.request.make_response(
            cert or "",
            headers=[("Content-Type", "text/plain; charset=utf-8")],
        )

    @http.route("/wexplay/qz/sign", type="json", auth="user", methods=["POST"])
    def qz_sign(self, to_sign=""):
        """Firma el string de QZ Tray con la clave privada RSA configurada."""
        if not to_sign:
            return ""

        private_key_pem = http.request.env["ir.config_parameter"].sudo().get_param(
            "wex_print_core.qz_private_key", ""
        )
        if not private_key_pem:
            raise UserError("No hay clave privada configurada en Ajustes → Wexplay Print / QZ.")

        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

            private_key = serialization.load_pem_private_key(
                private_key_pem.encode("utf-8"),
                password=None,
            )
            signature = private_key.sign(
                to_sign.encode("utf-8"),
                asym_padding.PKCS1v15(),
                hashes.SHA512(),
            )
            return base64.b64encode(signature).decode("utf-8")

        except Exception as e:
            _logger.exception("Error firmando request QZ: %s", e)
            raise UserError(f"Error al firmar el certificado QZ: {e}")
