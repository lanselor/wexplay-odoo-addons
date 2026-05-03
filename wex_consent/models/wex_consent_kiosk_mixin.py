# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import AccessError


class WexConsentKioskAccessMixin(models.AbstractModel):
    _name = "wex.consent.kiosk.access.mixin"
    _description = "Mixin de acceso kiosko de consentimientos"

    def _check_kiosk_access(self):
        if not (
            self.env.user.has_group("wex_consent.group_wex_consent_kiosk")
            or self.env.user.has_group("wex_consent.group_wex_consent_manager")
        ):
            raise AccessError(_("No tienes permisos para operar el modo kiosko."))
