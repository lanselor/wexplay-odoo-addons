from odoo import _, api, fields, models


class RepairOrder(models.Model):
    _inherit = "repair.order"

    knowledge_article_count = fields.Integer(compute="_compute_knowledge_article_count")

    @api.depends()
    def _compute_knowledge_article_count(self):
        article_ids = self.env["wex.knowledge.article"].get_article_ids_for_related_model("repair.order")
        count = len(article_ids)
        for order in self:
            order.knowledge_article_count = count

    def action_view_knowledge_articles(self):
        self.ensure_one()
        return self.env["wex.knowledge.article"].action_open_for_related_model(
            "repair.order",
            action_name=_("Articulos de reparaciones"),
        )
