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



    @api.depends("author_id", "owner_id", "collaborator_ids", "is_locked")

    def _compute_permissions(self):

        current_user = self.env.user

        is_editor = self._user_is_editor(current_user)

        is_manager = self._user_is_manager(current_user)

        for article in self:

            article.can_edit = article._user_can_edit_record(current_user)

            article.can_manage_relations = is_manager or is_editor

            article.can_change_lock = is_manager



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



    @api.model_create_multi

    def create(self, vals_list):

        current_user = self.env.user

        is_editor = self._user_is_editor(current_user)

        is_manager = self._user_is_manager(current_user)

        for vals in vals_list:

            vals.setdefault("author_id", current_user.id)

            vals.setdefault("owner_id", current_user.id)

            vals.setdefault("last_editor_id", current_user.id)

            if not is_editor and self._EDITOR_RESTRICTED_FIELDS.intersection(vals):

                raise AccessError(_("Only editors can configure workflow, ownership and generic relations."))

            if not is_manager and self._MANAGER_RESTRICTED_FIELDS.intersection(vals):

                raise AccessError(_("Only managers can manage locks and company scope."))

        return super().create(vals_list)



    def write(self, vals):

        current_user = self.env.user

        is_editor = self._user_is_editor(current_user)

        is_manager = self._user_is_manager(current_user)

        if not is_editor and self._EDITOR_RESTRICTED_FIELDS.intersection(vals):

            raise AccessError(_("Only editors can change workflow, ownership, collaborators and related record links."))

        if not is_manager and self._MANAGER_RESTRICTED_FIELDS.intersection(vals):

            raise AccessError(_("Only managers can change locks and company scope."))

        if self._EDITORIAL_FIELDS.intersection(vals):

            for article in self:

                if not article._user_can_edit_record(current_user):

                    raise AccessError(_("You do not have permission to edit the selected article."))

            vals = dict(vals, last_editor_id=current_user.id)

        return super().write(vals)



    def unlink(self):

        if not self._user_is_manager():

            raise AccessError(_("Only managers can delete knowledge articles."))

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



    def action_lock(self):

        if not self._user_is_manager():

            raise AccessError(_("Only managers can lock articles."))

        self.write({"is_locked": True})



    def action_unlock(self):

        if not self._user_is_manager():

            raise AccessError(_("Only managers can unlock articles."))

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

        payload = self.env.context.get("wex_kb_explorer_payload") or {}

        return {

            "type": "ir.actions.act_window",

            "name": _("Nuevo artículo hijo"),

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

        payload = self.env.context.get("wex_kb_explorer_payload") or {}

        action["context"] = {"wex_kb_explorer_payload": payload}

        return action



    @api.model

    def _search_domain_from_payload(self, payload=None):

        payload = payload or {}

        domain = []

        search_term = (payload.get("search") or "").strip()

        if search_term:

            domain = [

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

        if payload.get("category_id"):

            domain.append(("category_ids", "in", int(payload["category_id"])))

        if payload.get("tag_id"):

            domain.append(("tag_ids", "in", int(payload["tag_id"])))

        if payload.get("author_id"):

            domain.append(("author_id", "=", int(payload["author_id"])))

        if payload.get("owner_id"):

            domain.append(("owner_id", "=", int(payload["owner_id"])))

        if payload.get("collaborator_id"):

            domain.append(("collaborator_ids", "in", int(payload["collaborator_id"])))

        if payload.get("state"):

            domain.append(("state", "=", payload["state"]))

        if payload.get("visibility"):

            domain.append(("visibility", "=", payload["visibility"]))

        if payload.get("company_id"):

            company_id = int(payload["company_id"])

            domain.extend(["|", ("is_global", "=", True), ("company_id", "=", company_id)])

        if payload.get("favorites_only"):

            domain.append(("favorite_user_ids", "in", self.env.user.id))

        if payload.get("article_branch_id"):

            domain.append(("id", "child_of", int(payload["article_branch_id"])))

        return domain



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

            "preview": tools.ustr(article.body_plaintext or "")[:240],

        }



    @api.model

    def _sidebar_category_data(self, categories):

        return [

            {

                "id": category.id,

                "name": category.complete_name,

                "color": category.color,

                "icon": category.icon or "fa fa-folder-open-o",

                "count": self.search_count([("category_ids", "in", category.id)]),

            }

            for category in categories

        ]



    @api.model

    def _sidebar_tag_data(self, tags):

        return [

            {

                "id": tag.id,

                "name": tag.name,

                "color": tag.color,

                "count": self.search_count([("tag_ids", "in", tag.id)]),

            }

            for tag in tags

        ]



    @api.model

    def _sidebar_article_tree(self, root_articles, selected_article_id=None, max_depth=4, current_depth=0):

        if current_depth >= max_depth:

            return []

        selected_article_id = int(selected_article_id) if selected_article_id else False

        tree = []

        for article in root_articles:

            children = article.child_ids.sorted(key=lambda a: (a.sequence, a.name or "", -a.id))

            is_selected = bool(selected_article_id and article.id == selected_article_id)

            is_in_selected_path = bool(selected_article_id and selected_article_id in article.search([("id", "child_of", article.id)]).ids)

            tree.append({

                "id": article.id,

                "name": article.name,

                "state": article.state,

                "is_favorite": article.is_favorite,

                "child_count": article.child_count,

                "is_selected": is_selected,

                "is_in_selected_path": is_in_selected_path,

                "children": self._sidebar_article_tree(children, selected_article_id=selected_article_id, max_depth=max_depth, current_depth=current_depth + 1),

            })

        return tree


    @api.model

    def _sidebar_category_article_tree(self, categories, selected_category_id=None, selected_article_id=None):

        selected_category_id = int(selected_category_id) if selected_category_id else False

        selected_article_id = int(selected_article_id) if selected_article_id else False

        def serialize_articles(articles, current_depth=0, max_depth=4):

            if current_depth >= max_depth:

                return []

            serialized = []

            for article in articles:

                children = article.child_ids.sorted(key=lambda record: (record.sequence, record.name or "", -record.id))

                serialized.append({

                    "id": article.id,

                    "name": article.name,

                    "child_count": article.child_count,

                    "is_selected": bool(selected_article_id and article.id == selected_article_id),

                    "is_in_selected_path": bool(selected_article_id and selected_article_id in article.search([("id", "child_of", article.id)]).ids),

                    "children": serialize_articles(children, current_depth=current_depth + 1, max_depth=max_depth),

                })

            return serialized

        def serialize_category(category):

            root_articles = self.search([("category_ids", "in", category.id), ("parent_id", "=", False)], limit=10, order="sequence, name, id")

            return {

                "id": category.id,

                "name": category.name,

                "count": self.search_count([("category_ids", "in", category.id)]),

                "is_selected": bool(selected_category_id and category.id == selected_category_id),

                "children": [

                    serialize_category(child)

                    for child in category.child_ids.sorted(key=lambda record: (record.sequence, record.name or "", record.id))

                ],

                "articles": serialize_articles(root_articles),

            }

        return [serialize_category(category) for category in categories]



    def _related_model_names(self):

        self.ensure_one()

        model_names = set(self.link_ids.mapped("res_model"))

        for category in self.category_ids:

            current_category = category

            while current_category:

                model_names.update(current_category.model_ids.mapped("model"))

                current_category = current_category.parent_id

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

        action.update({

            "name": action_name or _("Art?culos relacionados"),

            "domain": [("id", "in", article_ids)],

            "context": {"search_default_published": 0},

        })

        return action



    @api.model

    def get_dashboard_data(self):

        recent_articles = self.search([], limit=self._DASHBOARD_SECTION_LIMIT, order="create_date desc, id desc")

        updated_articles = self.search([], limit=self._DASHBOARD_SECTION_LIMIT, order="write_date desc, id desc")

        favorite_articles = self.search([("favorite_user_ids", "in", self.env.user.id)], limit=6, order="write_date desc, id desc")

        categories = self.env["wex.knowledge.category"].search([], limit=6, order="sequence, name")

        return {

            "counts": {

                "articles": self.search_count([]),

                "drafts": self.search_count([("state", "=", "draft")]),

                "published": self.search_count([("state", "=", "published")]),

                "favorites": self.search_count([("favorite_user_ids", "in", self.env.user.id)]),

            },

            "recent_articles": [self._article_card_data(article) for article in recent_articles],

            "updated_articles": [self._article_card_data(article) for article in updated_articles],

            "favorite_articles": [self._article_card_data(article) for article in favorite_articles],

            "categories": self._sidebar_category_data(categories),

            "quick_links": [

                {"label": _("Todos los artículos"), "action_xmlid": "wex_knowledge.action_knowledge_explorer"},

                {"label": _("Mis favoritos"), "action_xmlid": "wex_knowledge.action_knowledge_explorer", "favorites_only": True},

                {"label": _("Explorar artículos"), "action_xmlid": "wex_knowledge.action_knowledge_explorer"},

            ],

        }



    @api.model

    def get_explorer_data(self, payload=None):

        payload = payload or {}

        domain = self._search_domain_from_payload(payload)

        articles = self.search(domain, limit=60, order="write_date desc, id desc")

        categories = self.env["wex.knowledge.category"].search([], order="sequence, name", limit=15)

        tags = self.env["wex.knowledge.tag"].search([], order="name", limit=20)

        authors = self.search([]).mapped("author_id")[:20]

        owners = self.search([]).mapped("owner_id")[:20]

        collaborators = self.search([("collaborator_ids", "!=", False)]).mapped("collaborator_ids")[:20]

        tree_roots = self.search([("parent_id", "=", False)], limit=20, order="sequence, name, id")

        category_roots = self.env["wex.knowledge.category"].search([("parent_id", "=", False)], order="sequence, name", limit=12)

        return {

            "filters": payload,

            "total_count": self.search_count(domain),

            "articles": [self._article_card_data(article) for article in articles],

            "sidebar": {

                "article_tree": self._sidebar_article_tree(tree_roots, selected_article_id=payload.get("article_branch_id")),

                "category_article_tree": self._sidebar_category_article_tree(category_roots, selected_category_id=payload.get("category_id"), selected_article_id=payload.get("article_branch_id")),

                "categories": self._sidebar_category_data(categories),

                "tags": self._sidebar_tag_data(tags),

                "authors": [{"id": user.id, "name": user.name} for user in authors],

                "owners": [{"id": user.id, "name": user.name} for user in owners],

                "collaborators": [{"id": user.id, "name": user.name} for user in collaborators],

                "companies": [{"id": company.id, "name": company.name} for company in self.env.user.company_ids],

            },

        }





