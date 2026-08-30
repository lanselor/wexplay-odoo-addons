# -*- coding: utf-8 -*-

from markupsafe import Markup, escape

from odoo import _, fields, models
from odoo.exceptions import AccessError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    def _collect_portal_sat_report_images(self):
        """Collect every image already authorized for the portal company."""
        self.ensure_one()
        image_records = self.x_image_ids.filtered(
            lambda record: record.media_kind == "image"
        ).sorted(lambda record: (record.sequence, record.id))
        image_records.mapped("dms_file_id").read(["mimetype", "image_1920"])
        image_records.mapped("tag_ids")

        images = []
        for record in image_records:
            image_data = record.dms_file_id.image_1920
            if not image_data:
                continue
            data_b64 = image_data.decode("utf-8") if isinstance(image_data, bytes) else image_data
            images.append({
                "name": record.name or "",
                "src": "data:%s;base64,%s" % (record.dms_file_id.mimetype or "image/jpeg", data_b64),
                "description": record.description or "",
                "tags": ", ".join(record._get_repair_image_tag_names()),
            })
        return images

    def _prepare_portal_wexplay_sat_report_context(self):
        self.ensure_one()
        repair = self.sudo()
        context = repair._prepare_sat_report_context()
        images = repair._collect_portal_sat_report_images()
        context["image_pages"] = list(images)
        context.update({
            "issuer_name": repair.company_id.name,
            "issuer_logo": False,
            "issuer_primary_color": "#7b68b5",
            "show_issuer_logo": False,
        })
        return context

    def _get_portal_sat_report_user(self):
        self.ensure_one()
        user_id = self.env.context.get("portal_sat_report_user_id")
        return self.env["res.users"].sudo().browse(user_id).exists() or self.env.user

    def _prepare_portal_custom_sat_report_context(self):
        """Prepare only the data that belongs in a client-branded report."""
        self.ensure_one()
        repair = self.sudo()
        portal_user = self._get_portal_sat_report_user()
        brand_model = self.env["wex.portal.sat.report.brand"].sudo()
        brand = brand_model._get_portal_brand_for_user(portal_user)
        identity = (
            brand._prepare_report_identity()
            if brand
            else brand_model._prepare_billing_report_identity(
                portal_user.partner_id.commercial_partner_id
            )
        )
        images = repair._collect_portal_sat_report_images()

        return {
            "issuer": identity,
            "generated_at": fields.Datetime.now(),
            "customer": repair.partner_id,
            "customer_reference": repair.x_customer_reference or "",
            "device_type_label": repair._get_sat_report_selection_label(
                "x_device_type", repair.x_device_type
            ),
            "brand": repair.x_brand_id.name if repair.x_brand_id else (repair.x_brand or ""),
            "model": repair.x_model_id.name if repair.x_model_id else (repair.x_model or ""),
            "imei": repair.x_imei or "",
            "accessories": repair.x_accessories or "",
            "reported_issue": repair.x_reported_issue or "",
            "diagnosis": repair.internal_notes or "",
            "report_notes": repair.x_sat_report_notes or "",
            "parts": repair._get_sat_report_parts(),
            "services": repair._get_sat_report_services(),
            "image_pages": list(images),
        }

    def _render_portal_sat_report_pdf(self, identity_mode):
        self.ensure_one()
        if identity_mode not in ("wexplay", "custom"):
            raise AccessError(_("Formato de informe no válido."))
        if not self._can_portal_user_access(self.env.user):
            raise AccessError(_("No tienes acceso a este informe."))

        report_xmlid = (
            "wexplay_portal_repair_reports.action_report_portal_custom_sat_service"
            if identity_mode == "custom"
            else "wexplay_portal_repair_reports.action_report_portal_sat_service"
        )
        report = self.env.ref(report_xmlid).sudo()
        return self.sudo().with_context(
            portal_sat_report_user_id=self.env.user.id,
        ).env["ir.actions.report"]._render_qweb_pdf(report.report_name, res_ids=self.ids)[0]

    def _log_portal_sat_report_download(self, identity_mode, user=None):
        """Record a rendered portal report without exposing internal report data."""
        self.ensure_one()
        if identity_mode not in ("wexplay", "custom"):
            raise AccessError(_("Formato de informe no válido."))
        user = user or self.env.user
        if not self._can_portal_user_access(user):
            raise AccessError(_("No tienes acceso a este informe."))

        variant_label = dict(
            self.env["wex.portal.repair.event"]._fields["report_variant"].selection
        )[identity_mode]
        self.sudo()._create_portal_repair_event(
            "report_downloaded",
            user=user,
            extra_values={"report_variant": identity_mode},
        )
        user_name = escape(user.display_name or user.partner_id.display_name or "Usuario portal")
        message = Markup(
            "<p><strong>Informe descargado desde el portal</strong></p>"
            "<p>%s ha descargado: %s.</p>"
        ) % (user_name, escape(variant_label))
        self.sudo().message_post(
            body=message,
            message_type="comment",
            subtype_xmlid="wexplay_portal_repair_reports.mt_repair_portal_report_downloaded",
            author_id=user.partner_id.id,
        )
        return True
