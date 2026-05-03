# -*- coding: utf-8 -*-

from odoo import _, fields, models

PORTAL_B2B_PLACEHOLDER = "${enlaceportalB2B}"


class WhatsappComposeWizard(models.TransientModel):
    _inherit = "whatsapp.compose.wizard"

    portal_link_type = fields.Selection(
        selection_add=[("repair_b2b", "Reparación B2B del cliente")],
        ondelete={"repair_b2b": "set default"},
    )

    def _get_default_portal_link_type(self, res_model):
        if res_model == "repair.order":
            return "repair_b2b"
        return super()._get_default_portal_link_type(res_model)

    def _get_repair_b2b_record(self):
        self.ensure_one()
        target = self._get_target_record_from_context()
        if target and target._name == "repair.order":
            return target
        return self.env["repair.order"]

    def _get_repair_b2b_url(self):
        self.ensure_one()
        repair = self._get_repair_b2b_record()
        if not repair:
            return ""
        return f"/my/repairs/{repair.id}"

    def _partner_has_active_b2b_portal(self):
        self.ensure_one()
        commercial_partner = self._get_partner_commercial_partner()
        if not commercial_partner:
            return False

        portal_group = self.env.ref("base.group_portal", raise_if_not_found=False)
        if not portal_group:
            return False

        portal_users = self.env["res.users"].sudo().search(
            [
                ("active", "=", True),
                ("partner_id", "child_of", commercial_partner.ids),
                ("groups_id", "in", portal_group.id),
            ],
            limit=1,
        )
        return bool(portal_users)

    def _check_repair_b2b_allowed(self):
        self.ensure_one()
        repair = self._get_repair_b2b_record()
        if not repair:
            return False
        if not self._check_record_belongs_to_partner(repair):
            return False
        if not self._partner_has_active_b2b_portal():
            return False
        return True

    def _get_portal_link_url(self):
        self.ensure_one()
        if self.portal_link_type == "repair_b2b":
            if not self._check_repair_b2b_allowed():
                return ""
            return self._get_repair_b2b_url()
        return super()._get_portal_link_url()

    def _is_b2b_portal_link_type(self):
        self.ensure_one()
        return self.portal_link_type == "repair_b2b"

    def _get_portal_link_status(self):
        self.ensure_one()
        if self.portal_link_type != "repair_b2b":
            return super()._get_portal_link_status()

        repair = self._get_repair_b2b_record()
        if not repair:
            return _("Abre el WhatsApp desde una reparación para insertar el enlace B2B."), False
        if not self._check_record_belongs_to_partner(repair):
            return _("La reparación no pertenece al cliente seleccionado."), False
        if not self._partner_has_active_b2b_portal():
            return _("Portal B2B no activo para este cliente. No se puede insertar el enlace."), False
        return _("Portal B2B activo. Enlace privado de la reparación listo para insertar."), True

    def _render_placeholder(self, expr, render_context):
        self.ensure_one()
        if (expr or "").strip() == "enlaceportalB2B":
            if self._is_b2b_portal_link_type():
                return self.portal_url or PORTAL_B2B_PLACEHOLDER
            return PORTAL_B2B_PLACEHOLDER
        return super()._render_placeholder(expr, render_context)

    def _get_portal_link_placeholder(self):
        self.ensure_one()
        if self._is_b2b_portal_link_type():
            return PORTAL_B2B_PLACEHOLDER
        return super()._get_portal_link_placeholder()
