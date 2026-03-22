from odoo.exceptions import AccessError, ValidationError
from odoo.tests import SavepointCase, tagged


@tagged("post_install", "-at_install")
class TestKnowledgeArticle(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "Knowledge Test B"})
        cls.group_user = cls.env.ref("wex_knowledge.group_knowledge_user")
        cls.group_editor = cls.env.ref("wex_knowledge.group_knowledge_editor")
        cls.group_manager = cls.env.ref("wex_knowledge.group_knowledge_manager")
        cls.extra_group = cls.env["res.groups"].create({"name": "Knowledge Restricted Readers"})
        cls.repair_model = cls.env["ir.model"]._get("repair.order")
        cls.purchase_model = cls.env["ir.model"]._get("purchase.order")
        cls.stock_model = cls.env["ir.model"]._get("stock.picking")
        cls.sale_model = cls.env["ir.model"]._get("sale.order")
        cls.product_model = cls.env["ir.model"]._get("product.template")

        cls.user_a = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Knowledge User A",
            "login": "knowledge.user.a",
            "email": "knowledge.user.a@example.com",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id])],
            "groups_id": [(6, 0, [cls.group_user.id, cls.extra_group.id])],
        })
        cls.user_b = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Knowledge User B",
            "login": "knowledge.user.b",
            "email": "knowledge.user.b@example.com",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id])],
            "groups_id": [(6, 0, [cls.group_user.id])],
        })
        cls.user_company_b = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Knowledge User B Company",
            "login": "knowledge.user.company.b",
            "email": "knowledge.user.company.b@example.com",
            "company_id": cls.company_b.id,
            "company_ids": [(6, 0, [cls.company_b.id])],
            "groups_id": [(6, 0, [cls.group_user.id])],
        })
        cls.editor = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Knowledge Editor",
            "login": "knowledge.editor",
            "email": "knowledge.editor@example.com",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id])],
            "groups_id": [(6, 0, [cls.group_editor.id])],
        })
        cls.manager = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Knowledge Manager",
            "login": "knowledge.manager",
            "email": "knowledge.manager@example.com",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id, cls.company_b.id])],
            "groups_id": [(6, 0, [cls.group_manager.id])],
        })

        cls.category = cls.env["wex.knowledge.category"].with_user(cls.manager).create({
            "name": "SAT",
            "company_id": cls.company_a.id,
            "is_global": False,
        })
        cls.global_category = cls.env["wex.knowledge.category"].with_user(cls.manager).create({
            "name": "Global Docs",
            "company_id": False,
            "is_global": True,
        })
        cls.category_b = cls.env["wex.knowledge.category"].with_user(cls.manager).create({
            "name": "Empresa B",
            "company_id": cls.company_b.id,
            "is_global": False,
        })
        cls.model_category = cls.env["wex.knowledge.category"].with_user(cls.manager).create({
            "name": "Operativa SAT",
            "company_id": cls.company_a.id,
            "model_ids": [(6, 0, [cls.repair_model.id])],
        })
        cls.tag = cls.env["wex.knowledge.tag"].with_user(cls.user_a).create({
            "name": "Recepci?n",
            "company_id": cls.company_a.id,
        })
        cls.tag_b = cls.env["wex.knowledge.tag"].with_user(cls.manager).create({
            "name": "Empresa B",
            "company_id": cls.company_b.id,
        })

    def test_article_creation_defaults_and_hierarchy(self):
        parent = self.env["wex.knowledge.article"].with_user(self.user_a).create({
            "name": "Recepci?n SAT",
            "subtitle": "Base del procedimiento",
            "body_html": "<p>Contenido principal</p>",
            "category_ids": [(6, 0, [self.category.id])],
            "tag_ids": [(6, 0, [self.tag.id])],
        })
        child = self.env["wex.knowledge.article"].with_user(self.user_a).create({
            "name": "Checklist de admisi?n",
            "body_html": "<p>Checklist</p>",
            "parent_id": parent.id,
        })
        self.assertEqual(parent.author_id, self.user_a)
        self.assertEqual(parent.owner_id, self.user_a)
        self.assertEqual(parent.last_editor_id, self.user_a)
        self.assertIn(child, parent.child_ids)
        self.assertEqual(child.display_path, "Recepci?n SAT / Checklist de admisi?n")

    def test_private_visibility_rules(self):
        private_article = self.env["wex.knowledge.article"].with_user(self.user_a).create({
            "name": "Diagn?stico privado",
            "body_html": "<p>Privado</p>",
            "visibility": "private",
        })
        visible_to_author = self.env["wex.knowledge.article"].with_user(self.user_a).search([("id", "=", private_article.id)])
        visible_to_other = self.env["wex.knowledge.article"].with_user(self.user_b).search([("id", "=", private_article.id)])
        self.assertTrue(visible_to_author)
        self.assertFalse(visible_to_other)

    def test_by_group_visibility_rules(self):
        article = self.env["wex.knowledge.article"].with_user(self.editor).create({
            "name": "Gu?a restringida",
            "body_html": "<p>Visible solo a un grupo</p>",
            "visibility": "by_group",
            "allowed_group_ids": [(6, 0, [self.extra_group.id])],
        })
        self.assertTrue(self.env["wex.knowledge.article"].with_user(self.user_a).search([("id", "=", article.id)]))
        self.assertFalse(self.env["wex.knowledge.article"].with_user(self.user_b).search([("id", "=", article.id)]))

    def test_favorite_toggle(self):
        article = self.env["wex.knowledge.article"].with_user(self.user_a).create({
            "name": "Art?culo favorito",
            "body_html": "<p>Fav</p>",
        })
        article.with_user(self.user_a).action_toggle_favorite()
        self.assertTrue(article.with_user(self.user_a).is_favorite)
        article.with_user(self.user_a).action_toggle_favorite()
        self.assertFalse(article.with_user(self.user_a).is_favorite)

    def test_multi_company_scope(self):
        company_b_article = self.env["wex.knowledge.article"].with_user(self.manager).create({
            "name": "Empresa B",
            "body_html": "<p>B</p>",
            "company_id": self.company_b.id,
        })
        global_article = self.env["wex.knowledge.article"].with_user(self.manager).create({
            "name": "Global",
            "body_html": "<p>Global</p>",
            "company_id": False,
            "is_global": True,
            "category_ids": [(6, 0, [self.global_category.id])],
        })
        visible_for_user_a = self.env["wex.knowledge.article"].with_user(self.user_a).search([("id", "in", (company_b_article | global_article).ids)])
        visible_for_manager = self.env["wex.knowledge.article"].with_user(self.manager).search([("id", "in", (company_b_article | global_article).ids)])
        self.assertEqual(visible_for_user_a, global_article)
        self.assertEqual(visible_for_manager, company_b_article | global_article)

    def test_cross_company_collaborator_cannot_bypass_company_scope(self):
        article = self.env["wex.knowledge.article"].with_user(self.manager).create({
            "name": "Solo empresa A",
            "body_html": "<p>A</p>",
            "company_id": self.company_a.id,
            "collaborator_ids": [(6, 0, [self.user_company_b.id])],
        })
        self.assertFalse(self.env["wex.knowledge.article"].with_user(self.user_company_b).search([("id", "=", article.id)]))

    def test_editor_can_publish_visible_article(self):
        article = self.env["wex.knowledge.article"].with_user(self.user_a).create({
            "name": "Borrador compartido",
            "body_html": "<p>Compartido</p>",
            "visibility": "internal",
        })
        article.with_user(self.editor).write({"state": "published"})
        self.assertEqual(article.state, "published")

    def test_locked_article_blocks_editor_but_manager_can_edit(self):
        article = self.env["wex.knowledge.article"].with_user(self.manager).create({
            "name": "Bloqueado",
            "body_html": "<p>Base</p>",
        })
        article.with_user(self.manager).action_lock()
        with self.assertRaises(AccessError):
            article.with_user(self.editor).write({"subtitle": "Intento editor"})
        article.with_user(self.manager).write({"subtitle": "Cambio manager"})
        self.assertEqual(article.subtitle, "Cambio manager")

    def test_category_model_inheritance_reaches_children(self):
        parent = self.env["wex.knowledge.article"].with_user(self.manager).create({
            "name": "Manual SAT",
            "body_html": "<p>Manual</p>",
            "category_ids": [(6, 0, [self.model_category.id])],
        })
        child = self.env["wex.knowledge.article"].with_user(self.manager).create({
            "name": "Paso SAT",
            "body_html": "<p>Paso</p>",
            "parent_id": parent.id,
        })
        article_ids = self.env["wex.knowledge.article"].with_user(self.user_a).get_article_ids_for_related_model("repair.order")
        self.assertIn(parent.id, article_ids)
        self.assertIn(child.id, article_ids)


    def test_related_model_resolution_for_additional_business_models(self):
        category = self.env["wex.knowledge.category"].with_user(self.manager).create({
            "name": "Operativa transversal",
            "company_id": self.company_a.id,
            "model_ids": [(6, 0, [
                self.purchase_model.id,
                self.stock_model.id,
                self.sale_model.id,
                self.product_model.id,
            ])],
        })
        article = self.env["wex.knowledge.article"].with_user(self.manager).create({
            "name": "Manual operativo general",
            "body_html": "<p>Proceso</p>",
            "category_ids": [(6, 0, [category.id])],
        })
        model_names = ["purchase.order", "stock.picking", "sale.order", "product.template"]
        article_model = self.env["wex.knowledge.article"].with_user(self.user_a)
        for model_name in model_names:
            self.assertIn(article.id, article_model.get_article_ids_for_related_model(model_name))

    def test_related_model_resolution_respects_private_visibility(self):
        category = self.env["wex.knowledge.category"].with_user(self.manager).create({
            "name": "Ventas privadas",
            "company_id": self.company_a.id,
            "model_ids": [(6, 0, [self.sale_model.id])],
        })
        article = self.env["wex.knowledge.article"].with_user(self.user_a).create({
            "name": "Gu?a privada de ventas",
            "body_html": "<p>Privado</p>",
            "visibility": "private",
            "category_ids": [(6, 0, [category.id])],
        })
        visible_ids = self.env["wex.knowledge.article"].with_user(self.user_a).get_article_ids_for_related_model("sale.order")
        hidden_ids = self.env["wex.knowledge.article"].with_user(self.user_b).get_article_ids_for_related_model("sale.order")
        self.assertIn(article.id, visible_ids)
        self.assertNotIn(article.id, hidden_ids)

    def test_taxonomy_scope_constraints(self):
        with self.assertRaises(ValidationError):
            self.env["wex.knowledge.article"].with_user(self.manager).create({
                "name": "Global mal etiquetado",
                "body_html": "<p>Global</p>",
                "company_id": False,
                "is_global": True,
                "tag_ids": [(6, 0, [self.tag.id])],
                "category_ids": [(6, 0, [self.global_category.id])],
            })
        with self.assertRaises(ValidationError):
            self.env["wex.knowledge.article"].with_user(self.manager).create({
                "name": "Categor?a de otra empresa",
                "body_html": "<p>Error</p>",
                "company_id": self.company_a.id,
                "category_ids": [(6, 0, [self.category_b.id])],
            })
        with self.assertRaises(ValidationError):
            self.env["wex.knowledge.article"].with_user(self.manager).create({
                "name": "Tag de otra empresa",
                "body_html": "<p>Error</p>",
                "company_id": self.company_a.id,
                "tag_ids": [(6, 0, [self.tag_b.id])],
            })
