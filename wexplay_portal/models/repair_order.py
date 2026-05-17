# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_portal_state_label = fields.Char(
        string="Portal status label",
        compute="_compute_x_portal_state_label",
        store=False,
    )

    @api.depends("state")
    def _compute_x_portal_state_label(self):
        for repair in self:
            repair.x_portal_state_label = repair._get_portal_status_label()

    @api.model
    def _get_portal_done_states(self):
        return ("done", "cancel", "delivered")

    @api.model
    def _get_portal_visible_domain(self, user=None):
        user = user or self.env.user
        commercial_partner = user.partner_id.commercial_partner_id
        return [("partner_id", "child_of", commercial_partner.ids)]

    def _can_portal_user_access(self, user=None):
        self.ensure_one()
        domain = self._get_portal_visible_domain(user=user)
        return bool(self.search_count(domain + [("id", "=", self.id)]))

    def _is_portal_repair_active(self):
        self.ensure_one()
        return self.state not in self._get_portal_done_states()

    def _get_portal_status_label(self):
        self.ensure_one()
        return dict(self._fields["state"].selection).get(self.state, self.state or "")

    def _get_portal_device_type_label(self):
        self.ensure_one()
        if "x_device_type" not in self._fields:
            return ""
        return dict(self._fields["x_device_type"].selection).get(
            self.x_device_type, self.x_device_type or ""
        )

    def _get_portal_brand_label(self):
        self.ensure_one()
        self._check_portal_related_read_access()
        repair = self.sudo()
        if getattr(repair, "x_brand_id", False):
            return repair.x_brand_id.display_name
        return getattr(self, "x_brand", False) or ""

    def _get_portal_model_label(self):
        self.ensure_one()
        self._check_portal_related_read_access()
        repair = self.sudo()
        if getattr(repair, "x_model_id", False):
            return repair.x_model_id.display_name
        return getattr(self, "x_model", False) or ""

    def _get_portal_product_label(self):
        self.ensure_one()
        self._check_portal_related_read_access()
        repair = self.sudo()
        return repair.product_id.display_name if repair.product_id else ""

    def _get_portal_unlock_type_label(self):
        self.ensure_one()
        if "x_unlock_type" not in self._fields:
            return ""
        return dict(self._fields["x_unlock_type"].selection).get(
            self.x_unlock_type, self.x_unlock_type or ""
        )

    def _get_portal_unlock_description(self):
        self.ensure_one()
        values = []
        unlock_type = self._get_portal_unlock_type_label()
        if unlock_type:
            values.append(unlock_type)

        if getattr(self, "x_unlock_code", False):
            values.append(self.x_unlock_code)
        elif getattr(self, "x_unlock_pattern", False):
            values.append(self.x_unlock_pattern)

        return " - ".join(values)

    def _get_portal_status_steps(self):
        self.ensure_one()
        state_labels = dict(self._fields["state"].selection)
        steps = [
            ("draft", state_labels.get("draft", "New")),
            ("confirmed", state_labels.get("confirmed", "Confirmed")),
            ("under_repair", state_labels.get("under_repair", "Under Repair")),
            ("done", state_labels.get("done", "Repaired")),
        ]
        if any(key == "delivered" for key, _label in self._fields["state"].selection):
            steps.append(("delivered", state_labels.get("delivered", "Delivered")))
        steps.append(("cancel", state_labels.get("cancel", "Cancelled")))
        return self._prepare_portal_steps("state", steps)

    def _get_portal_budget_steps(self):
        self.ensure_one()
        if "x_budget_stage" not in self._fields:
            return []

        budget_labels = dict(self._fields["x_budget_stage"].selection)
        steps = [
            ("none", budget_labels.get("none", "No budget")),
            ("estimating", budget_labels.get("estimating", "Revision")),
            ("waiting_customer", budget_labels.get("waiting_customer", "Waiting customer")),
            ("accepted", budget_labels.get("accepted", "Accepted")),
            ("rejected", budget_labels.get("rejected", "Rejected")),
            ("not_repairable", budget_labels.get("not_repairable", "Not repairable")),
        ]
        return self._prepare_portal_steps("x_budget_stage", steps)

    def _prepare_portal_steps(self, field_name, ordered_steps):
        self.ensure_one()
        current_value = self[field_name]
        ordered_keys = [key for key, _label in ordered_steps]
        current_index = ordered_keys.index(current_value) if current_value in ordered_keys else -1
        is_cancel_flow = field_name == "state" and current_value == "cancel"
        is_rejected_flow = field_name == "x_budget_stage" and current_value == "rejected"
        is_not_repairable_flow = (
            field_name == "x_budget_stage" and current_value == "not_repairable"
        )

        steps = []
        for index, (key, label) in enumerate(ordered_steps):
            is_current = key == current_value
            is_completed = current_index > index and not (
                (is_cancel_flow and key == "delivered")
                or (is_rejected_flow and key == "accepted")
                or (
                    is_not_repairable_flow
                    and key in ("waiting_customer", "accepted", "rejected")
                )
            )
            is_visible = not (
                (is_cancel_flow and key == "delivered")
                or (is_rejected_flow and key == "accepted")
                or (
                    is_not_repairable_flow
                    and key in ("waiting_customer", "accepted", "rejected")
                )
            )
            steps.append(
                {
                    "key": key,
                    "label": label,
                    "is_current": is_current,
                    "is_completed": is_completed,
                    "is_visible": is_visible,
                }
            )
        return [step for step in steps if step["is_visible"]]

    def _get_portal_part_lines(self):
        self.ensure_one()
        return self.move_ids.filtered(lambda move: move.repair_line_type == "add")

    def _get_portal_service_lines(self):
        self.ensure_one()
        repair = self.sudo()
        if not repair.sale_order_id:
            return self.env["sale.order.line"]

        part_sale_lines = repair._get_portal_part_lines().mapped("sale_line_id").sudo()
        return repair.sale_order_id.order_line.sudo().filtered(
            lambda line: not line.display_type
            and line.product_id
            and line.product_id.type == "service"
            and line != repair.sale_order_line_id
            and line not in part_sale_lines
        )

    def _get_portal_part_line_status(self, move):
        move.ensure_one()
        if self.state in ("done", "delivered"):
            return _("Used")
        if self.state == "cancel":
            return _("Cancelled")
        if not move.product_id or move.repair_line_type != "add":
            return ""
        if move.forecast_availability >= move.product_uom_qty:
            return _("Available")
        return _("Not available")

    def _get_portal_part_line_values(self):
        self.ensure_one()
        self._check_portal_related_read_access()
        values = []
        for move in self.sudo()._get_portal_part_lines():
            values.append(
                {
                    "name": move.product_id.display_name or move.name,
                    "description": move.description_picking or "",
                    "quantity": move.product_uom_qty,
                    "uom": move.product_uom.display_name if move.product_uom else "",
                    "status": self._get_portal_part_line_status(move),
                }
            )
        return values

    def _get_portal_service_line_values(self):
        self.ensure_one()
        self._check_portal_related_read_access()
        values = []
        for line in self.sudo()._get_portal_service_lines().sudo():
            line = line.sudo()
            values.append(
                {
                    "name": line.product_id.display_name or line.name,
                    "description": line.name or "",
                    "quantity": line.product_uom_qty,
                    "subtotal": line.price_subtotal,
                    "currency": line.currency_id,
                }
            )
        return values

    def _get_portal_related_invoices(self):
        self.ensure_one()
        self._check_portal_related_read_access()
        repair = self.sudo()
        if not repair.sale_order_id:
            return self.env["account.move"]

        return self.env["account.move"].search(
            [
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("state", "=", "posted"),
                ("invoice_line_ids.sale_line_ids.order_id", "=", repair.sale_order_id.id),
            ],
            order="invoice_date desc, id desc",
        )

    def _get_portal_invoice_values(self):
        self.ensure_one()
        values = []
        for invoice in self._get_portal_related_invoices():
            values.append(
                {
                    "id": invoice.id,
                    "name": invoice.name or invoice.ref or _("Invoice"),
                    "date": invoice.invoice_date,
                    "amount_total": invoice.amount_total,
                    "currency": invoice.currency_id,
                    "state": invoice.state,
                    "payment_state": invoice.payment_state,
                    "move_type_label": dict(invoice._fields["move_type"].selection).get(
                        invoice.move_type, invoice.move_type or ""
                    ),
                    "payment_state_label": dict(
                        invoice._fields["payment_state"].selection
                    ).get(invoice.payment_state, invoice.payment_state or ""),
                    "portal_url": invoice.get_portal_url(),
                }
            )
        return values

    def _get_portal_repair_context_bar_values(self):
        self.ensure_one()
        return {
            "repair_name": self.name or "-",
            "customer_reference": self.x_customer_reference or "",
            "device_label": (
                " / ".join(
                    value
                    for value in (
                        self._get_portal_brand_label(),
                        self._get_portal_model_label(),
                    )
                    if value
                )
                or self._get_portal_product_label()
                or self._get_portal_device_type_label()
                or "-"
            ),
            "status": {
                "key": "service",
                "label": self._get_portal_status_label(),
                "message": "",
            },
            "action_url": "",
            "action_label": "",
        }

    def _get_portal_warranty_values(self):
        self.ensure_one()
        if "x_show_warranty_status" not in self._fields or not self.x_show_warranty_status:
            return {}

        self._check_portal_related_read_access()
        repair = self.sudo()
        warranty_status = ""
        if "x_warranty_status" in repair._fields:
            warranty_status = dict(repair._fields["x_warranty_status"].selection).get(
                repair.x_warranty_status, repair.x_warranty_status or ""
            )

        warranty_budget_status = ""
        if "x_warranty_budget_stage" in repair._fields:
            warranty_budget_status = dict(
                repair._fields["x_warranty_budget_stage"].selection
            ).get(repair.x_warranty_budget_stage, repair.x_warranty_budget_stage or "")

        return {
            "show": True,
            "status": warranty_status,
            "is_valid": warranty_status == dict(repair._fields["x_warranty_status"].selection).get("valid", "En garantía")
            if "x_warranty_status" in repair._fields
            else False,
            "is_case": bool(getattr(repair, "x_is_warranty_case", False)),
            "origin_name": getattr(repair, "x_warranty_origin_repair_name", False) or "",
            "source_invoice": (
                repair.x_warranty_source_invoice_id.name
                if getattr(repair, "x_warranty_source_invoice_id", False)
                else ""
            ),
            "source_invoice_date": getattr(repair, "x_warranty_source_invoice_date", False),
            "parts_months": getattr(repair, "x_warranty_parts_months", 0),
            "labor_months": getattr(repair, "x_warranty_labor_months", 0),
            "parts_deadline": getattr(repair, "x_warranty_parts_deadline", False),
            "labor_deadline": getattr(repair, "x_warranty_labor_deadline", False),
            "parts_valid": bool(getattr(repair, "x_is_parts_under_warranty", False)),
            "labor_valid": bool(getattr(repair, "x_is_labor_under_warranty", False)),
            "budget_status": warranty_budget_status,
        }

    def _check_portal_related_read_access(self):
        self.ensure_one()
        user = self.env.user
        if user.has_group("base.group_portal") and not self._can_portal_user_access(user):
            raise AccessError(_("You cannot access this repair from the portal."))
        return True

    def _get_portal_image_records(self, tag_code=None):
        self.ensure_one()
        self._check_portal_related_read_access()
        if "x_image_ids" not in self._fields:
            return self.env["wex.image.record"]
        images = self.sudo().x_image_ids.sorted(lambda image: (image.sequence, image.id))
        if tag_code:
            images = images.filtered(lambda image: tag_code in image.tag_ids.mapped("code"))
        return images

    def _get_portal_image_filter_values(self, selected_tag_code=None):
        self.ensure_one()
        images = self._get_portal_image_records()
        tags = images.mapped("tag_ids").sorted(lambda tag: (tag.sequence, tag.name, tag.id))
        values = [
            {
                "code": "",
                "name": _("All"),
                "count": len(images),
                "is_selected": not selected_tag_code,
            }
        ]
        for tag in tags:
            values.append(
                {
                    "code": tag.code,
                    "name": tag.name,
                    "count": len(images.filtered(lambda image: tag in image.tag_ids)),
                    "is_selected": selected_tag_code == tag.code,
                }
            )
        return values

    def _get_portal_image_values(self, tag_code=None):
        self.ensure_one()
        values = []
        for image in self._get_portal_image_records(tag_code=tag_code):
            sorted_tags = image.tag_ids.sorted(lambda tag: (tag.sequence, tag.name, tag.id))
            values.append(
                {
                    "id": image.id,
                    "name": image.name or _("SAT image"),
                    "description": image.description or "",
                    "tags": sorted_tags.mapped("name"),
                    "tag_codes": sorted_tags.mapped("code"),
                    "has_binary": bool(image.dms_file_id and image.dms_file_id.content),
                    "image_url": f"/my/repairs/{self.id}/images/{image.id}?variant=preview",
                    "thumbnail_url": f"/my/repairs/{self.id}/images/{image.id}?variant=thumb",
                    "preview_url": f"/my/repairs/{self.id}/images/{image.id}?variant=preview",
                    "download_url": f"/my/repairs/{self.id}/images/{image.id}?download=1",
                    "modal_id": f"wexRepairImageModal{self.id}_{image.id}",
                    "modal_label_id": f"wexRepairImageModalLabel{self.id}_{image.id}",
                    "filename": image.dms_file_name or image.name or _("SAT image"),
                    "uploaded_at": image.uploaded_at,
                }
            )
        return values
