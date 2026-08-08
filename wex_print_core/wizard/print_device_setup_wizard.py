# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WexPrintDeviceSetupWizard(models.TransientModel):
    _name = "wex.print.device.setup.wizard"
    _description = "Wex Print Device Setup Wizard"

    snapshot_id = fields.Many2one(
        "wex.print.device.snapshot",
        string="Impresora detectada",
        readonly=True,
    )
    existing_device_id = fields.Many2one(
        "wex.print.device",
        string="Dispositivo existente",
        readonly=True,
    )
    name = fields.Char(string="Nombre del dispositivo", required=True)
    qz_printer_name = fields.Char(string="Nombre en QZ", required=True, readonly=True)
    model_hint = fields.Char(string="Modelo de impresora")
    backend = fields.Selection(
        [("qz", "QZ Tray")],
        string="Backend",
        default="qz",
        readonly=True,
        required=True,
    )
    device_kind = fields.Selection(
        [
            ("label", "Etiqueta"),
            ("thermal", "Térmica"),
            ("a4", "A4"),
        ],
        string="Tipo de impresora",
        required=True,
    )
    company_id = fields.Many2one("res.company", string="Empresa")
    document_line_ids = fields.One2many(
        "wex.print.device.setup.document.line",
        "wizard_id",
        string="Documentos configurados",
    )
    user_id = fields.Many2one("res.users", string="Usuario")
    priority = fields.Integer(string="Prioridad", default=90)
    pilot_use_new_resolution = fields.Boolean(
        string="Activar resolución nueva ahora",
        default=False,
        help="Déjalo desactivado para conservar el comportamiento legacy hasta validar esta impresora.",
    )
    allow_fallback = fields.Boolean(string="Permitir fallback", default=True)
    duplex_mode = fields.Selection(
        [
            ("default", "Por defecto"),
            ("long-edge", "Doble cara (borde largo)"),
            ("short-edge", "Doble cara (borde corto)"),
            ("one-sided", "Una cara"),
        ],
        string="Modo dúplex",
        default="default",
        required=True,
    )
    notes = fields.Text(string="Notas")

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        device_id = values.get("existing_device_id") or self.env.context.get("default_existing_device_id")
        device = self.env["wex.print.device"].browse(device_id).exists()
        if device:
            values.update({
                "existing_device_id": device.id,
                "name": device.name,
                "qz_printer_name": device.qz_printer_name,
                "model_hint": device.model_hint or "",
                "backend": device.backend,
                "company_id": device.company_id.id,
                "device_kind": device.device_kind,
                "user_id": self.env.user.id,
            })
            return values

        snapshot_id = values.get("snapshot_id") or self.env.context.get("default_snapshot_id")
        snapshot = self.env["wex.print.device.snapshot"].browse(snapshot_id).exists()
        if snapshot:
            values.update({
                "snapshot_id": snapshot.id,
                "name": snapshot.printer_name,
                "qz_printer_name": snapshot.printer_name,
                "model_hint": snapshot.driver or "",
                "company_id": snapshot.company_id.id,
                "user_id": snapshot.user_id.id,
                "device_kind": self._get_suggested_device_kind(snapshot),
            })
        return values

    @api.model
    def _get_suggested_device_kind(self, snapshot):
        details = " ".join(filter(None, [snapshot.printer_type, snapshot.driver, snapshot.printer_name])).lower()
        if any(token in details for token in ("thermal", "receipt", "pos", "prp-", "80mm")):
            return "thermal"
        if any(token in details for token in ("laser", "inkjet", "mfc", "a4")):
            return "a4"
        if any(token in details for token in ("label", "ql-", "zebra")):
            return "label"
        return False

    @api.onchange("device_kind")
    def _onchange_device_kind(self):
        for wizard in self:
            wizard.document_line_ids = wizard.document_line_ids.filtered(
                lambda line: line.document_type_id.legacy_kind == wizard.device_kind
            )
            if wizard.device_kind != "a4":
                wizard.duplex_mode = "default"

    def _get_document_types(self):
        self.ensure_one()
        document_types = self.document_line_ids.mapped("document_type_id")
        if not document_types:
            raise ValidationError(_("Selecciona al menos un tipo de documento para esta impresora."))
        if len(document_types) != len(set(document_types.ids)):
            raise ValidationError(_("No puedes añadir el mismo tipo de documento más de una vez."))
        if any(document.legacy_kind != self.device_kind for document in document_types):
            raise ValidationError(_("Todos los documentos deben ser compatibles con el tipo de impresora seleccionado."))
        return document_types

    def _prepare_device_values(self):
        return {
            "name": self.name,
            "backend": self.backend,
            "qz_printer_name": self.qz_printer_name,
            "device_kind": self.device_kind,
            "model_hint": self.model_hint,
            "company_id": self.company_id.id,
            "notes": self.notes,
        }

    def _get_or_create_profile(self, device):
        self.ensure_one()
        domain = [
            ("device_id", "=", device.id),
            ("legacy_kind", "=", self.device_kind),
            ("company_id", "=", self.company_id.id or False),
            ("allow_fallback", "=", self.allow_fallback),
            ("duplex_mode", "=", self.duplex_mode),
        ]
        profile = self.env["wex.print.profile"].search(domain, limit=1)
        if profile:
            return profile

        profile_code = "device_%s_%s_%s" % (device.id, self.device_kind, self.duplex_mode)
        return self.env["wex.print.profile"].create({
            "name": "%s - Estándar" % device.name,
            "code": profile_code,
            "legacy_kind": self.device_kind,
            "device_id": device.id,
            "allow_fallback": self.allow_fallback,
            "duplex_mode": self.duplex_mode,
            "company_id": self.company_id.id,
            "notes": _("Perfil creado desde el asistente de impresoras detectadas."),
        })

    def _prepare_assignment_values(self, document_type, profile):
        return {
            "name": "%s - %s" % (document_type.name, profile.name),
            "priority": self.priority,
            "pilot_use_new_resolution": self.pilot_use_new_resolution,
            "document_type_id": document_type.id,
            "profile_id": profile.id,
            "user_id": self.user_id.id,
            "company_id": self.company_id.id,
            "notes": _("Asignación creada desde el asistente de impresoras detectadas."),
        }

    def _create_missing_assignments(self, document_types, profile):
        assignment_model = self.env["wex.print.assignment"]
        for document_type in document_types:
            domain = [
                ("document_type_id", "=", document_type.id),
                ("profile_id", "=", profile.id),
                ("user_id", "=", self.user_id.id or False),
                ("company_id", "=", self.company_id.id or False),
            ]
            if not assignment_model.search(domain, limit=1):
                assignment_model.create(self._prepare_assignment_values(document_type, profile))

    def action_apply(self):
        self.ensure_one()
        document_types = self._get_document_types()
        device = self.existing_device_id
        if not device:
            device_model = self.env["wex.print.device"]
            device = device_model.search([("qz_printer_name", "=", self.qz_printer_name)], limit=1)
            if device:
                raise ValidationError(_("Ya existe un dispositivo configurado con este nombre de QZ."))
            device = device_model.create(self._prepare_device_values())

        profile = self._get_or_create_profile(device)
        self._create_missing_assignments(document_types, profile)

        return {
            "type": "ir.actions.act_window",
            "name": _("Dispositivo de impresión"),
            "res_model": "wex.print.device",
            "res_id": device.id,
            "view_mode": "form",
            "target": "current",
        }


class WexPrintDeviceSetupDocumentLine(models.TransientModel):
    _name = "wex.print.device.setup.document.line"
    _description = "Wex Print Device Setup Document Line"

    wizard_id = fields.Many2one(
        "wex.print.device.setup.wizard",
        string="Asistente",
        required=True,
        ondelete="cascade",
    )
    wizard_device_kind = fields.Selection(related="wizard_id.device_kind")
    document_type_id = fields.Many2one(
        "wex.print.document.type",
        string="Tipo de documento",
        required=True,
        domain="[('active', '=', True), ('legacy_kind', '=', wizard_device_kind)]",
    )
    report_action_id = fields.Many2one(related="document_type_id.report_action_id", string="Reporte", readonly=True)
    paperformat_id = fields.Many2one(related="document_type_id.paperformat_id", string="Formato", readonly=True)
