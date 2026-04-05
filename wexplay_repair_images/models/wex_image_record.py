# -*- coding: utf-8 -*-

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WexImageRecord(models.Model):
    _inherit = "wex.image.record"

    repair_order_id = fields.Many2one(
        comodel_name="repair.order",
        string="Repair Order",
        ondelete="cascade",
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            repair_order_id = vals.get("repair_order_id")
            if repair_order_id:
                vals.setdefault("res_model", "repair.order")
                vals.setdefault("res_id", repair_order_id)
                if "company_id" not in vals:
                    repair = self.env["repair.order"].browse(repair_order_id)
                    vals["company_id"] = repair.company_id.id
        records = super().create(vals_list)
        if not self.env.context.get("skip_repair_image_chatter"):
            records._post_image_added_to_repair_chatter()
        return records

    def write(self, vals):
        repair_order_id = vals.get("repair_order_id")
        if repair_order_id:
            vals.setdefault("res_model", "repair.order")
            vals.setdefault("res_id", repair_order_id)
            if "company_id" not in vals:
                repair = self.env["repair.order"].browse(repair_order_id)
                vals["company_id"] = repair.company_id.id
        return super().write(vals)

    @api.constrains("repair_order_id", "res_model", "res_id")
    def _check_repair_order_link_consistency(self):
        for rec in self:
            if rec.repair_order_id and (
                rec.res_model != "repair.order" or rec.res_id != rec.repair_order_id.id
            ):
                raise ValidationError(
                    "The repair image link is inconsistent with the generic owner fields."
                )

    def _get_repair_image_tag_names(self):
        self.ensure_one()
        return [tag.name for tag in self.tag_ids.sorted(lambda tag: (tag.sequence, tag.name))]

    def _build_repair_image_chatter_body(self):
        self.ensure_one()
        thumbnail_html = ""
        if self.thumbnail_url:
            thumbnail_html = Markup(
                '<div class="wex_repair_image_chatter__thumb_wrap">'
                '<img class="wex_repair_image_chatter__thumb" src="%s" alt="%s"/>'
                "</div>"
            ) % (
                escape(self.thumbnail_url),
                escape(self.name or _("Imagen SAT")),
            )

        description_html = ""
        if self.description:
            description_html = Markup(
                '<div class="wex_repair_image_chatter__description"><strong>%s</strong> %s</div>'
            ) % (
                escape(_("Descripción:")),
                escape(self.description),
            )

        tags = self._get_repair_image_tag_names()
        tags_html = ""
        if tags:
            badges = Markup("").join(
                Markup(
                    '<span class="wex_repair_image_chatter__tag">%s</span>'
                ) % escape(tag_name)
                for tag_name in tags[:4]
            )
            tags_html = Markup(
                '<div class="wex_repair_image_chatter__tags"><strong>%s</strong><div class="wex_repair_image_chatter__tag_list">%s</div></div>'
            ) % (
                escape(_("Etiquetas:")),
                badges,
            )

        body = Markup(
            '<div class="wex_repair_image_chatter">'
            '<div class="wex_repair_image_chatter__title">%s</div>'
            '<div class="wex_repair_image_chatter__body">'
            '%s'
            '<div class="wex_repair_image_chatter__content">'
            '<div class="wex_repair_image_chatter__meta">'
            '<span class="wex_repair_image_chatter__label">%s</span><span>%s</span>'
            '<span class="wex_repair_image_chatter__label">%s</span><span>%s</span>'
            '<span class="wex_repair_image_chatter__label">%s</span><span>%s</span>'
            '<span class="wex_repair_image_chatter__label">%s</span><span>%s</span>'
            "</div>"
            "%s"
            "%s"
            "</div>"
            "</div>"
            "</div>"
        ) % (
            escape(_("Nueva imagen añadida al expediente SAT")),
            thumbnail_html,
            escape(_("Nombre:")),
            escape(self.name or "-"),
            escape(_("Archivo DMS:")),
            escape(self.dms_file_name or self.dms_file_id.name or "-"),
            escape(_("Orden:")),
            escape(str(self.sequence)),
            escape(_("Subida por:")),
            escape(self.uploaded_by_id.display_name or self.env.user.display_name),
            description_html,
            tags_html,
        )
        return body

    def _post_image_added_to_repair_chatter(self):
        for rec in self.filtered("repair_order_id"):
            rec.repair_order_id.message_post(
                body=rec._build_repair_image_chatter_body(),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
