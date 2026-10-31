from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WexReturnDispatch(models.TransientModel):
    _name = "wex.return.dispatch"
    _description = "Prepare Supplier Return Shipment"

    return_ids = fields.Many2many("wex.purchase.return", required=True, readonly=True)
    picking_ids = fields.Many2many("stock.picking", readonly=True)
    operation_count = fields.Integer(compute="_compute_summary", string="Devoluciones a preparar")
    supplier_count = fields.Integer(compute="_compute_summary", string="Proveedores")

    @api.depends("return_ids")
    def _compute_summary(self):
        for wizard in self:
            wizard.operation_count = len({(record.receipt_picking_id.id, record.staging_location_id.id) for record in wizard.return_ids})
            wizard.supplier_count = len(wizard.return_ids.vendor_id.commercial_partner_id)

    def action_create_returns(self):
        self.ensure_one()
        self.check_access("write")
        self.return_ids._check_dispatch_access()
        self.env.flush_all()
        self.env.cr.execute("SELECT id FROM wex_return_dispatch WHERE id = %s FOR UPDATE", [self.id])
        self.invalidate_recordset()
        if not self.picking_ids:
            self.picking_ids = self.return_ids._create_native_dispatch()
        return self.return_ids._open_return_pickings(self.picking_ids)


class WexReturnRma(models.TransientModel):
    _name = "wex.return.rma"
    _description = "Assign Common RMA Reference"

    return_ids = fields.Many2many("wex.purchase.return", required=True, readonly=True)
    rma_reference = fields.Char(string="Referencia RMA")

    def action_assign(self):
        self.ensure_one()
        self.check_access("write")
        records = self.return_ids
        records._check_dispatch_access()
        if len(records.company_id) != 1 or len(records.vendor_id.commercial_partner_id) != 1:
            raise UserError(_("Selecciona piezas de una misma compañía y proveedor."))
        records.write({"rma_reference": (self.rma_reference or "").strip() or False})
        return {"type": "ir.actions.act_window_close"}
