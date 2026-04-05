# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    x_repair_budget_location_estimating_id = fields.Many2one(
        related="company_id.x_repair_budget_location_estimating_id",
        comodel_name="stock.location",
        string="Ubicación SAT para Revisión",
        readonly=False,
    )

    x_repair_budget_location_waiting_customer_id = fields.Many2one(
        related="company_id.x_repair_budget_location_waiting_customer_id",
        comodel_name="stock.location",
        string="Ubicación SAT para Esperando cliente",
        readonly=False,
    )

    x_repair_budget_location_accepted_id = fields.Many2one(
        related="company_id.x_repair_budget_location_accepted_id",
        comodel_name="stock.location",
        string="Ubicación SAT para Aceptado",
        readonly=False,
    )

    x_repair_budget_location_rejected_id = fields.Many2one(
        related="company_id.x_repair_budget_location_rejected_id",
        comodel_name="stock.location",
        string="Ubicación SAT para Rechazado",
        readonly=False,
    )

    x_repair_state_location_under_repair_id = fields.Many2one(
        related="company_id.x_repair_state_location_under_repair_id",
        comodel_name="stock.location",
        string="Ubicación SAT para En reparación",
        readonly=False,
    )

    x_repair_state_location_done_id = fields.Many2one(
        related="company_id.x_repair_state_location_done_id",
        comodel_name="stock.location",
        string="Ubicación SAT para Finalizada",
        readonly=False,
    )

    x_repair_state_location_delivered_id = fields.Many2one(
        related="company_id.x_repair_state_location_delivered_id",
        comodel_name="stock.location",
        string="Ubicación SAT para Entregada",
        readonly=False,
    )

    x_repair_state_location_glue_desk_id = fields.Many2one(
        related="company_id.x_repair_state_location_glue_desk_id",
        comodel_name="stock.location",
        string="Ubicación SAT para Mesa Pegado",
        readonly=False,
    )

    x_repair_state_location_waiting_spare_id = fields.Many2one(
        related="company_id.x_repair_state_location_waiting_spare_id",
        comodel_name="stock.location",
        string="Ubicación SAT para Pendiente de repuesto",
        readonly=False,
    )