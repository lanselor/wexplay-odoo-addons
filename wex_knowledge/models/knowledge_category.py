from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class KnowledgeCategory(models.Model):
    _name = "wex.knowledge.category"
    _description = "Knowledge Category"
    _order = "sequence, name, id"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "complete_name"

    _ICON_SELECTION = [
        ("fa fa-book", "Libro"),
        ("fa fa-folder-open", "Carpeta"),
        ("fa fa-question-circle", "FAQ"),
        ("fa fa-graduation-cap", "Tutorial"),
        ("fa fa-lightbulb-o", "Buenas prácticas"),
        ("fa fa-wrench", "Herramientas"),
        ("fa fa-life-ring", "Soporte"),
        ("fa fa-cogs", "Procesos"),
        ("fa fa-file-text-o", "Documento"),
        ("fa fa-bolt", "Operaciones"),
        ("fa fa-bug", "Incidencias"),
        ("fa fa-shopping-bag", "Comercial"),
        ("fa fa-truck", "Logística"),
        ("fa fa-shield", "Calidad"),
        ("fa fa-line-chart", "Análisis"),
    ]

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    parent_id = fields.Many2one("wex.knowledge.category", ondelete="restrict", index=True)
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("wex.knowledge.category", "parent_id")
    sequence = fields.Integer(default=10)
    color = fields.Integer(default=0)
    icon = fields.Char(help="Clase CSS del icono, por ejemplo: fa fa-book")
    icon_preset = fields.Selection(selection=_ICON_SELECTION, string="Icono sugerido")
    icon_preview = fields.Char(compute="_compute_icon_preview", string="Vista previa")
    company_id = fields.Many2one("res.company", index=True, default=lambda self: self.env.company)
    is_global = fields.Boolean(default=False)
    active = fields.Boolean(default=True)
    model_ids = fields.Many2many(
        "ir.model",
        "wex_knowledge_category_model_rel",
        "category_id",
        "model_id",
        string="Modelos relacionados",
        domain=[("transient", "=", False)],
    )
    article_ids = fields.Many2many(
        "wex.knowledge.article",
        "wex_knowledge_article_category_rel",
        "category_id",
        "article_id",
        string="Articles",
    )
    article_count = fields.Integer(compute="_compute_article_count")
    complete_name = fields.Char(compute="_compute_complete_name", store=True, recursive=True)

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = "%s / %s" % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    @api.onchange("icon_preset")
    def _onchange_icon_preset(self):
        for category in self:
            if category.icon_preset:
                category.icon = category.icon_preset

    @api.onchange("icon")
    def _onchange_icon(self):
        valid_icons = {value for value, _label in self._ICON_SELECTION}
        for category in self:
            category.icon_preset = category.icon if category.icon in valid_icons else False

    @api.depends("icon")
    def _compute_icon_preview(self):
        fallback = "fa fa-folder-open"
        for category in self:
            category.icon_preview = category.icon or fallback

    def _compute_article_count(self):
        article_model = self.env["wex.knowledge.article"]
        for category in self:
            category.article_count = article_model.search_count([("category_ids", "in", category.id)])

    @api.constrains("company_id", "is_global")
    def _check_company_scope(self):
        for category in self:
            if category.is_global and category.company_id:
                raise ValidationError(_("A global category cannot be assigned to a company."))
            if not category.is_global and not category.company_id:
                raise ValidationError(_("A non-global category must belong to a company."))

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_("You cannot create recursive category hierarchies."))
