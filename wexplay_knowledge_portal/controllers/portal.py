# -*- coding: utf-8 -*-

from werkzeug.exceptions import NotFound

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request
from odoo.osv import expression


class WexplayKnowledgePortal(CustomerPortal):
    def _get_portal_parent_article(self, article):
        parent_article = article.parent_id
        if not parent_article:
            return article.browse()
        return parent_article if parent_article._can_user_read_portal_article(request.env.user) else article.browse()

    def _get_public_parent_article(self, article):
        parent_article = article.parent_id
        if not parent_article:
            return article.browse()
        if not parent_article.public_access_token:
            return article.browse()
        return parent_article if parent_article._can_read_public_article(parent_article.public_access_token) else article.browse()

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "knowledge_count" in counters:
            values["knowledge_count"] = request.env["wex.knowledge.article"].sudo().search_count(
                request.env["wex.knowledge.article"].sudo()._get_portal_visible_domain(request.env.user)
            )
        return values

    def _get_portal_knowledge_domain(self, user=None, search=None):
        article_model = request.env["wex.knowledge.article"].sudo()
        return expression.AND(
            [
                article_model._get_portal_visible_domain(user or request.env.user),
                article_model._get_portal_search_domain(search),
            ]
        )

    def _get_portal_knowledge_article_or_404(self, article_id):
        article = request.env["wex.knowledge.article"].sudo().search(
            self._get_portal_knowledge_domain() + [("id", "=", article_id)],
            limit=1,
        )
        if not article:
            raise NotFound()
        return article

    @http.route(
        ["/my/knowledge", "/my/knowledge/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_knowledge(self, page=1, search=None, **kw):
        article_model = request.env["wex.knowledge.article"].sudo()
        values = self._prepare_portal_layout_values()
        search = (search or "").strip()
        domain = self._get_portal_knowledge_domain(search=search)
        article_count = article_model.search_count(domain)
        pager = portal_pager(
            url="/my/knowledge",
            url_args={"search": search} if search else {},
            total=article_count,
            page=page,
            step=self._items_per_page,
        )
        articles = article_model.search(
            domain,
            order="sequence, write_date desc, id desc",
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        values.update(
            {
                "page_name": "knowledge",
                "default_url": "/my/knowledge",
                "pager": pager,
                "articles": articles,
                "knowledge_count": article_count,
                "search": search,
            }
        )
        return request.render("wexplay_knowledge_portal.portal_my_knowledge", values)

    @http.route(
        ["/my/knowledge/<int:article_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_knowledge_page(self, article_id, **kw):
        article = self._get_portal_knowledge_article_or_404(article_id)
        article.log_external_access("portal", user=request.env.user)
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "knowledge_detail",
                "article": article,
                "parent_article": self._get_portal_parent_article(article),
                "sub_articles": article._get_portal_sub_articles(request.env.user),
                "related_articles": article._get_portal_related_articles(request.env.user),
            }
        )
        return request.render("wexplay_knowledge_portal.portal_knowledge_page", values)

    @http.route(
        ["/knowledge/public/<string:access_token>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def public_knowledge_page(self, access_token, **kw):
        article = request.env["wex.knowledge.article"].sudo().search(
            request.env["wex.knowledge.article"].sudo()._get_public_visible_domain()
            + [("public_access_token", "=", access_token)],
            limit=1,
        )
        if not article or not article._can_read_public_article(access_token):
            raise NotFound()

        article.log_external_access("public_link", access_token=access_token)
        response = request.render(
            "wexplay_knowledge_portal.public_knowledge_page",
            {
                "article": article,
                "parent_article": self._get_public_parent_article(article),
                "sub_articles": article._get_public_sub_articles(),
                "related_articles": article._get_public_related_articles(),
            },
        )
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response
