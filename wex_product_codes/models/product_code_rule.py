from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WexProductCodeRule(models.Model):
    _name = "wex.product.code.rule"
    _description = "Product Code Rule (Category -> Prefix -> Sequence)"
    _order = "categ_id"

    active = fields.Boolean(default=True)
    categ_id = fields.Many2one(
        "product.category",
        string="Product Category",
        required=True,
        ondelete="cascade",
    )
    prefix = fields.Char(string="Prefix", required=True)
    sequence_id = fields.Many2one(
        "ir.sequence",
        string="Sequence",
        help="Sequence used to generate default_code for products in this category.",
    )
    padding = fields.Integer(string="Padding", default=6)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        help="If you use multi-company, keep rules per company. Otherwise leave as default.",
    )

    _sql_constraints = [
        ("uniq_categ_company", "unique(categ_id, company_id)", "A rule already exists for this category (in this company)."),
    ]

    @api.constrains("prefix")
    def _check_prefix(self):
        for rec in self:
            if not rec.prefix or rec.prefix.strip() != rec.prefix:
                raise ValidationError(_("Prefix cannot be empty or have leading/trailing spaces."))
            if "-" in rec.prefix:
                # Permitido, pero evitamos dobles guiones al construir PREFIJO-000001
                if rec.prefix.endswith("-"):
                    raise ValidationError(_("Prefix must not end with '-'."))

    def _sequence_code(self):
        # Código técnico único por regla (no por categoría) para evitar colisiones
        # Odoo requiere que ir.sequence.code no sea único, pero es buena práctica.
        self.ensure_one()
        return f"wex.product.code.rule.{self.id}"

    def action_create_sequence(self):
        """Create a dedicated ir.sequence if missing."""
        for rec in self:
            if rec.sequence_id:
                continue
            seq = self.env["ir.sequence"].sudo().create({
                "name": f"Wex {rec.prefix} ({rec.categ_id.complete_name})",
                "code": f"wex.product.code.{rec.company_id.id}.{rec.categ_id.id}",
                "implementation": "standard",
                "prefix": "",  # prefix lo construimos nosotros
                "padding": rec.padding or 6,
                "company_id": rec.company_id.id,
            })
            rec.sequence_id = seq.id

    def next_code(self):
        """Return next code like PREFIX-000001."""
        self.ensure_one()
        if not self.sequence_id:
            self.action_create_sequence()
        if not self.sequence_id:
            raise ValidationError(_("No sequence configured for this rule."))

        # next_by_id ya devuelve string con padding; como dejamos prefix vacío en la secuencia,
        # nos devuelve solo el número (ej '000001')
        number = self.sequence_id.sudo().next_by_id()
        prefix = self.prefix.strip()
        return f"{prefix}-{number}"

    @api.model
    def find_rule_for_category(self, categ_id, company_id=None):
        """Exact match only (no fallback)."""
        if not categ_id:
            return False
        company_id = company_id or self.env.company.id
        return self.search([
            ("active", "=", True),
            ("categ_id", "=", categ_id),
            ("company_id", "=", company_id),
        ], limit=1)

    def action_generate_missing_codes(self):
        """Batch: generate codes for products without default_code in mapped categories."""
        ProductT = self.env["product.template"].sudo()
        for rec in self:
            if not rec.active:
                continue
            if not rec.categ_id:
                continue

            # Productos de esta categoría sin default_code
            products = ProductT.search([
                ("categ_id", "=", rec.categ_id.id),
                ("default_code", "=", False),
            ])
            for p in products:
                # Respeta inmutabilidad: solo si sigue vacío
                p._wex_assign_default_code_if_needed()
