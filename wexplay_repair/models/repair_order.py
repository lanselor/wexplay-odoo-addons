from odoo import models, fields


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_device_type = fields.Selection(
        [
            ("mobile", "Móvil"),
            ("tablet", "Tablet"),
            ("laptop", "Portátil"),
            ("desktop", "Sobremesa"),
            ("all_in_one", "Todo en Uno"),
            ("mini_pc", "Mini PC"),
            ("imac", "iMac"),
            ("monitor", "Monitor"),
            ("gpu", "Gráfica"),
            ("motherboard", "Placa base"),
            ("smartwatch", "Smartwatch"),
            ("console", "Consola"),
            ("pos", "TPV"),
            ("other", "Otros"),
        ],
        string="Tipo de dispositivo",
    )
    x_partner_mobile = fields.Char(
        string="Móvil",
        related="partner_id.mobile",
        readonly=True,
        store=False,
    )

    x_brand = fields.Char(string="Marca")
    x_model = fields.Char(string="Modelo")
    x_imei = fields.Char(string="IMEI / Nº de serie")

    x_accessories = fields.Text(string="Accesorios entregados")
    x_reported_issue = fields.Text(string="Avería descrita por el cliente")
    x_internal_notes = fields.Text(string="Observaciones internas (técnico)")
