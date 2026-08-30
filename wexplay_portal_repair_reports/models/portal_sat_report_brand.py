# -*- coding: utf-8 -*-

import base64
import io
import re
import warnings

from PIL import Image, UnidentifiedImageError

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
ALLOWED_LOGO_FORMATS = {"PNG", "JPEG", "WEBP"}
MAX_LOGO_UPLOAD_SIZE = 6 * 1024 * 1024
MAX_LOGO_SOURCE_PIXELS = 16_777_216
MAX_LOGO_SIZE = (1024, 768)


class PortalSatReportBrand(models.Model):
    _name = "wex.portal.sat.report.brand"
    _description = "Portal SAT Report Brand"
    _rec_name = "commercial_partner_id"
    _check_company_auto = True

    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        readonly=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    manager_user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        readonly=True,
        ondelete="restrict",
    )
    identity_source = fields.Selection(
        selection=[("billing", "Datos de facturación"), ("custom", "Datos personalizados")],
        required=True,
        default="billing",
    )
    logo = fields.Image(string="Logotipo", max_width=1024, max_height=768)
    name = fields.Char(string="Nombre comercial")
    vat = fields.Char(string="NIF / CIF")
    street = fields.Char(string="Dirección")
    street2 = fields.Char(string="Dirección 2")
    zip = fields.Char(string="Código postal")
    city = fields.Char(string="Ciudad")
    state_id = fields.Many2one(comodel_name="res.country.state", string="Provincia")
    country_id = fields.Many2one(comodel_name="res.country", string="País")
    phone = fields.Char(string="Teléfono")
    email = fields.Char(string="Correo electrónico")
    website = fields.Char(string="Sitio web")
    primary_color = fields.Char(string="Color corporativo", default="#7b68b5")

    _sql_constraints = [
        (
            "wex_portal_sat_report_brand_partner_unique",
            "unique(commercial_partner_id)",
            "Solo puede existir una identidad de informe por empresa comercial.",
        ),
    ]

    @api.constrains("primary_color")
    def _check_primary_color(self):
        for record in self:
            if record.primary_color and not HEX_COLOR_RE.match(record.primary_color):
                raise ValidationError(_("El color corporativo debe tener formato hexadecimal, por ejemplo #1A5E8A."))

    @api.model
    def _get_portal_brand_for_user(self, user=None):
        user = user or self.env.user
        partner = user.partner_id.commercial_partner_id
        return self.sudo().search([("commercial_partner_id", "=", partner.id)], limit=1)

    @api.model
    def _get_or_create_portal_brand_for_user(self, user=None):
        user = user or self.env.user
        brand = self._get_portal_brand_for_user(user)
        if brand:
            return brand
        return self.sudo().create({
            "commercial_partner_id": user.partner_id.commercial_partner_id.id,
            "manager_user_id": user.id,
            "company_id": self.env.company.id,
        })

    def _check_portal_manager(self, user=None):
        self.ensure_one()
        user = user or self.env.user
        if user._is_internal():
            return True
        if not user.has_group("base.group_portal"):
            raise AccessError(_("Solo los usuarios del portal pueden gestionar esta identidad."))
        if self.commercial_partner_id != user.partner_id.commercial_partner_id:
            raise AccessError(_("No puedes gestionar la identidad de otra empresa."))
        if self.manager_user_id != user:
            raise AccessError(_("Solo el gestor de identidad de tu empresa puede modificarla."))
        return True

    @api.model
    def _prepare_portal_logo_upload(self, uploaded_file):
        """Validate the real image content and store a bounded static logo."""
        image_bytes = uploaded_file.read(MAX_LOGO_UPLOAD_SIZE + 1)
        if len(image_bytes) > MAX_LOGO_UPLOAD_SIZE:
            raise ValidationError(_("El logotipo no puede superar 6 MB."))

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(image_bytes)) as source:
                    image_format = source.format
                    if image_format not in ALLOWED_LOGO_FORMATS:
                        raise ValidationError(_("El logotipo debe ser PNG, JPEG o WebP."))
                    if source.width * source.height > MAX_LOGO_SOURCE_PIXELS:
                        raise ValidationError(_("Las dimensiones originales del logotipo son demasiado grandes."))
                    source.verify()

                with Image.open(io.BytesIO(image_bytes)) as source:
                    source.load()
                    normalized = source.convert("RGBA")
                    normalized.thumbnail(MAX_LOGO_SIZE, Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    normalized.save(output, format="PNG", optimize=True)
        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            UnidentifiedImageError,
            OSError,
            ValueError,
        ):
            raise ValidationError(_("El archivo seleccionado no es una imagen válida.")) from None

        return base64.b64encode(output.getvalue())

    def _prepare_report_identity(self):
        self.ensure_one()
        source = self.commercial_partner_id if self.identity_source == "billing" else self
        logo = self.logo or (source.image_1920 if self.identity_source == "billing" else False)
        return self._prepare_identity_values(source, logo, self.primary_color)

    def _get_logo_preview_data_uri(self):
        """Return the stored custom logo for the authorized portal form."""
        self.ensure_one()
        logo_data = self.logo.decode("utf-8") if isinstance(self.logo, bytes) else self.logo
        return "data:image/png;base64,%s" % logo_data if logo_data else False

    @api.model
    def _prepare_billing_report_identity(self, partner):
        return self._prepare_identity_values(partner, partner.image_1920, "#7b68b5")

    @api.model
    def _prepare_identity_values(self, source, logo, primary_color):
        logo_data = logo.decode("utf-8") if isinstance(logo, bytes) else logo
        return {
            "issuer_name": source.name or "",
            "issuer_logo": "data:image/png;base64,%s" % logo_data if logo_data else False,
            "issuer_primary_color": primary_color or "#7b68b5",
            "issuer_vat": source.vat or "",
            "issuer_phone": source.phone or getattr(source, "mobile", False) or "",
            "issuer_email": source.email or "",
            "issuer_website": source.website or "",
            "issuer_address": ", ".join(filter(None, [
                source.street,
                source.street2,
                " ".join(filter(None, [source.zip, source.city])),
                source.state_id.name,
                source.country_id.name,
            ])),
        }
