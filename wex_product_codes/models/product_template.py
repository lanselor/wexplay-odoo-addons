from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"  # Hereda del modelo product.template
    def _wex_assign_default_code_if_needed(self):
        """Assign default_code if empty and category has a rule."""
        # Asigna default_code si está vacío y la categoría tiene una regla
        for rec in self:
            if rec.default_code:
                continue
            if not rec.categ_id:
                continue

            # Company resolution: product company if set, else env company
            company = rec.company_id or rec.env.company
            rule = self.env["wex.product.code.rule"].find_rule_for_category(rec.categ_id.id, company_id=company.id)
            if not rule:
                continue

            rec.default_code = rule.next_code()

    @api.model_create_multi
    def create(self, vals_list):
        # Sobreescribe el método create para asignar el código después de crear el producto
        records = super().create(vals_list)
        # Asignar tras crear: ya existe ID, no interfiere con el create original
        records._wex_assign_default_code_if_needed()
        return records

    def write(self, vals):
        # Sobreescribe el método write para reasignar el código si se cambia la categoría o si el código está vacío
        res = super().write(vals)
        # Solo intentamos asignar si sigue vacío (inmutable si ya lo tenía)
        # y si se ha tocado categ_id o si default_code sigue vacío
        if "categ_id" in vals or "default_code" in vals:
            self._wex_assign_default_code_if_needed()
        else:
            # Caso típico: se crea producto sin categ_id, luego se completa:
            # si categ_id NO está en vals, no hacemos nada.
            # Si queréis forzar también en cualquier write, quitad este else.
            pass
        return res

    def copy(self, default=None):
        """When duplicating, force a new code by clearing default_code."""
        # Al duplicar, fuerza un nuevo código borrando el default_code
        default = dict(default or {})
        default.setdefault("default_code", False)
        return super().copy(default=default)

