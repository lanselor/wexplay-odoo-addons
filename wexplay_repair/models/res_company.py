# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    x_repair_budget_location_estimating_id = fields.Many2one(
        "stock.location",
        string="Ubicación SAT para Revisión",
        domain="[('usage', '=', 'internal')]",
        help="Ubicación SAT a usar cuando el presupuesto está en estado 'Revisión'.",
    )

    x_repair_budget_location_waiting_customer_id = fields.Many2one(
        "stock.location",
        string="Ubicación SAT para Esperando cliente",
        domain="[('usage', '=', 'internal')]",
        help="Ubicación SAT a usar cuando el presupuesto está en estado 'Esperando cliente'.",
    )

    x_repair_budget_location_accepted_id = fields.Many2one(
        "stock.location",
        string="Ubicación SAT para Aceptado",
        domain="[('usage', '=', 'internal')]",
        help="Ubicación SAT a usar cuando el presupuesto está en estado 'Aceptado'.",
    )

    x_repair_budget_location_rejected_id = fields.Many2one(
        "stock.location",
        string="Ubicación SAT para Rechazado",
        domain="[('usage', '=', 'internal')]",
        help="Ubicación SAT a usar cuando el presupuesto está en estado 'Rechazado'.",
    )

    x_repair_state_location_under_repair_id = fields.Many2one(
        "stock.location",
        string="Ubicación SAT para En reparación",
        domain="[('usage', '=', 'internal')]",
        help="Ubicación SAT a usar cuando la reparación entra en estado 'En reparación'.",
    )

    x_repair_state_location_done_id = fields.Many2one(
        "stock.location",
        string="Ubicación SAT para Finalizada",
        domain="[('usage', '=', 'internal')]",
        help="Ubicación SAT a usar cuando la reparación queda finalizada y pendiente de recogida.",
    )

    x_repair_state_location_glue_desk_id = fields.Many2one(
        "stock.location",
        string="Ubicación SAT para Mesa Pegado",
        domain="[('usage', '=', 'internal')]",
        help="Ubicación SAT a usar al finalizar reparaciones de móvil/tablet que deban quedar en mesa de pegado.",
    )

    x_repair_state_location_waiting_spare_id = fields.Many2one(
        "stock.location",
        string="Ubicación SAT para Pendiente de repuesto",
        domain="[('usage', '=', 'internal')]",
        help="Ubicación SAT a usar cuando una reparación queda pendiente de la llegada de un repuesto.",
    )