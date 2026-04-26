from odoo import fields, models


class KnowledgeArticleHistory(models.Model):
    _name = "wex.knowledge.article.history"
    _description = "Knowledge Article History"
    _order = "event_at desc, id desc"

    article_id = fields.Many2one(
        comodel_name="wex.knowledge.article",
        required=True,
        ondelete="cascade",
        index=True,
    )
    event_type = fields.Selection(
        [
            ("editorial", "Editorial"),
            ("publication", "Publicación"),
            ("security", "Seguridad"),
            ("system", "Sistema"),
        ],
        required=True,
        default="editorial",
        index=True,
        readonly=True,
    )
    description = fields.Char(required=True, readonly=True)
    user_id = fields.Many2one("res.users", readonly=True, index=True)
    event_at = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True, index=True)
