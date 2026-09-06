from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    wex_auto_portal_billing = fields.Boolean(
        string="Añadir automáticamente los SAT finalizados a facturación pendiente",
        help="Se aplica a reparaciones normales con presupuesto aceptado de empresas "
             "SAT profesionales con portal activo. No crea facturas.",
        tracking=True,
        groups="base.group_user",
    )
