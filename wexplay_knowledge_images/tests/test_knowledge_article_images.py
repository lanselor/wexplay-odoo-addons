# -*- coding: utf-8 -*-

from odoo.tests.common import SavepointCase


class TestKnowledgeArticleImages(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.storage = cls.env["dms.storage"].create(
            {
                "name": "Knowledge Images Test Storage",
                "save_type": "database",
            }
        )
        cls.company = cls.env.company
        cls.company.x_wex_knowledge_images_dms_storage_id = cls.storage

        cls.group_user = cls.env.ref("wex_knowledge.group_knowledge_user")
        cls.group_editor = cls.env.ref("wex_knowledge.group_knowledge_editor")

        cls.user_a = cls.env["res.users"].create(
            {
                "name": "Knowledge User A",
                "login": "knowledge_user_a",
                "email": "knowledge_user_a@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.group_user.id])],
                "company_id": cls.company.id,
                "company_ids": [(6, 0, cls.company.ids)],
            }
        )
        cls.user_b = cls.env["res.users"].create(
            {
                "name": "Knowledge User B",
                "login": "knowledge_user_b",
                "email": "knowledge_user_b@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.group_user.id])],
                "company_id": cls.company.id,
                "company_ids": [(6, 0, cls.company.ids)],
            }
        )
        cls.editor = cls.env["res.users"].create(
            {
                "name": "Knowledge Editor",
                "login": "knowledge_editor",
                "email": "knowledge_editor@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.group_editor.id])],
                "company_id": cls.company.id,
                "company_ids": [(6, 0, cls.company.ids)],
            }
        )

    def test_upload_wizard_creates_image_in_dms_and_appends_html(self):
        article = self.env["wex.knowledge.article"].with_user(self.user_a).create(
            {
                "name": "Manual SAT",
                "body_html": "<p>Inicio</p>",
            }
        )
        wizard = self.env["wex.knowledge.article.image.upload.wizard"].with_user(self.user_a).create(
            {
                "article_id": article.id,
                "name": "Foto principal",
                "filename": "foto-principal.png",
                "image_file": "ZmFrZV9pbWFnZQ==",
            }
        )

        wizard.action_upload_image()

        image = self.env["wex.knowledge.article.image"].search([("article_id", "=", article.id)], limit=1)
        self.assertTrue(image)
        self.assertEqual(image.dms_file_id.directory_id.name, "IMAGES")
        self.assertEqual(image.dms_file_id.directory_id.parent_id.name, article.name)
        self.assertEqual(image.dms_file_id.directory_id.parent_id.parent_id.name, "KNOWLEDGE")
        self.assertEqual(image.name, "Manual SAT - Image 1")
        self.assertEqual(image.dms_file_name, "manual-sat-image-1.png")
        self.assertIn("/wex_knowledge/image/%s/" % image.id, article.body_html)

    def test_private_article_media_access_follows_article_visibility(self):
        article = self.env["wex.knowledge.article"].with_user(self.user_a).create(
            {
                "name": "Privado",
                "body_html": "<p>Privado</p>",
                "visibility": "private",
            }
        )
        image = self.env["wex.knowledge.article.image"].with_user(self.user_a).create_embedded_image_from_binary(
            article=article,
            name="Imagen privada",
            filename="privada.png",
            binary_content="ZmFrZV9pbWFnZQ==",
        )

        self.assertTrue(article.with_user(self.user_a)._user_can_read_record(self.user_a))
        self.assertFalse(article.with_user(self.user_b)._user_can_read_record(self.user_b))
        self.assertEqual(image.article_id.id, article.id)

    def test_second_embedded_image_uses_next_automatic_name(self):
        article = self.env["wex.knowledge.article"].with_user(self.user_a).create(
            {
                "name": "Recepcion",
                "body_html": "<p>Base</p>",
            }
        )

        first = self.env["wex.knowledge.article.image"].with_user(self.user_a).create_embedded_image_from_binary(
            article=article,
            name=article._build_embedded_image_name(article._get_next_embedded_image_index()),
            filename=article._build_embedded_image_filename("foto.png", article._get_next_embedded_image_index()),
            binary_content="ZmFrZV9pbWFnZQ==",
        )
        second = self.env["wex.knowledge.article.image"].with_user(self.user_a).create_embedded_image_from_binary(
            article=article,
            name=article._build_embedded_image_name(article._get_next_embedded_image_index()),
            filename=article._build_embedded_image_filename("foto.png", article._get_next_embedded_image_index()),
            binary_content="ZmFrZV9pbWFnZQ==",
        )

        self.assertEqual(first.name, "Recepcion - Image 1")
        self.assertEqual(second.name, "Recepcion - Image 2")
        self.assertEqual(first.dms_file_name, "recepcion-image-1.png")
        self.assertEqual(second.dms_file_name, "recepcion-image-2.png")

    def test_deleting_embedded_image_removes_dms_file_and_html_reference(self):
        article = self.env["wex.knowledge.article"].with_user(self.user_a).create(
            {
                "name": "Borrado",
                "body_html": "<p>Base</p>",
            }
        )
        image = self.env["wex.knowledge.article.image"].with_user(self.user_a).create_embedded_image_from_binary(
            article=article,
            name=article._build_embedded_image_name(article._get_next_embedded_image_index()),
            filename=article._build_embedded_image_filename("foto.png", article._get_next_embedded_image_index()),
            binary_content="ZmFrZV9pbWFnZQ==",
        )
        article.write({"body_html": "<p>Base</p>%s" % image._build_embedded_html()})
        dms_file = image.dms_file_id

        image.with_user(self.user_a).action_delete_image()

        self.assertFalse(self.env["wex.knowledge.article.image"].search([("id", "=", image.id)]))
        self.assertFalse(self.env["dms.file"].search([("id", "=", dms_file.id)]))
        self.assertNotIn(image.image_url, article.body_html)
