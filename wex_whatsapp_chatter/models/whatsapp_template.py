# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


TEMPLATE_CONTEXT_GROUP_SELECTION = [
    ("general", "General"),
    ("repair_budget", "SAT: Presupuesto"),
    ("repair_ready", "SAT: Listo / Entrega"),
    ("repair_pending", "SAT: Pendiente cliente"),
    ("repair_non_repairable", "SAT: No reparable"),
    ("repair_b2b", "SAT: Empresa / B2B"),
    ("repair_other", "SAT: Otros"),
    ("sale_quote", "Ventas: Presupuesto / Pedido"),
    ("sale_followup", "Ventas: Seguimiento"),
    ("sale_other", "Ventas: Otros"),
    ("account_invoice", "Facturacion: Factura / Abono"),
    ("account_payment", "Facturacion: Cobro / Pago"),
    ("account_other", "Facturacion: Otros"),
    ("partner_general", "Contactos: General"),
    ("partner_followup", "Contactos: Seguimiento"),
]


class WhatsappTemplate(models.Model):
    _name = "whatsapp.template"
    _description = "WhatsApp Template"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        index=True,
    )

    # Explicit model selection (keeps system robust and simple)
    res_model = fields.Selection(
        selection=[
            ("sale.order", "Sales: Quotation / Order"),
            ("account.move", "Accounting: Invoice"),
            ("repair.order", "Repairs: Repair Order"),
            ("res.partner", "Contacts: Contact"),
        ],
        string="Applies to",
        required=True,
        index=True,
        help="Used to filter templates by document type.",
    )

    context_group = fields.Selection(
        selection=TEMPLATE_CONTEXT_GROUP_SELECTION,
        string="Template Group",
        required=True,
        default="general",
        index=True,
        help="Functional group used by the WhatsApp template filters.",
    )

    body = fields.Text(
        string="Message Body",
        required=True,
        help="Supports dynamic variables like ${object.name}, ${object.partner_id.name}, etc.",
    )

    @api.model
    def _get_default_context_group(self, res_model):
        defaults = {
            "sale.order": "sale_quote",
            "account.move": "account_invoice",
            "repair.order": "repair_budget",
            "res.partner": "partner_general",
        }
        return defaults.get(res_model, "general")

    @api.model
    def _get_allowed_context_groups_by_model(self):
        return {
            "sale.order": {"general", "sale_quote", "sale_followup", "sale_other"},
            "account.move": {"general", "account_invoice", "account_payment", "account_other"},
            "repair.order": {
                "general",
                "repair_budget",
                "repair_ready",
                "repair_pending",
                "repair_non_repairable",
                "repair_b2b",
                "repair_other",
            },
            "res.partner": {"general", "partner_general", "partner_followup"},
        }

    def _is_context_group_allowed_for_model(self, res_model, context_group):
        allowed_map = self._get_allowed_context_groups_by_model()
        return context_group in allowed_map.get(res_model, {"general"})

    @api.constrains("res_model", "context_group")
    def _check_context_group_matches_model(self):
        for template in self:
            if not template.res_model or not template.context_group:
                continue
            if not template._is_context_group_allowed_for_model(
                template.res_model, template.context_group
            ):
                raise ValidationError(
                    _(
                        "The template group '%(group)s' is not valid for model '%(model)s'."
                    )
                    % {
                        "group": template.context_group,
                        "model": template.res_model,
                    }
                )

    @api.onchange("res_model")
    def _onchange_res_model(self):
        for template in self:
            default_group = template._get_default_context_group(template.res_model)
            if not template.context_group or not template._is_context_group_allowed_for_model(
                template.res_model, template.context_group
            ):
                template.context_group = default_group

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            vals = dict(vals or {})
            res_model = vals.get("res_model")
            context_group = vals.get("context_group")
            if res_model and (
                not context_group
                or not self._is_context_group_allowed_for_model(res_model, context_group)
            ):
                vals["context_group"] = self._get_default_context_group(res_model)
            normalized_vals_list.append(vals)
        return super().create(normalized_vals_list)

    def render_body(self, res_model, res_id):
        """
        Secure dynamic rendering using Odoo's mail.template engine.

        Why:
        - Avoids unsafe eval.
        - Reuses official rendering logic.
        - Supports ${object.field} syntax.

        If no valid record is provided, falls back to raw body.
        """
        self.ensure_one()

        if not (res_model and res_id):
            return self.body or ""

        record = self.env[res_model].browse(res_id).exists()
        if not record:
            return self.body or ""

        rendered = self.env["mail.template"]._render_template(
            self.body or "",
            res_model,
            [record.id],
        )

        return rendered.get(record.id) or (self.body or "")
