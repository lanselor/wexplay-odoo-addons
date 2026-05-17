# -*- coding: utf-8 -*-
from odoo import fields, models


class WexPrintDeviceSnapshot(models.Model):
    _name = "wex.print.device.snapshot"
    _description = "Wex Print Device Snapshot"
    _order = "snapshot_at desc, id desc"

    name = fields.Char(string="Nombre", required=True)
    snapshot_at = fields.Datetime(string="Capturado el", required=True, default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", string="Usuario", default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one("res.company", string="Empresa", default=lambda self: self.env.company, readonly=True)

    printer_name = fields.Char(string="Nombre de impresora", required=True, readonly=True)
    driver = fields.Char(string="Driver", readonly=True)
    density = fields.Char(string="Densidad", readonly=True)
    trays_text = fields.Text(string="Bandejas", readonly=True)
    is_default = fields.Boolean(string="Por defecto", readonly=True)
    is_physical = fields.Boolean(string="Es física", readonly=True)
    printer_type = fields.Char(string="Tipo", readonly=True)
    raw_details_json = fields.Text(string="Detalles raw (JSON)", readonly=True)

    existing_device_id = fields.Many2one(
        "wex.print.device",
        string="Saved device",
        compute="_compute_existing_device_id",
    )

    def _compute_existing_device_id(self):
        for rec in self:
            rec.existing_device_id = self.env["wex.print.device"].search(
                [("qz_printer_name", "=", rec.printer_name)], limit=1
            )

    def action_save_as_device(self):
        self.ensure_one()
        existing = self.env["wex.print.device"].search(
            [("qz_printer_name", "=", self.printer_name)], limit=1
        )
        if existing:
            # Abre el dispositivo existente en lugar de crear un duplicado
            return {
                "type": "ir.actions.act_window",
                "res_model": "wex.print.device",
                "res_id": existing.id,
                "view_mode": "form",
                "target": "current",
            }

        device = self.env["wex.print.device"].create({
            "name": self.printer_name,
            "qz_printer_name": self.printer_name,
            "model_hint": self.driver or "",
            "backend": "qz",
            "device_kind": "label",
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "wex.print.device",
            "res_id": device.id,
            "view_mode": "form",
            "target": "current",
        }
