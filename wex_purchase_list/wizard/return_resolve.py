from odoo import _, fields, models
from odoo.exceptions import UserError


class WexReturnResolve(models.TransientModel):
    _name = "wex.return.resolve"
    _description = "Resolve Vendor Return Without Shipment"
    _check_company_auto = True

    return_id = fields.Many2one("wex.purchase.return", required=True, readonly=True, check_company=True)
    company_id = fields.Many2one(related="return_id.company_id")
    product_id = fields.Many2one(related="return_id.product_id")
    quantity = fields.Float(string="Cantidad", digits="Product Unit of Measure", required=True)
    disposition = fields.Selection(
        selection=lambda self: self.env["wex.return.resolution"]._fields["disposition"]._description_selection(self.env), string="Decisión",
    )
    destination_location_id = fields.Many2one("stock.location", string="Ubicación disponible de destino", check_company=True)
    package_id = fields.Many2one("stock.quant.package", string="Paquete de origen", check_company=True)
    explanation = fields.Text(string="Explicación")
    resolution_id = fields.Many2one("wex.return.resolution", readonly=True, copy=False, check_company=True)

    def action_resolve(self):
        self.ensure_one()
        self.check_access("write")
        trace = self.return_id
        trace._check_dispatch_access()
        with self.env.cr.savepoint():
            self.env.flush_all()
            self.env.cr.execute("SELECT id FROM wex_return_resolve WHERE id = %s FOR UPDATE", [self.id])
            self.invalidate_recordset()
            if self.resolution_id:
                if self.resolution_id.return_id != self.return_id:
                    raise UserError(_("La resolución registrada no corresponde a esta devolución."))
                return self.resolution_id._open_document()
            trace._lock_dispatch_records()
            if not self.disposition:
                raise UserError(_("Selecciona qué hacer con la pieza."))
            trace._check_resolution_quantity(self.quantity, include_prepared=self.disposition != "hold")
            if not (self.explanation or "").strip():
                raise UserError(_("Explica por qué la pieza no se enviará."))
            resolution = self.env["wex.return.resolution"].create({
                "return_id": trace.id, "quantity": self.quantity, "disposition": self.disposition,
                "explanation": self.explanation, "destination_location_id": self.destination_location_id.id,
                "package_id": self.package_id.id,
            })
            if self.disposition == "recover":
                resolution._create_recovery_transfer()
            elif self.disposition == "scrap":
                resolution._create_scrap_document()
            self.resolution_id = resolution
            trace.resolution_revision += 1
            return resolution._open_document()
