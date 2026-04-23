from odoo import fields, models


class KnowledgePortalAccessLog(models.Model):
    _name = "wex.knowledge.portal.access.log"
    _description = "Knowledge Portal Access Log"
    _order = "accessed_at desc, id desc"

    article_id = fields.Many2one(
        comodel_name="wex.knowledge.article",
        required=True,
        index=True,
        ondelete="cascade",
    )
    access_type = fields.Selection(
        [
            ("portal", "Portal"),
            ("public_link", "Public Link"),
        ],
        required=True,
        index=True,
    )
    user_id = fields.Many2one("res.users", index=True, readonly=True)
    partner_id = fields.Many2one("res.partner", index=True, readonly=True)
    commercial_partner_id = fields.Many2one("res.partner", index=True, readonly=True)
    access_token_hint = fields.Char(readonly=True)
    ip_address = fields.Char(readonly=True)
    user_agent = fields.Char(readonly=True)
    accessed_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True, readonly=True)
