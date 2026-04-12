from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError, ValidationError


class KnowledgeArticle(models.Model):
    _name = "wex.knowledge.article"
    _description = "Knowledge Article"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, write_date desc, id desc"
    _parent_name = "parent_id"
    _parent_store = True

    _EDITOR_RESTRICTED_FIELDS = {
        "state",
        "owner_id",
        "collaborator_ids",
        "allowed_group_ids",
        "link_ids",
    }
    _MANAGER_RESTRICTED_FIELDS = {
        "is_locked",
        "company_id",
        "is_global",
    }
    _EDITORIAL_FIELDS = {
        "name",
        "subtitle",
        "body_html",
        "state",
        "visibility",
        "category_ids",
        "tag_ids",
        "parent_id",
        "sequence",
        "owner_id",
        "collaborator_ids",
        "allowed_group_ids",
        "link_ids",
        "is_locked",
        "company_id",
        "is_global",
    }
    _DASHBOARD_SECTION_LIMIT = 8

    name = fields.Char(required=True, tracking=True)
    subtitle = fields.Char(tracking=True)
    body_html = fields.Html(string="Content", sanitize=True)
    body_plaintext = fields.Text(compute="_compute_body_plaintext", store=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("published", "Published"),
            ("archived", "Archived"),
            ("obsolete", "Obsolete"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    visibility = fields.Selection(
        [
            ("private", "Private"),
            ("internal", "Internal"),
            ("by_group", "By Group"),
        ],
        default="internal",
        required=True,
        tracking=True,
    )
    is_locked = fields.Boolean(string="Locked", tracking=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, tracking=True, index=True)
    is_global = fields.Boolean(default=False, tracking=True)
    author_id = fields.Many2one("res.users", required=True, readonly=True, default=lambda self: self.env.user)
    owner_id = fields.Many2one("res.users", required=True, tracking=True, default=lambda self: self.env.user)
    last_editor_id = fields.Many2one("res.users", readonly=True, tracking=True, default=lambda self: self.env.user)
    collaborator_ids = fields.Many2many("res.users", "wex_knowledge_article_collaborator_rel", "article_id", "user_id")
    allowed_group_ids = fields.Many2many("res.groups", "wex_knowledge_article_group_rel", "article_id", "group_id")
    category_ids = fields.Many2many(
        "wex.knowledge.category",
        "wex_knowledge_article_category_rel",
        "article_id",
        "category_id",
    )
    tag_ids = fields.Many2many(
        "wex.knowledge.tag",
        "wex_knowledge_article_tag_rel",
        "article_id",
        "tag_id",
    )
    parent_id = fields.Many2one("wex.knowledge.article", ondelete="restrict", index=True)
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("wex.knowledge.article", "parent_id")
    link_ids = fields.One2many("wex.knowledge.article.link", "article_id", string="Related Records")
    favorite_user_ids = fields.Many2many(
        "res.users",
        "wex_knowledge_article_favorite_rel",
        "article_id",
        "user_id",
        string="Favorite Users",
    )
    is_favorite = fields.Boolean(compute="_compute_is_favorite", inverse="_inverse_is_favorite", search="_search_is_favorite")
    display_path = fields.Char(compute="_compute_display_path")
    child_count = fields.Integer(compute="_compute_child_count")
    related_record_count = fields.Integer(compute="_compute_related_record_count")
    can_edit = fields.Boolean(compute="_compute_permissions")
    can_manage_relations = fields.Boolean(compute="_compute_permissions")
    can_change_lock = fields.Boolean(compute="_compute_permissions")

    @api.depends("body_html")
    def _compute_body_plaintext(self):
        for article in self:
            article.body_plaintext = tools.html2plaintext(article.body_html or "").strip()

    @api.depends("favorite_user_ids")
    def _compute_is_favorite(self):
        current_user = self.env.user
        for article in self:
            article.is_favorite = current_user in article.favorite_user_ids

    def _inverse_is_favorite(self):
        current_user = self.env.user
        for article in self:
            if article.is_favorite:
                article.favorite_user_ids = [(4, current_user.id)]
            else:
                article.favorite_user_ids = [(3, current_user.id)]

    def _search_is_favorite(self, operator, value):
        if operator not in ("=", "!="):
            raise ValidationError(_("Unsupported favorite search operator."))
        expected = bool(value)
        if operator == "!=":
            expected = not expected
        if expected:
            return [("favorite_user_ids", "in", self.env.user.id)]
        return [("favorite_user_ids", "not in", self.env.user.id)]

    @api.depends("parent_id.display_path", "name")
    def _compute_display_path(self):
        for article in self:
            if article.parent_id:
                article.display_path = "%s / %s" % (article.parent_id.display_path, article.name)
            else:
                article.display_path = article.name or ""

    def _compute_child_count(self):
        for article in self:
            article.child_count = len(article.child_ids)

    def _compute_related_record_count(self):
        for article in self:
            article.related_record_count = len(article.link_ids)

    def _user_is_editor(self, user=None):
        user = user or self.env.user
        return user.has_group("wex_knowledge.group_knowledge_editor")

    def _user_is_manager(self, user=None):
        user = user or self.env.user
        return user.has_group("wex_knowledge.group_knowledge_manager")

    def _user_can_edit_record(self, user):
        self.ensure_one()
        if self._user_is_manager(user):
            return True
        if self.is_locked:
            return False
        if self._user_is_editor(user):
            return True
        return user == self.author_id or user == self.owner_id or user in self.collaborator_ids

    def _can_user_manage_relations(self, user):
        return self._user_is_manager(user) or self._user_is_editor(user)

    @api.depends("author_id", "owner_id", "collaborator_ids", "is_locked")
    def _compute_permissions(self):
        current_user = self.env.user
        for article in self:
            article.can_edit = article._user_can_edit_record(current_user)
            article.can_manage_relations = article._can_user_manage_relations(current_user)
            article.can_change_lock = article._user_is_manager(current_user)

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_("You cannot create recursive article hierarchies."))

    @api.constrains("company_id", "is_global")
    def _check_company_scope(self):
        for article in self:
            if article.is_global and article.company_id:
                raise ValidationError(_("A global article cannot be assigned to a company."))
            if not article.is_global and not article.company_id:
                raise ValidationError(_("A non-global article must belong to a company."))

    @api.constrains("visibility", "allowed_group_ids")
    def _check_visibility_groups(self):
        for article in self:
            if article.visibility == "by_group" and not article.allowed_group_ids:
                raise ValidationError(_("Articles with visibility by group require at least one allowed group."))

    @api.constrains("company_id", "is_global", "category_ids", "tag_ids")
    def _check_taxonomy_scope(self):
        for article in self:
            if article.is_global:
                if article.category_ids.filtered(lambda category: not category.is_global):
                    raise ValidationError(_("Global articles can only use global categories."))
                if article.tag_ids:
                    raise ValidationError(_("Global articles cannot use company-specific tags."))
                continue
            invalid_categories = article.category_ids.filtered(
                lambda category: not category.is_global and category.company_id != article.company_id
            )
            if invalid_categories:
                raise ValidationError(_("Article categories must be global or belong to the same company as the article."))
            invalid_tags = article.tag_ids.filtered(lambda tag: tag.company_id != article.company_id)
            if invalid_tags:
                raise ValidationError(_("Article tags must belong to the same company as the article."))

    def _check_restricted_field_permissions(self, vals, current_user, create_mode=False):
        is_editor = self._user_is_editor(current_user)
        is_manager = self._user_is_manager(current_user)
        if not is_editor and self._EDITOR_RESTRICTED_FIELDS.intersection(vals):
            if create_mode:
                raise AccessError(_("Only editors can configure workflow, ownership and generic relations."))
            raise AccessError(_("Only editors can change workflow, ownership, collaborators and related record links."))
        if not is_manager and self._MANAGER_RESTRICTED_FIELDS.intersection(vals):
            raise AccessError(_("Only managers can change locks and company scope."))

    def _prepare_create_vals(self, vals, current_user):
        prepared_vals = dict(vals)
        prepared_vals.setdefault("author_id", current_user.id)
        prepared_vals.setdefault("owner_id", current_user.id)
        prepared_vals.setdefault("last_editor_id", current_user.id)
        return prepared_vals

    def _check_create_permissions(self, vals_list, current_user):
        for vals in vals_list:
            prepared_vals = self._prepare_create_vals(vals, current_user)
            vals.update(prepared_vals)
            self._check_restricted_field_permissions(prepared_vals, current_user, create_mode=True)

    def _check_user_can_edit_records(self, current_user):
        for article in self:
            if not article._user_can_edit_record(current_user):
                raise AccessError(_("You do not have permission to edit the selected article."))

    def _prepare_write_vals(self, vals, current_user):
        prepared_vals = dict(vals)
        self._check_restricted_field_permissions(prepared_vals, current_user)
        if self._EDITORIAL_FIELDS.intersection(prepared_vals):
            self._check_user_can_edit_records(current_user)
            prepared_vals["last_editor_id"] = current_user.id
        return prepared_vals

    @api.model_create_multi
    def create(self, vals_list):
        current_user = self.env.user
        self._check_create_permissions(vals_list, current_user)
        return super().create(vals_list)

    def write(self, vals):
        prepared_vals = self._prepare_write_vals(vals, self.env.user)
        return super().write(prepared_vals)

    def _check_can_unlink(self):
        if not self._user_is_manager():
            raise AccessError(_("Only managers can delete knowledge articles."))

    def unlink(self):
        self._check_can_unlink()
        return super().unlink()

    def action_toggle_favorite(self):
        for article in self:
            article.is_favorite = not article.is_favorite
        return True

    def action_publish(self):
        self.write({"state": "published"})

    def action_archive(self):
        self.write({"state": "archived"})

    def action_mark_obsolete(self):
        self.write({"state": "obsolete"})

    def action_reset_draft(self):
        self.write({"state": "draft"})

    def _check_can_change_lock(self):
        if not self._user_is_manager():
            raise AccessError(_("Only managers can change article locks."))

    def action_lock(self):
        self._check_can_change_lock()
        self.write({"is_locked": True})

    def action_unlock(self):
        self._check_can_change_lock()
        self.write({"is_locked": False})

    def action_open_related_links(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Related Records"),
            "res_model": "wex.knowledge.article.link",
            "view_mode": "list,form",
            "domain": [("article_id", "=", self.id)],
            "context": {"default_article_id": self.id},
            "target": "current",
        }

    def action_open_children(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Child Articles"),
            "res_model": "wex.knowledge.article",
            "view_mode": "list,form",
            "domain": [("parent_id", "=", self.id)],
            "context": {"default_parent_id": self.id},
            "target": "current",
        }

    def action_create_child_article(self):
        self.ensure_one()
        payload = self._get_explorer_payload_from_context()
        return {
            "type": "ir.actions.act_window",
            "name": _("Nuevo art?culo hijo"),
            "res_model": "wex.knowledge.article",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_parent_id": self.id,
                "default_owner_id": self.owner_id.id or self.env.user.id,
                "default_company_id": self.company_id.id,
                "default_is_global": self.is_global,
                "default_visibility": self.visibility,
                "wex_kb_explorer_payload": payload,
            },
        }

    def action_return_to_explorer(self):
        action = self.env["ir.actions.actions"]._for_xml_id("wex_knowledge.action_knowledge_explorer")
        action["context"] = {"wex_kb_explorer_payload": self._get_explorer_payload_from_context()}
        return action

    def _get_explorer_payload_from_context(self):
        return self.env.context.get("wex_kb_explorer_payload") or {}

    @api.model
    def _payload_to_int(self, payload, key):
        value = payload.get(key)
        return int(value) if value else False

    @api.model
    def _get_search_domain_for_term(self, search_term):
        if not search_term:
            return []
        return [
            "|",
            "|",
            "|",
            "|",
            ("name", "ilike", search_term),
            ("subtitle", "ilike", search_term),
            ("body_plaintext", "ilike", search_term),
            ("category_ids.name", "ilike", search_term),
            ("tag_ids.name", "ilike", search_term),
        ]

    @api.model
    def _append_relation_payload_filters(self, domain, payload):
        field_mapping = {
            "category_id": "category_ids",
            "tag_id": "tag_ids",
            "author_id": "author_id",
            "owner_id": "owner_id",
            "collaborator_id": "collaborator_ids",
        }
        for payload_key, domain_field in field_mapping.items():
            value = self._payload_to_int(payload, payload_key)
            if not value:
                continue
            operator = "in" if domain_field in {"category_ids", "tag_ids", "collaborator_ids"} else "="
            domain.append((domain_field, operator, value))
        return domain

    @api.model
    def _append_scalar_payload_filters(self, domain, payload):
        if payload.get("state"):
            domain.append(("state", "=", payload["state"]))
        if payload.get("visibility"):
            domain.append(("visibility", "=", payload["visibility"]))
        if payload.get("favorites_only"):
            domain.append(("favorite_user_ids", "in", self.env.user.id))
        return domain

    @api.model
    def _append_company_scope_payload_filter(self, domain, payload):
        company_id = self._payload_to_int(payload, "company_id")
        if company_id:
            domain.extend(["|", ("is_global", "=", True), ("company_id", "=", company_id)])
        return domain

    @api.model
    def _append_branch_payload_filter(self, domain, payload):
        article_branch_id = self._payload_to_int(payload, "article_branch_id")
        if article_branch_id:
            domain.append(("id", "child_of", article_branch_id))
        return domain

    @api.model
    def _append_payload_domain_filters(self, domain, payload):
        domain = list(domain)
        self._append_relation_payload_filters(domain, payload)
        self._append_scalar_payload_filters(domain, payload)
        self._append_company_scope_payload_filter(domain, payload)
        self._append_branch_payload_filter(domain, payload)
        return domain

    @api.model
    def _search_domain_from_payload(self, payload=None):
        payload = payload or {}
        search_term = (payload.get("search") or "").strip()
        domain = self._get_search_domain_for_term(search_term)
        return self._append_payload_domain_filters(domain, payload)

    @api.model
    def _get_article_preview(self, article, limit=240):
        return tools.ustr(article.body_plaintext or "")[:limit]

    @api.model
    def _article_card_data(self, article):
        return {
            "id": article.id,
            "name": article.name,
            "subtitle": article.subtitle or "",
            "state": article.state,
            "visibility": article.visibility,
            "display_path": article.display_path,
            "write_date": fields.Datetime.to_string(article.write_date) if article.write_date else "",
            "author_name": article.author_id.name or "",
            "owner_name": article.owner_id.name or "",
            "company_name": article.company_id.name or _("Global"),
            "is_favorite": article.is_favorite,
            "is_locked": article.is_locked,
            "category_names": article.category_ids.mapped("name")[:3],
            "tag_names": article.tag_ids.mapped("name")[:4],
            "preview": self._get_article_preview(article),
        }

    @api.model
    def _get_article_count_for_category(self, category):
        return self.search_count([("category_ids", "in", category.id)])

    @api.model
    def _get_article_count_for_tag(self, tag):
        return self.search_count([("tag_ids", "in", tag.id)])

    @api.model
    def _serialize_sidebar_category(self, category):
        return {
            "id": category.id,
            "name": category.complete_name,
            "color": category.color,
            "icon": category.icon or "fa fa-folder-open-o",
            "count": self._get_article_count_for_category(category),
        }

    @api.model
    def _sidebar_category_data(self, categories):
        return [self._serialize_sidebar_category(category) for category in categories]

    @api.model
    def _serialize_sidebar_tag(self, tag):
        return {
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "count": self._get_article_count_for_tag(tag),
        }

    @api.model
    def _sidebar_tag_data(self, tags):
        return [self._serialize_sidebar_tag(tag) for tag in tags]

    @api.model
    def _sorted_child_articles(self, article):
        return article.child_ids.sorted(key=lambda record: (record.sequence, record.name or "", -record.id))

    @api.model
    def _article_contains_selected_descendant(self, article, selected_article_id):
        if not selected_article_id:
            return False
        return bool(self.search_count([("id", "=", selected_article_id), ("id", "child_of", article.id)]))

    @api.model
    def _serialize_article_tree_node(self, article, selected_article_id=False, max_depth=4, current_depth=0):
        children = []
        if current_depth < max_depth:
            children = [
                self._serialize_article_tree_node(
                    child,
                    selected_article_id=selected_article_id,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                )
                for child in self._sorted_child_articles(article)
            ]
        return {
            "id": article.id,
            "name": article.name,
            "state": article.state,
            "is_favorite": article.is_favorite,
            "child_count": article.child_count,
            "is_selected": bool(selected_article_id and article.id == selected_article_id),
            "is_in_selected_path": self._article_contains_selected_descendant(article, selected_article_id),
            "children": children,
        }

    @api.model
    def _sidebar_article_tree(self, root_articles, selected_article_id=None, max_depth=4, current_depth=0):
        if current_depth >= max_depth:
            return []
        selected_article_id = int(selected_article_id) if selected_article_id else False
        return [
            self._serialize_article_tree_node(
                article,
                selected_article_id=selected_article_id,
                max_depth=max_depth,
                current_depth=current_depth,
            )
            for article in root_articles
        ]

    @api.model
    def _serialize_category_branch_articles(self, articles, selected_article_id=False, current_depth=0, max_depth=4):
        if current_depth >= max_depth:
            return []
        serialized = []
        for article in articles:
            serialized.append(
                {
                    "id": article.id,
                    "name": article.name,
                    "child_count": article.child_count,
                    "is_selected": bool(selected_article_id and article.id == selected_article_id),
                    "is_in_selected_path": self._article_contains_selected_descendant(article, selected_article_id),
                    "children": self._serialize_category_branch_articles(
                        self._sorted_child_articles(article),
                        selected_article_id=selected_article_id,
                        current_depth=current_depth + 1,
                        max_depth=max_depth,
                    ),
                }
            )
        return serialized

    @api.model
    def _get_root_articles_for_category(self, category, limit=10):
        return self.search(
            [("category_ids", "in", category.id), ("parent_id", "=", False)],
            limit=limit,
            order="sequence, name, id",
        )

    @api.model
    def _serialize_category_tree_node(self, category, selected_category_id=False, selected_article_id=False):
        return {
            "id": category.id,
            "name": category.name,
            "count": self._get_article_count_for_category(category),
            "is_selected": bool(selected_category_id and category.id == selected_category_id),
            "children": [
                self._serialize_category_tree_node(
                    child,
                    selected_category_id=selected_category_id,
                    selected_article_id=selected_article_id,
                )
                for child in category.child_ids.sorted(key=lambda record: (record.sequence, record.name or "", record.id))
            ],
            "articles": self._serialize_category_branch_articles(
                self._get_root_articles_for_category(category),
                selected_article_id=selected_article_id,
            ),
        }

    @api.model
    def _sidebar_category_article_tree(self, categories, selected_category_id=None, selected_article_id=None):
        selected_category_id = int(selected_category_id) if selected_category_id else False
        selected_article_id = int(selected_article_id) if selected_article_id else False
        return [
            self._serialize_category_tree_node(
                category,
                selected_category_id=selected_category_id,
                selected_article_id=selected_article_id,
            )
            for category in categories
        ]

    def _get_category_model_names(self, category):
        model_names = set()
        current_category = category
        while current_category:
            model_names.update(current_category.model_ids.mapped("model"))
            current_category = current_category.parent_id
        return model_names

    def _related_model_names(self):
        self.ensure_one()
        model_names = set(self.link_ids.mapped("res_model"))
        for category in self.category_ids:
            model_names.update(self._get_category_model_names(category))
        if self.parent_id:
            model_names.update(self.parent_id._related_model_names())
        return {name for name in model_names if name}

    @api.model
    def get_article_ids_for_related_model(self, res_model):
        return self.search([]).filtered(lambda article: res_model in article._related_model_names()).ids

    @api.model
    def action_open_for_related_model(self, res_model, action_name=None):
        article_ids = self.get_article_ids_for_related_model(res_model)
        action = self.env["ir.actions.actions"]._for_xml_id("wex_knowledge.action_knowledge_article_library")
        action.update(
            {
                "name": action_name or _("Art?culos relacionados"),
                "domain": [("id", "in", article_ids)],
                "context": {"search_default_published": 0},
            }
        )
        return action

    @api.model
    def _get_dashboard_count_payload(self):
        current_user = self.env.user
        return {
            "articles": self.search_count([]),
            "drafts": self.search_count([("state", "=", "draft")]),
            "published": self.search_count([("state", "=", "published")]),
            "favorites": self.search_count([("favorite_user_ids", "in", current_user.id)]),
        }

    @api.model
    def _get_dashboard_quick_links(self):
        return [
            {"label": _("Todos los art?culos"), "action_xmlid": "wex_knowledge.action_knowledge_explorer"},
            {
                "label": _("Mis favoritos"),
                "action_xmlid": "wex_knowledge.action_knowledge_explorer",
                "favorites_only": True,
            },
            {"label": _("Explorar art?culos"), "action_xmlid": "wex_knowledge.action_knowledge_explorer"},
        ]

    @api.model
    def _get_dashboard_articles(self, domain=None, order="write_date desc, id desc", limit=None):
        return self.search(domain or [], limit=limit or self._DASHBOARD_SECTION_LIMIT, order=order)

    @api.model
    def _serialize_article_cards(self, articles):
        return [self._article_card_data(article) for article in articles]

    @api.model
    def get_dashboard_data(self):
        recent_articles = self._get_dashboard_articles(order="create_date desc, id desc")
        updated_articles = self._get_dashboard_articles(order="write_date desc, id desc")
        favorite_articles = self._get_dashboard_articles(
            domain=[("favorite_user_ids", "in", self.env.user.id)],
            order="write_date desc, id desc",
            limit=6,
        )
        categories = self.env["wex.knowledge.category"].search([], limit=6, order="sequence, name")
        return {
            "counts": self._get_dashboard_count_payload(),
            "recent_articles": self._serialize_article_cards(recent_articles),
            "updated_articles": self._serialize_article_cards(updated_articles),
            "favorite_articles": self._serialize_article_cards(favorite_articles),
            "categories": self._sidebar_category_data(categories),
            "quick_links": self._get_dashboard_quick_links(),
        }

    @api.model
    def _serialize_people_sidebar_users(self, users, limit=20):
        return [{"id": user.id, "name": user.name} for user in users[:limit]]

    @api.model
    def _get_explorer_sidebar_people(self):
        all_articles = self.search([])
        collaborator_articles = self.search([("collaborator_ids", "!=", False)])
        return {
            "authors": self._serialize_people_sidebar_users(all_articles.mapped("author_id")),
            "owners": self._serialize_people_sidebar_users(all_articles.mapped("owner_id")),
            "collaborators": self._serialize_people_sidebar_users(collaborator_articles.mapped("collaborator_ids")),
        }

    @api.model
    def _get_sidebar_company_data(self):
        return [{"id": company.id, "name": company.name} for company in self.env.user.company_ids]

    @api.model
    def _get_explorer_sidebar_data(self, payload):
        categories = self.env["wex.knowledge.category"].search([], order="sequence, name", limit=15)
        tags = self.env["wex.knowledge.tag"].search([], order="name", limit=20)
        tree_roots = self.search([("parent_id", "=", False)], limit=20, order="sequence, name, id")
        category_roots = self.env["wex.knowledge.category"].search(
            [("parent_id", "=", False)],
            order="sequence, name",
            limit=12,
        )
        people = self._get_explorer_sidebar_people()
        return {
            "article_tree": self._sidebar_article_tree(
                tree_roots,
                selected_article_id=payload.get("article_branch_id"),
            ),
            "category_article_tree": self._sidebar_category_article_tree(
                category_roots,
                selected_category_id=payload.get("category_id"),
                selected_article_id=payload.get("article_branch_id"),
            ),
            "categories": self._sidebar_category_data(categories),
            "tags": self._sidebar_tag_data(tags),
            "authors": people["authors"],
            "owners": people["owners"],
            "collaborators": people["collaborators"],
            "companies": self._get_sidebar_company_data(),
        }

    @api.model
    def get_explorer_data(self, payload=None):
        payload = payload or {}
        domain = self._search_domain_from_payload(payload)
        articles = self.search(domain, limit=60, order="write_date desc, id desc")
        return {
            "filters": payload,
            "total_count": self.search_count(domain),
            "articles": [self._article_card_data(article) for article in articles],
            "sidebar": self._get_explorer_sidebar_data(payload),
        }
