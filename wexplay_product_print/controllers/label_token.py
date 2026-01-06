# -*- coding: utf-8 -*-
import time
import hmac
import hashlib

from odoo import http
from odoo.http import request


class WexplayProductLabelToken(http.Controller):
    """
    1) /wexplay/label/signed_url (JSON, auth=user):
       Devuelve una URL pública firmada para el PDF del reporte.
    2) /wexplay/label/pdf/<id> (HTTP, auth=public):
       Devuelve el PDF si el token+expires es válido.
    """
    @http.route("/wexplay/label/ping", type="http", auth="public", methods=["GET"])
    def ping(self, **kw):
        return request.make_response("OK", [("Content-Type", "text/plain")])



    def _sign(self, product_id: int, expires: int) -> str:
        # Secret estable por BD (válido para firmar)
        secret = request.env["ir.config_parameter"].sudo().get_param("database.secret") or ""
        msg = f"{product_id}:{expires}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    @http.route("/wexplay/label/signed_url", type="json", auth="user", methods=["POST"])
    def signed_url(self, product_id: int):
        # URL válida 60 segundos (ajústalo si quieres)
        expires = int(time.time()) + 60
        token = self._sign(int(product_id), expires)

        # IMPORTANTE: report_name EXACTO (tu restricción)
        report_name = "wexplay_product_print.report_product_label_ql700_62x29"

        # Construimos la URL ABSOLUTA que QZ podrá descargar sin sesión
        base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if base_url.startswith("http://"):
            base_url = "https://" + base_url[len("http://"):]
        pdf_url = f"{base_url}/wexplay/label/pdf/{int(product_id)}?expires={expires}&token={token}&report_name={report_name}"

        return {
            "pdf_url": pdf_url,
            "expires": expires,
        }

    @http.route("/wexplay/label/pdf/<int:product_id>", type="http", auth="public", methods=["GET"])
    def label_pdf(self, product_id, token=None, expires=None, report_name=None, **kwargs):
        # Validaciones básicas
        try:
            expires_i = int(expires or "0")
        except Exception:
            return request.not_found()

        if not token or not expires_i:
            return request.not_found()

        # Expiración
        if time.time() > expires_i:
            return request.not_found()

        # Token
        expected = self._sign(int(product_id), expires_i)
        if not hmac.compare_digest(token, expected):
            return request.not_found()

        # Report name (solo aceptamos el que quieres usar)
        allowed_report = "wexplay_product_print.report_product_label_ql700_62x29"
        if report_name != allowed_report:
            return request.not_found()

        # Render del PDF del reporte QWeb por report_name (NO dependemos de ir.actions.report external id)
        pdf, _ = request.env["ir.actions.report"].sudo()._render_qweb_pdf(allowed_report, [int(product_id)])

        headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", str(len(pdf))),
        ]
        return request.make_response(pdf, headers=headers)
