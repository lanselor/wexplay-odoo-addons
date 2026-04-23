# -*- coding: utf-8 -*-

import secrets

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request
from odoo.osv import expression


class KnowledgeArticle(models.Model):
    _inherit = "wex.knowledge.article"

    _PORTAL_PUBLICATION_FIELDS = {
        "portal_visible",
        "portal_contact_ids",
        "public_link_enabled",
        "public_access_token",
        "public_access_expires_at",
    }

    portal_visible = fields.Boolean(string="Visible in Portal", tracking=True)
    portal_contact_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="wex_knowledge_article_portal_contact_rel",
        column1="article_id",
        column2="partner_id",
        string="Portal Contacts",
        help="Exact portal contacts allowed to access this article even if it is not generally visible in portal.",
        tracking=True,
    )
    public_link_enabled = fields.Boolean(string="Public by Link", tracking=True)
    public_access_token = fields.Char(copy=False, readonly=True, index=True)
    public_access_expires_at = fields.Datetime(string="Public Link Expires At", tracking=True)
    public_link_url = fields.Char(compute="_compute_public_link_url")
    portal_view_count = fields.Integer(readonly=True)
    public_view_count = fields.Integer(readonly=True)
    last_portal_view_at = fields.Datetime(readonly=True)
    last_public_view_at = fields.Datetime(readonly=True)

    def _compute_public_link_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for article in self:
            if article.public_link_enabled and article.public_access_token and base_url:
                article.public_link_url = "%s/knowledge/public/%s" % (base_url.rstrip("/"), article.public_access_token)
            else:
                article.public_link_url = False

    @api.constrains("portal_contact_ids")
    def _check_portal_contacts_are_portal_users(self):
        for article in self:
            invalid_contacts = article.portal_contact_ids.filtered(lambda partner: not article._partner_has_portal_user(partner))
            if invalid_contacts:
                raise ValidationError(
                    _(
                        "Portal contacts must have at least one portal-enabled user. Invalid contacts: %s"
                    )
                    % ", ".join(invalid_contacts.mapped("display_name"))
                )

    def _partner_has_portal_user(self, partner):
        self.ensure_one()
        portal_users = partner.user_ids.filtered(
            lambda user: user.has_group("base.group_portal") and not user._is_internal()
        )
        return bool(portal_users)

    def _check_portal_publication_permissions(self, vals, current_user):
        if not self._PORTAL_PUBLICATION_FIELDS.intersection(vals):
            return
        if not (self._user_is_editor(current_user) or self._user_is_manager(current_user)):
            raise AccessError(_("Only knowledge editors can manage portal publication settings."))

    def _prepare_external_publication_vals(self, vals):
        prepared_vals = dict(vals)
        if prepared_vals.get("public_link_enabled") and not prepared_vals.get("public_access_token"):
            prepared_vals["public_access_token"] = self._generate_public_access_token()
        return prepared_vals

    @api.model
    def _generate_public_access_token(self):
        return secrets.token_urlsafe(24)

    def _check_create_permissions(self, vals_list, current_user):
        super()._check_create_permissions(vals_list, current_user)
        for vals in vals_list:
            self._check_portal_publication_permissions(vals, current_user)
            prepared_vals = self._prepare_external_publication_vals(vals)
            vals.update(prepared_vals)

    def _prepare_write_vals(self, vals, current_user):
        prepared_vals = super()._prepare_write_vals(vals, current_user)
        self._check_portal_publication_permissions(prepared_vals, current_user)
        if self._PORTAL_PUBLICATION_FIELDS.intersection(prepared_vals):
            self._check_user_can_edit_records(current_user)
        return self._prepare_external_publication_vals(prepared_vals)

    def action_regenerate_public_access_token(self):
        self.ensure_one()
        if not self._user_can_edit_record(self.env.user):
            raise AccessError(_("You do not have permission to manage the selected article."))
        self.write({"public_access_token": self._generate_public_access_token()})
        return True

    def action_open_children(self):
        action = super().action_open_children()
        action["name"] = _("Sub-articulos")
        return action

    def action_create_child_article(self):
        action = super().action_create_child_article()
        action["name"] = _("Nuevo sub-articulo")
        return action

    def _is_externally_published(self):
        self.ensure_one()
        return self.state == "published"

    def _matches_current_company_scope(self):
        self.ensure_one()
        return self.is_global or self.company_id == self.env.company

    def _user_is_portal_user(self, user):
        return bool(user and user.has_group("base.group_portal") and not user._is_internal())

    def _is_portal_contact_allowed(self, user):
        self.ensure_one()
        if not self._user_is_portal_user(user):
            return False
        return bool(user.partner_id and user.partner_id in self.portal_contact_ids)

    def _is_visible_in_portal_for_user(self, user):
        self.ensure_one()
        if not self._user_is_portal_user(user):
            return False
        if not self._is_externally_published() or not self._matches_current_company_scope():
            return False
        return self.portal_visible or self._is_portal_contact_allowed(user)

    def _is_public_token_valid(self, access_token):
        self.ensure_one()
        if not access_token or not self.public_link_enabled or not self.public_access_token:
            return False
        if access_token != self.public_access_token:
            return False
        if self.public_access_expires_at and fields.Datetime.now() > self.public_access_expires_at:
            return False
        return self._is_externally_published() and self._matches_current_company_scope()

    def _can_user_read_portal_article(self, user):
        self.ensure_one()
        return self._is_visible_in_portal_for_user(user)

    def _can_read_public_article(self, access_token):
        self.ensure_one()
        return self._is_public_token_valid(access_token)

    def _can_read_external_article(self, user=None, access_token=None):
        self.ensure_one()
        user = user or self.env.user
        return self._can_user_read_portal_article(user) or self._can_read_public_article(access_token)

    @api.model
    def _get_external_company_domain(self):
        return ["|", ("is_global", "=", True), ("company_id", "=", self.env.company.id)]

    @api.model
    def _get_portal_visible_domain(self, user=None):
        user = user or self.env.user
        partner_id = user.partner_id.id if user and user.partner_id else False
        if not self._user_is_portal_user(user):
            return [("id", "=", 0)]
        visibility_domain = (
            ["|", ("portal_visible", "=", True), ("portal_contact_ids", "in", partner_id)]
            if partner_id
            else [("portal_visible", "=", True)]
        )
        return expression.AND(
            [
                [("state", "=", "published")],
                self._get_external_company_domain(),
                visibility_domain,
            ]
        )

    @api.model
    def _get_public_link_validity_domain(self):
        now = fields.Datetime.now()
        return ["|", ("public_access_expires_at", "=", False), ("public_access_expires_at", ">=", now)]

    @api.model
    def _get_public_visible_domain(self):
        return expression.AND(
            [
                [("state", "=", "published"), ("public_link_enabled", "=", True)],
                self._get_external_company_domain(),
                self._get_public_link_validity_domain(),
            ]
        )

    @api.model
    def _get_portal_search_domain(self, search_term):
        search_term = (search_term or "").strip()
        if not search_term:
            return []
        return expression.OR(
            [
                [("name", "ilike", search_term)],
                [("subtitle", "ilike", search_term)],
                [("body_plaintext", "ilike", search_term)],
                [("category_ids.name", "ilike", search_term)],
            ]
        )

    def _get_portal_related_articles(self, user=None, limit=6):
        self.ensure_one()
        user = user or self.env.user
        category_ids = self.category_ids.ids
        if not category_ids:
            return self.browse()
        domain = expression.AND(
            [
                self._get_portal_visible_domain(user),
                [("id", "!=", self.id), ("category_ids", "child_of", category_ids)],
            ]
        )
        return self.sudo().search(domain, limit=limit, order="sequence, name, id")

    def _get_portal_sub_articles(self, user=None):
        self.ensure_one()
        user = user or self.env.user
        domain = expression.AND(
            [
                self._get_portal_visible_domain(user),
                [("parent_id", "=", self.id)],
            ]
        )
        return self.sudo().search(domain, order="sequence, name, id")

    def _get_public_sub_articles(self):
        self.ensure_one()
        domain = expression.AND(
            [
                self._get_public_visible_domain(),
                [("parent_id", "=", self.id)],
            ]
        )
        return self.sudo().search(domain, order="sequence, name, id")

    def _get_public_related_articles(self, limit=6):
        self.ensure_one()
        category_ids = self.category_ids.ids
        if not category_ids:
            return self.browse()
        domain = expression.AND(
            [
                self._get_public_visible_domain(),
                [("id", "!=", self.id), ("category_ids", "child_of", category_ids)],
            ]
        )
        return self.sudo().search(domain, limit=limit, order="sequence, name, id")

    def _prepare_external_access_log_vals(self, access_type, user=None, access_token=None):
        self.ensure_one()
        user = user or self.env.user
        partner = user.partner_id if user and not user._is_public() else self.env["res.partner"]
        try:
            http_request = request.httprequest
        except RuntimeError:
            http_request = False
        return {
            "article_id": self.id,
            "access_type": access_type,
            "user_id": user.id if user and not user._is_public() else False,
            "partner_id": partner.id if partner else False,
            "commercial_partner_id": partner.commercial_partner_id.id if partner else False,
            "access_token_hint": access_token[-8:] if access_token else False,
            "ip_address": http_request.remote_addr if http_request else False,
            "user_agent": http_request.user_agent.string if http_request and http_request.user_agent else False,
            "accessed_at": fields.Datetime.now(),
        }

    def _increment_external_access_counters(self, access_type):
        self.ensure_one()
        now = fields.Datetime.now()
        if access_type == "portal":
            self.sudo().write(
                {
                    "portal_view_count": self.portal_view_count + 1,
                    "last_portal_view_at": now,
                }
            )
            return
        self.sudo().write(
            {
                "public_view_count": self.public_view_count + 1,
                "last_public_view_at": now,
            }
        )

    def log_external_access(self, access_type, user=None, access_token=None):
        self.ensure_one()
        self.env["wex.knowledge.portal.access.log"].sudo().create(
            self._prepare_external_access_log_vals(
                access_type=access_type,
                user=user,
                access_token=access_token,
            )
        )
        self._increment_external_access_counters(access_type)
