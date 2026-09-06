from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    wex_has_active_portal = fields.Boolean(
        string="Portal activo",
        compute="_compute_wex_has_active_portal",
        search="_search_wex_has_active_portal",
        groups="base.group_user",
        help="En empresas, indica acceso portal activo en su entidad comercial. "
             "En personas, indica únicamente su acceso propio, no un inicio de sesión.",
    )

    @api.model
    def _get_active_portal_users(self, domain=None):
        # Solo se devuelve un indicador al backend, nunca datos de las cuentas.
        return self.env["res.users"].sudo().search([
            ("active", "=", True),
            ("groups_id", "in", [self.env.ref("base.group_portal").id]),
        ] + (domain or []))

    @api.depends(
        "is_company", "commercial_partner_id", "user_ids.active", "user_ids.groups_id",
        "child_ids", "child_ids.user_ids.active", "child_ids.user_ids.groups_id",
        "child_ids.commercial_partner_id",
    )
    def _compute_wex_has_active_portal(self):
        companies = self.filtered("is_company")
        users = self._get_active_portal_users([
            "|", ("partner_id", "in", self.ids),
            ("partner_id.commercial_partner_id", "in", companies.commercial_partner_id.ids),
        ])
        own_partner_ids = set(users.partner_id.ids)
        commercial_partner_ids = set(users.partner_id.commercial_partner_id.ids)
        for partner in self:
            partner.wex_has_active_portal = (
                partner.commercial_partner_id.id in commercial_partner_ids
                if partner.is_company else partner.id in own_partner_ids
            )

    @api.model
    def _search_wex_has_active_portal(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise NotImplementedError("Portal activo only supports boolean = and != searches.")
        users = self._get_active_portal_users()
        domain = [
            "|", ("id", "in", users.partner_id.ids),
            "&", ("is_company", "=", True),
            ("commercial_partner_id", "in", users.partner_id.commercial_partner_id.ids),
        ]
        return domain if value == (operator == "=") else ["!"] + domain
