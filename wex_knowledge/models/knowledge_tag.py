from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class KnowledgeTag(models.Model):
    _name = "wex.knowledge.tag"
    _description = "Knowledge Tag"
    _order = "name, id"

    name = fields.Char(required=True, translate=True)
    normalized_name = fields.Char(required=True, copy=False, index=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)
    article_ids = fields.Many2many(
        "wex.knowledge.article",
        "wex_knowledge_article_tag_rel",
        "tag_id",
        "article_id",
        string="Articles",
    )

    _sql_constraints = [
        (
            "wex_knowledge_tag_normalized_company_uniq",
            "unique(normalized_name, company_id)",
            "A tag with the same name already exists in this company.",
        ),
    ]

    @api.model
    def _normalize_name(self, name):
        return " ".join((name or "").strip().lower().split())

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["normalized_name"] = self._normalize_name(vals.get("name"))
        return super().create(vals_list)

    def write(self, vals):
        if "name" in vals:
            vals["normalized_name"] = self._normalize_name(vals["name"])
        return super().write(vals)

    @api.constrains("name")
    def _check_name(self):
        for tag in self:
            if not tag._normalize_name(tag.name):
                raise ValidationError(_("A tag name cannot be empty."))
