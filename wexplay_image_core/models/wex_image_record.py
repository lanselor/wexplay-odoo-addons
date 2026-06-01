# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class WexImageRecord(models.Model):
    _name = "wex.image.record"
    _description = "Imagen Wex"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence asc, id asc"

    name = fields.Char(string="Nombre", required=True, tracking=True)
    description = fields.Text(string="Descripción")
    sequence = fields.Integer(string="Orden", default=10)
    active = fields.Boolean(string="Activo", default=True)

    tag_ids = fields.Many2many(
        comodel_name="wex.image.tag",
        relation="wex_image_record_tag_rel",
        column1="image_id",
        column2="tag_id",
        string="Etiquetas",
    )
    dms_file_name = fields.Char(string="Nombre de archivo DMS", readonly=True)

    res_model = fields.Char(string="Modelo", required=True, index=True)
    res_id = fields.Integer(string="Registro", required=True, index=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    uploaded_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Subida por",
        default=lambda self: self.env.user,
        readonly=True,
    )
    uploaded_at = fields.Datetime(string="Subida el", default=fields.Datetime.now, readonly=True)

    dms_file_id = fields.Many2one(
        comodel_name="dms.file",
        string="Archivo DMS",
        required=True,
        ondelete="restrict",
        index=True,
    )
    dms_directory_id = fields.Many2one(
        related="dms_file_id.directory_id",
        comodel_name="dms.directory",
        string="Carpeta DMS",
        store=False,
        readonly=True,
    )
    mimetype = fields.Char(string="Tipo", related="dms_file_id.mimetype", store=False, readonly=True)
    file_size = fields.Float(string="Tamaño", related="dms_file_id.size", store=False, readonly=True)
    checksum = fields.Char(string="Checksum/SHA1", related="dms_file_id.checksum", store=False, readonly=True)
    preview_image = fields.Image(string="Imagen", related="dms_file_id.image_1920", readonly=True)
    thumbnail_url = fields.Char(compute="_compute_preview_urls")
    preview_url = fields.Char(compute="_compute_preview_urls")

    _sql_constraints = [
        (
            "wex_image_record_sequence_positive",
            "CHECK(sequence >= 0)",
            "El orden debe ser positivo.",
        ),
    ]

    @api.depends("dms_file_id")
    def _compute_preview_urls(self):
        for rec in self:
            if not rec.dms_file_id:
                rec.thumbnail_url = False
                rec.preview_url = False
                continue
            rec.thumbnail_url = (
                "/web/image/dms.file/%s/image_128/128x128?crop=1" % rec.dms_file_id.id
            )
            rec.preview_url = "/web/image/dms.file/%s/image_1920" % rec.dms_file_id.id

    @api.constrains("res_model", "res_id")
    def _check_link_target(self):
        for rec in self:
            if not rec.res_model or not rec.res_id:
                raise ValidationError(_("El registro vinculado es obligatorio."))

    @api.model
    def _find_existing_dms_file(self, directory, filename):
        return self.env["dms.file"].search(
            [
                ("directory_id", "=", directory.id),
                ("name", "=", filename),
            ],
            limit=1,
        )

    @api.model
    def create_image_from_binary(
        self,
        *,
        name,
        binary_content,
        directory,
        res_model,
        res_id,
        description=False,
        tag_ids=None,
        sequence=10,
        company_id=False,
        mimetype=False,
        replace_existing=False,
        extra_vals=None,
    ):
        if not binary_content:
            raise UserError(_("La imagen está vacía."))
        if not directory:
            raise UserError(_("Se necesita una carpeta DMS para guardar la imagen."))

        dms_file_name = (extra_vals or {}).get("dms_file_name") or name

        existing_dms_file = self._find_existing_dms_file(directory, dms_file_name)
        if existing_dms_file and not replace_existing:
            raise UserError(
                _("Ya existe un archivo DMS con el mismo nombre en la carpeta de destino.")
            )

        if existing_dms_file:
            existing_dms_file.write({"content": binary_content})
            dms_file = existing_dms_file
        else:
            dms_file = self.env["dms.file"].create(
                {
                    "directory_id": directory.id,
                    "name": dms_file_name,
                    "content": binary_content,
                }
            )

        values = {
            "name": name,
            "description": description,
            "sequence": sequence,
            "tag_ids": [(6, 0, tag_ids or [])],
            "res_model": res_model,
            "res_id": res_id,
            "company_id": company_id or self.env.company.id,
            "uploaded_by_id": self.env.user.id,
            "uploaded_at": fields.Datetime.now(),
            "dms_file_id": dms_file.id,
            "dms_file_name": dms_file_name,
        }
        if extra_vals:
            values.update(extra_vals)
        return self.create(values)

    def get_preview_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "preview_url": self.preview_url,
            "dms_file_id": self.dms_file_id.id,
            "tag_ids": self.tag_ids.ids,
        }

    def action_open_preview(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vista previa"),
            "res_model": self._name,
            "res_id": self.id,
            "views": [(self.env.ref("wexplay_image_core.view_wex_image_record_form").id, "form")],
            "view_mode": "form",
            "target": "new",
        }

    def action_open_dms_file(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Archivo DMS"),
            "res_model": "dms.file",
            "res_id": self.dms_file_id.id,
            "views": [(False, "form")],
            "view_mode": "form",
            "target": "current",
        }
