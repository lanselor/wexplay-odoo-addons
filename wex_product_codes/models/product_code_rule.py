from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WexProductCodeRule(models.Model):
    _name = "wex.product.code.rule"  # Nombre del modelo
    _description = "Product Code Rule (Category -> Prefix -> Sequence)"  # Descripción del modelo
    _order = "categ_id"  # Orden por defecto al listar las reglas

    active = fields.Boolean(default=True)  # Indica si la regla está activa
    categ_id = fields.Many2one(
        "product.category",  # Relación con el modelo product.category
        string="Product Category",  # Nombre del campo
        required=True,  # Obligatorio
        ondelete="cascade",  # Si se borra la categoría, se borra la regla
    )
    prefix = fields.Char(string="Prefix", required=True)  # Prefijo del código (obligatorio)
    sequence_id = fields.Many2one(
        "ir.sequence",  # Relación con el modelo ir.sequence
        string="Sequence",  # Nombre del campo
        help="Sequence used to generate default_code for products in this category.",  # Ayuda
    )
    padding = fields.Integer(string="Padding", default=6)  # Relleno de la secuencia (por defecto 6)
    company_id = fields.Many2one(
        "res.company",  # Relación con el modelo res.company
        string="Company",  # Nombre del campo
        default=lambda self: self.env.company,  # Por defecto, la compañía del entorno
        help="If you use multi-company, keep rules per company. Otherwise leave as default.",  # Ayuda
    )

    _sql_constraints = [
        ("uniq_categ_company", "unique(categ_id, company_id)", "A rule already exists for this category (in this company)."),  # Restricción SQL: debe haber una única regla por categoría y compañía
    ]

    @api.constrains("prefix")
    def _check_prefix(self):
        # Valida el prefijo para que no esté vacío ni tenga espacios al principio o al final
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
        # Crea una secuencia dedicada si no existe
        for rec in self:
            if rec.sequence_id:
                continue
            seq = self.env["ir.sequence"].sudo().create({
                "name": f"Wex {rec.prefix} ({rec.categ_id.complete_name})",
                "code": f"wex.product.code.{rec.company_id.id}.{rec.categ_id.id}",  # Código de la secuencia
                "implementation": "standard",
                "prefix": "",  # prefix lo construimos nosotros
                "padding": rec.padding or 6,
                "company_id": rec.company_id.id,
            })
            rec.sequence_id = seq.id

    def next_code(self):
        """Return next code like PREFIX-000001."""
        # Devuelve el siguiente código, como PREFIJO-000001
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
        # Busca la regla que corresponde a una categoría (sin fallback)
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
        # Genera códigos para los productos sin default_code en las categorías mapeadas
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

