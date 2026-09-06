from odoo import _, models
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_sat_customer_reference(self):
        self.ensure_one()
        self.order_id.check_access("read")
        # Acceso acotado al pedido autorizado; no exige permisos SAT al vendedor.
        repairs = self.env["repair.order"].sudo().search([
            ("sale_order_id", "=", self.order_id.id),
            ("company_id", "=", self.company_id.id),
        ])
        if len(repairs) > 1:
            line_repairs = self.move_ids.repair_id & repairs
            if len(line_repairs) == 1:
                repairs = line_repairs
            elif any(repairs.mapped("x_customer_reference")):
                raise UserError(_("El pedido %s está vinculado a varios SAT. Revisa la relación de sus líneas antes de facturar para no mezclar referencias de cliente.") % self.order_id.display_name)
        return repairs[:1].x_customer_reference.strip() if repairs[:1].x_customer_reference else ""

    def _prepare_invoice_line(self, **optional_values):
        values = super()._prepare_invoice_line(**optional_values)
        if self.display_type or self.is_downpayment or values.get("display_type") != "product":
            return values
        reference = self._get_sat_customer_reference()
        if reference:
            note = _("Referencia del cliente: %s") % reference
            description = values.get("name") or ""
            if note not in description.splitlines():
                values["name"] = description + "\n" + note
        return values
