# -*- coding: utf-8 -*-

from odoo import api, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    @api.model
    def _wexplay_cleanup_sat_mail_templates(self):
        old_template = self.env.ref(
            "wexplay_repair.email_template_edi_invoice_sat",
            raise_if_not_found=False,
        )
        if old_template:
            old_template.unlink()

        new_template = self.env.ref(
            "wexplay_repair.email_template_edi_invoice_sat_v2",
            raise_if_not_found=False,
        )
        if new_template:
            new_template.write({"name": "Factura SAT - Completa"})

        return True
