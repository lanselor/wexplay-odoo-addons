from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class KnowledgeArticleLink(models.Model):
    _name = "wex.knowledge.article.link"
    _description = "Knowledge Article Link"
    _order = "id desc"

    article_id = fields.Many2one("wex.knowledge.article", required=True, ondelete="cascade", index=True)
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade", string="Related Model", domain=[("transient", "=", False)])
    res_model = fields.Char(related="model_id.model", store=True, index=True)
    res_id = fields.Many2oneReference(string="Related Record", model_field="res_model")
    note = fields.Char()
    company_id = fields.Many2one(related="article_id.company_id", store=True)
    target_display_name = fields.Char(compute="_compute_target_display_name")

    @api.onchange("model_id")
    def _onchange_model_id(self):
        for link in self:
            link.res_id = False

    @api.depends("model_id", "res_model", "res_id")
    def _compute_target_display_name(self):
        for link in self:
            target = link._get_target_record()
            if target:
                link.target_display_name = target.display_name
            else:
                link.target_display_name = link.model_id.name or _("Missing record")

    def _get_target_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return self.env[self._name].browse()
        return self.env[self.res_model].browse(self.res_id).exists()

    @api.constrains("res_model", "res_id")
    def _check_target_exists(self):
        for link in self:
            if link.res_id and not link._get_target_record():
                raise ValidationError(_("The related record does not exist."))

    def action_open_target(self):
        self.ensure_one()
        record = self._get_target_record()
        if record:
            return {
                "type": "ir.actions.act_window",
                "name": record.display_name,
                "res_model": record._name,
                "res_id": record.id,
                "view_mode": "form",
                "target": "current",
            }
        if not self.res_model:
            raise ValidationError(_("The related model is not configured."))
        return {
            "type": "ir.actions.act_window",
            "name": self.model_id.name,
            "res_model": self.res_model,
            "view_mode": "list,form",
            "target": "current",
        }
