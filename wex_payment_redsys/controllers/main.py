from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from .. import const


class RedsysController(http.Controller):
    @http.route(const.NOTIFICATION_URL, type="http", auth="public", methods=["POST"],
                csrf=False, save_session=False)
    def redsys_notification(self, **data):
        form = request.httprequest.form
        required = ("Ds_MerchantParameters", "Ds_Signature", "Ds_SignatureVersion")
        if (request.httprequest.content_length or 0) > 24576 or any(
            len(form.getlist(key)) != 1 for key in required
        ):
            raise BadRequest("Invalid Redsys notification")
        try:
            # La firma autentica esta llamada externa; no depende de sesión ni token portal.
            with request.env.cr.savepoint():
                request.env["payment.transaction"].sudo()._handle_notification_data(
                    const.PROVIDER_CODE, {key: form[key] for key in required}
                )
        except ValidationError:
            raise BadRequest("Invalid Redsys notification") from None
        return request.make_response("OK", headers=[("Content-Type", "text/plain")])

    @http.route(const.RETURN_URL, type="http", auth="public", methods=["GET"], sitemap=False)
    def redsys_return(self, **kwargs):
        return request.redirect("/payment/status")
