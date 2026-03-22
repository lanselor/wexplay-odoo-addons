# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .device_constants import DEVICE_TYPE_SELECTION


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_device_type = fields.Selection(
        DEVICE_TYPE_SELECTION,
        string="Tipo de dispositivo",
    )

    x_sat_priority = fields.Selection(
        [
            ("normal", "Normal"),
            ("urgent", "Urgente"),
            ("company", "Empresa"),
            ("warranty", "GarantÃ­a"),
        ],
        string="Prioridad SAT",
        default="normal",
        tracking=True,
        index=True,
    )

    # NUEVO: empleado que recepciona el equipo
    x_reception_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Recepciona",
        help="Empleado que recepciona el equipo en mostrador.",
    )

    # Re-declaramos el campo original para hacerlo obligatorio
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
    )

    # Campo de Referencia del cliente para empresas.
    x_customer_reference = fields.Char(
        string="Referencia del cliente",
        help="Referencia de la orden de reparaciÃ³n del cliente empresa para vincularla con nuestra orden SAT.",
    )

    # Datos del cliente (related)
    x_partner_mobile = fields.Char(
        string="MÃ³vil",
        related="partner_id.mobile",
        readonly=True,
        store=False,
    )

    x_partner_phone = fields.Char(
        string="TelÃ©fono",
        related="partner_id.phone",
        readonly=True,
        store=False,
    )

    # Marca/Modelo normalizados (catÃ¡logo)
    x_brand_id = fields.Many2one(
        "wex.repair.brand",
        string="Marca",
        related="x_model_id.brand_id",
        store=True,
        readonly=True,
    )

    x_model_id = fields.Many2one(
        "wex.repair.device_model",
        string="Modelo",
        ondelete="restrict",
        domain="[('device_type', '=', x_device_type)]",
    )

    # Desbloqueo
    x_unlock_type = fields.Selection(
        [
            ("pin", "PIN"),
            ("pattern", "Patrón"),
            ("password", "Contraseña"),
            ("none", "Sin bloqueo"),
            ("unknown", "No indicado"),
        ],
        string="Tipo de desbloqueo",
    )

    x_unlock_code = fields.Char(string="Código / Contraseña")
    x_unlock_pattern = fields.Char(string="Patrón (descripción)")
    x_unlock_notes = fields.Text(string="Notas de desbloqueo")

    # Campos legacy / compatibilidad
    x_brand = fields.Char(string="Marca (texto)")
    x_model = fields.Char(string="Modelo (texto)")
    x_imei = fields.Char(string="IMEI / Nº de serie")
    x_accessories = fields.Text(string="Accesorios entregados")
    x_reported_issue = fields.Text(string="Averí­a descrita por el cliente")
    x_internal_notes = fields.Text(string="Observaciones internas (técnico)")

    # ---------------------------------------------------------
    # TOTAL SAT (informativo, SIN tocar BD)
    # Fuente: sale_order_id.amount_total
    # ---------------------------------------------------------
    x_sat_total_amount = fields.Monetary(
        string="Total SAT",
        currency_field="x_sat_currency_id",
        compute="_compute_x_sat_total_amount",
        store=False,
        readonly=True,
    )

    x_sat_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_x_sat_currency_id",
        store=False,
        readonly=True,
    )

    @api.depends("company_id")
    def _compute_x_sat_currency_id(self):
        for rec in self:
            rec.x_sat_currency_id = rec.company_id.currency_id

    @api.depends("sale_order_id", "sale_order_id.amount_total", "sale_order_id.currency_id", "company_id")
    def _compute_x_sat_total_amount(self):
        for rec in self:
            if rec.sale_order_id:
                rec.x_sat_total_amount = rec.sale_order_id.amount_total or 0.0
                rec.x_sat_currency_id = rec.sale_order_id.currency_id or rec.company_id.currency_id
            else:
                rec.x_sat_total_amount = 0.0
                rec.x_sat_currency_id = rec.company_id.currency_id

    # ---------------------------------------------------------
    # Onchange
    # ---------------------------------------------------------
    @api.onchange("x_device_type")
    def _onchange_x_device_type_reset_model_brand(self):
        """Si cambia el tipo, limpiamos modelo/marca para evitar inconsistencias."""
        for rec in self:
            rec.x_model_id = False

    # ---------------------------------------------------------
    # Historial por IMEI / NÂº de serie
    # ---------------------------------------------------------
    def action_view_device_history(self):
        self.ensure_one()

        serial = (self.x_imei or "").strip()
        if not serial:
            raise UserError(_("No hay IMEI / NÂº de serie informado en esta orden."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Historial del dispositivo"),
            "res_model": "repair.order",
            "view_mode": "list,form",
            "domain": [("x_imei", "=", serial)],
            "context": {
                "search_default_group_by_partner_id": 0,
                "default_x_imei": serial,
            },
        }
