from urllib.parse import quote

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import AccessError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_device_test_run_ids = fields.One2many(
        "wex.device.test.run",
        "repair_order_id",
        string="Device Test Runs",
        readonly=True,
    )
    x_device_test_active_run_id = fields.Many2one(
        "wex.device.test.run",
        compute="_compute_device_test_run_data",
        string="Active Device Test Run",
        readonly=True,
    )
    x_device_test_run_count = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Device Test Run Count",
        readonly=True,
    )
    x_device_test_download_url = fields.Char(
        compute="_compute_device_test_run_data",
        string="APK Download URL",
        readonly=True,
    )
    x_device_test_download_qr_html = fields.Html(
        compute="_compute_device_test_run_data",
        string="APK Download QR",
        sanitize=False,
        readonly=True,
    )
    x_device_test_pairing_code = fields.Char(
        compute="_compute_device_test_run_data",
        string="Pairing Code",
        readonly=True,
    )
    x_device_test_pairing_token = fields.Char(
        compute="_compute_device_test_run_data",
        string="Pairing Token",
        readonly=True,
    )
    x_device_test_session_id = fields.Many2one(
        "wex.device.test.session",
        compute="_compute_device_test_run_data",
        string="Current Device Session",
        readonly=True,
    )
    x_device_test_result_ids = fields.One2many(
        "wex.device.test.result",
        "run_id",
        compute="_compute_device_test_run_data",
        string="Device Test Results",
        readonly=True,
    )
    x_device_test_log_ids = fields.One2many(
        "wex.device.test.log",
        "run_id",
        compute="_compute_device_test_run_data",
        string="Device Test Logs",
        readonly=True,
    )
    x_device_test_result_count = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Device Test Result Count",
        readonly=True,
    )
    x_device_test_log_count = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Device Test Log Count",
        readonly=True,
    )
    x_device_test_device_uuid = fields.Char(
        compute="_compute_device_test_run_data",
        string="Device UUID",
        readonly=True,
    )
    x_device_test_device_manufacturer = fields.Char(
        compute="_compute_device_test_run_data",
        string="Device Manufacturer",
        readonly=True,
    )
    x_device_test_device_model = fields.Char(
        compute="_compute_device_test_run_data",
        string="Device Model",
        readonly=True,
    )
    x_device_test_android_version = fields.Char(
        compute="_compute_device_test_run_data",
        string="Android Version",
        readonly=True,
    )
    x_device_test_sdk_int = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Android SDK",
        readonly=True,
    )
    x_device_test_app_version = fields.Char(
        compute="_compute_device_test_run_data",
        string="App Version",
        readonly=True,
    )
    x_device_test_last_ping_at = fields.Datetime(
        compute="_compute_device_test_run_data",
        string="Last Ping At",
        readonly=True,
    )
    x_device_test_last_diagnostic_at = fields.Datetime(
        compute="_compute_device_test_run_data",
        string="Last Diagnostic At",
        readonly=True,
    )
    x_device_test_last_test_at = fields.Datetime(
        compute="_compute_device_test_run_data",
        string="Last Test At",
        readonly=True,
    )
    x_device_test_last_status = fields.Selection(
        selection=[
            ("ok", "OK"),
            ("error", "Error"),
        ],
        compute="_compute_device_test_run_data",
        string="Last Session Status",
        readonly=True,
    )
    x_device_test_last_message = fields.Text(
        compute="_compute_device_test_run_data",
        string="Last Session Message",
        readonly=True,
    )
    x_device_test_last_battery_level = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Last Battery Level",
        readonly=True,
    )
    x_device_test_last_network_type = fields.Char(
        compute="_compute_device_test_run_data",
        string="Last Network Type",
        readonly=True,
    )
    x_device_test_last_storage_free_mb = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Last Storage Free MB",
        readonly=True,
    )
    x_device_test_last_storage_total_mb = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Last Storage Total MB",
        readonly=True,
    )
    x_device_test_last_battery_temperature_c = fields.Float(
        compute="_compute_device_test_run_data",
        string="Last Battery Temperature C",
        readonly=True,
    )
    x_device_test_last_thermal_status = fields.Char(
        compute="_compute_device_test_run_data",
        string="Last Thermal Status",
        readonly=True,
    )
    x_device_test_show_pairing_token = fields.Boolean(
        compute="_compute_device_test_run_data",
        string="Show Pairing Token",
        readonly=True,
    )
    x_device_test_state = fields.Selection(
        selection=[
            ("pending_pairing", "Pending Pairing"),
            ("paired", "Paired"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        compute="_compute_device_test_run_data",
        string="Device Test State",
        readonly=True,
    )
    x_device_test_pairing_qr_html = fields.Html(
        compute="_compute_device_test_run_data",
        string="Pairing QR",
        sanitize=False,
        readonly=True,
    )
    x_device_test_pairing_payload = fields.Text(
        compute="_compute_device_test_run_data",
        string="Pairing Payload",
        readonly=True,
    )
    x_device_test_show_preparation_panel = fields.Boolean(
        compute="_compute_device_test_run_data",
        string="Show Preparation Panel",
        readonly=True,
    )
    x_device_test_show_operations_panel = fields.Boolean(
        compute="_compute_device_test_run_data",
        string="Show Operations Panel",
        readonly=True,
    )
    x_device_test_footer_allowed = fields.Boolean(
        compute="_compute_device_test_run_data",
        string="Device Test Footer Allowed",
        readonly=True,
    )
    x_device_test_results_ok_count = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Device Test OK Count",
        readonly=True,
    )
    x_device_test_results_fail_count = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Device Test Fail Count",
        readonly=True,
    )
    x_device_test_results_pending_count = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Device Test Pending Count",
        readonly=True,
    )
    x_device_test_results_unavailable_count = fields.Integer(
        compute="_compute_device_test_run_data",
        string="Device Test Unavailable Count",
        readonly=True,
    )
    x_device_test_latest_update_at = fields.Datetime(
        compute="_compute_device_test_run_data",
        string="Device Test Latest Update At",
        readonly=True,
    )
    x_device_test_audio_summary = fields.Char(
        compute="_compute_device_test_run_data",
        string="Device Test Audio Summary",
        readonly=True,
    )
    x_device_test_sensor_summary = fields.Char(
        compute="_compute_device_test_run_data",
        string="Device Test Sensor Summary",
        readonly=True,
    )
    x_device_test_thermal_summary = fields.Char(
        compute="_compute_device_test_run_data",
        string="Device Test Thermal Summary",
        readonly=True,
    )
    x_device_test_diagnostic_summary = fields.Char(
        compute="_compute_device_test_run_data",
        string="Device Test Diagnostic Summary",
        readonly=True,
    )
    x_device_test_overview_html = fields.Html(
        compute="_compute_device_test_run_data",
        string="Device Test Overview",
        sanitize=False,
        readonly=True,
    )
    x_device_test_results_summary_html = fields.Html(
        compute="_compute_device_test_run_data",
        string="Device Test Results Summary",
        sanitize=False,
        readonly=True,
    )
    x_device_test_categories_html = fields.Html(
        compute="_compute_device_test_run_data",
        string="Device Test Categories",
        sanitize=False,
        readonly=True,
    )
    x_device_test_environment_html = fields.Html(
        compute="_compute_device_test_run_data",
        string="Device Test Environment",
        sanitize=False,
        readonly=True,
    )

    def _get_device_test_download_url(self):
        self.ensure_one()
        return "https://www.wexplay.com/test"

    def _get_device_test_public_base_url(self):
        self.ensure_one()
        config = self.env["ir.config_parameter"].sudo()
        return (
            config.get_param("wex_device_test.public_base_url")
            or config.get_param("web.base.url")
            or ""
        ).strip()

    def _get_device_test_qr_url(self, value, width=280, height=280):
        self.ensure_one()
        if not value:
            return False
        return "/report/barcode/QR/%s?width=%s&height=%s" % (
            quote(value, safe=""),
            width,
            height,
        )

    def _build_device_test_qr_html(self, qr_url, alt_text):
        self.ensure_one()
        if not qr_url:
            return False
        return Markup(
            '<div class="text-center">'
            '<img src="%s" alt="%s" style="width:220px;height:220px;object-fit:contain;" class="img-fluid border rounded bg-white p-2"/>'
            "</div>"
        ) % (escape(qr_url), escape(alt_text))

    def _get_device_test_pairing_payload(self, active_run):
        self.ensure_one()
        if not active_run:
            return False
        base_url = self._get_device_test_public_base_url()
        if not base_url:
            return False
        return active_run._prepare_pairing_qr_payload(base_url)

    def _get_device_test_active_run(self):
        self.ensure_one()
        return self.env["wex.device.test.run"].search(
            [
                ("repair_order_id", "=", self.id),
                ("state", "in", self.env["wex.device.test.run"]._get_active_states()),
            ],
            order="started_at desc, id desc",
            limit=1,
        )

    def _has_device_test_access(self):
        self.ensure_one()
        return self.env.user.has_group("wex_device_test.group_wex_device_test_manager")

    def _ensure_device_test_access(self):
        self.ensure_one()
        if not self._has_device_test_access():
            raise AccessError("You do not have permission to use Device Test.")

    def _get_device_test_state_label(self, state):
        selection = dict(self._fields["x_device_test_state"].selection)
        return selection.get(state, "")

    def _get_device_test_footer_status_payload(self, active_run):
        self.ensure_one()
        if not active_run:
            return {"label": "Sin run", "tone": "neutral"}
        tone_map = {
            "pending_pairing": "warning",
            "paired": "success",
            "in_progress": "info",
            "completed": "success",
            "cancelled": "neutral",
        }
        return {
            "label": self._get_device_test_state_label(active_run.state) or "Sin estado",
            "tone": tone_map.get(active_run.state, "neutral"),
        }

    def _get_device_test_masked_pairing_token(self, active_run):
        self.ensure_one()
        if not active_run or not active_run.pairing_token:
            return ""
        return "*" * len(active_run.pairing_token)

    def _get_device_test_result_bucket(self, status):
        ok_statuses = {"confirmed_ok", "detected", "available"}
        fail_statuses = {"confirmed_fail", "not_detected", "error"}
        pending_statuses = {"pending", "played"}
        unavailable_statuses = {"not_available"}
        if status in ok_statuses:
            return "ok"
        if status in fail_statuses:
            return "fail"
        if status in pending_statuses:
            return "pending"
        if status in unavailable_statuses:
            return "unavailable"
        return "pending"

    def _format_device_test_category_summary(self, label, result_records):
        self.ensure_one()
        if not result_records:
            return "%s pendiente" % label
        ok_count = 0
        fail_count = 0
        pending_count = 0
        unavailable_count = 0
        for result in result_records:
            bucket = self._get_device_test_result_bucket(result.status)
            if bucket == "ok":
                ok_count += 1
            elif bucket == "fail":
                fail_count += 1
            elif bucket == "unavailable":
                unavailable_count += 1
            else:
                pending_count += 1
        parts = []
        if ok_count:
            parts.append("%s OK" % ok_count)
        if fail_count:
            parts.append("%s fallo" % fail_count)
        if pending_count:
            parts.append("%s pendiente" % pending_count)
        if unavailable_count:
            parts.append("%s no disponible" % unavailable_count)
        return "%s: %s" % (label, " · ".join(parts or ["sin datos"]))

    def _format_device_test_datetime(self, value):
        self.ensure_one()
        return fields.Datetime.to_string(value) if value else "Sin actualizar"

    def _build_device_test_dashboard_card(
        self,
        eyebrow,
        title,
        body,
        tone="neutral",
        icon_class=False,
        variant="default",
    ):
        self.ensure_one()
        tone_border = {
            "neutral": "#d7deea",
            "success": "#c7e6d0",
            "warning": "#ead8a4",
            "info": "#c9d9f5",
            "danger": "#ecc7c7",
        }
        tone_badge = {
            "neutral": "background:#f8fafc;color:#475467;border:1px solid #e2e8f0;",
            "success": "background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;",
            "warning": "background:#fffbeb;color:#92400e;border:1px solid #fde68a;",
            "info": "background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;",
            "danger": "background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;",
        }
        badge_label = {
            "neutral": "Info",
            "success": "OK",
            "warning": "Pendiente",
            "info": "Activo",
            "danger": "Atención",
        }
        layouts = {
            "default": {
                "wrapper": "border-radius:14px;padding:16px 18px;background:#ffffff;border:1px solid %s;border-top:3px solid %s;",
                "header_margin": "margin-bottom:8px;",
                "title": "font-size:16px;font-weight:800;line-height:1.25;margin-bottom:6px;color:#101828;",
                "body": "font-size:14px;line-height:1.45;color:#475467;",
                "icon_shell": "width:38px;height:38px;border-radius:12px;background:#f8fafc;color:#344054;font-size:16px;",
            },
            "header": {
                "wrapper": "border-radius:14px;padding:14px 16px;background:#ffffff;border:1px solid %s;border-left:4px solid %s;",
                "header_margin": "margin-bottom:6px;",
                "title": "font-size:15px;font-weight:800;line-height:1.2;margin-bottom:4px;color:#101828;",
                "body": "font-size:13px;line-height:1.35;color:#475467;",
                "icon_shell": "width:34px;height:34px;border-radius:10px;background:#f8fafc;color:#344054;font-size:15px;",
            },
            "compact": {
                "wrapper": "border-radius:12px;padding:12px 14px;background:#ffffff;border:1px solid %s;border-left:3px solid %s;",
                "header_margin": "margin-bottom:6px;",
                "title": "font-size:15px;font-weight:800;line-height:1.2;margin-bottom:4px;color:#101828;",
                "body": "font-size:13px;line-height:1.35;color:#475467;",
                "icon_shell": "width:34px;height:34px;border-radius:10px;background:#f8fafc;color:#344054;font-size:15px;",
            },
        }
        layout = layouts.get(variant, layouts["default"])
        icon_html = ""
        if icon_class:
            icon_html = Markup(
                '<span style="display:inline-flex;align-items:center;justify-content:center;%s">'
                '<i class="fa %s"></i>'
                "</span>"
            ) % (
                Markup(layout["icon_shell"]),
                escape(icon_class),
            )
        return Markup(
            '<div style="%s">'
            '<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;%s">'
            '<div style="display:flex;align-items:flex-start;gap:10px;min-width:0;">'
            "%s"
            '<div style="min-width:0;">'
            '<div style="font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#667085;">%s</div>'
            "</div>"
            "</div>"
            '<span style="display:inline-flex;align-items:center;padding:3px 8px;border-radius:999px;font-size:11px;font-weight:700;%s">%s</span>'
            "</div>"
            '<div style="%s">%s</div>'
            '<div style="%s">%s</div>'
            "</div>"
        ) % (
            Markup(layout["wrapper"]) % (
                escape(tone_border.get(tone, tone_border["neutral"])),
                escape(tone_border.get(tone, tone_border["neutral"])),
            ),
            Markup(layout["header_margin"]),
            icon_html,
            escape(eyebrow),
            Markup(tone_badge.get(tone, tone_badge["neutral"])),
            escape(badge_label.get(tone, badge_label["neutral"])),
            Markup(layout["title"]),
            escape(title),
            Markup(layout["body"]),
            escape(body),
        )

    def _build_device_test_overview_html(self, active_run, session, latest_update_at):
        self.ensure_one()
        state_payload = self._get_device_test_footer_status_payload(active_run)
        state_body = "Run activo: %s" % (active_run.display_name if active_run else "Sin run")
        device_title = session.display_name if session else "Sin dispositivo"
        device_body = "Modelo: %s" % (session.model or "Sin modelo") if session else "Todavía no hay sesión vinculada."
        update_title = self._format_device_test_datetime(latest_update_at)
        update_body = "Último mensaje: %s" % ((session.last_message or active_run.last_message) if (session or active_run) else "Sin actividad")
        return Markup(
            '<div class="row g-3">'
            '<div class="col-lg-4 col-md-6">%s</div>'
            '<div class="col-lg-4 col-md-6">%s</div>'
            '<div class="col-lg-4 col-md-12">%s</div>'
            "</div>"
        ) % (
            self._build_device_test_dashboard_card(
                "Estado",
                state_payload["label"],
                state_body,
                tone=state_payload["tone"],
                variant="header",
                icon_class="fa-link",
            ),
            self._build_device_test_dashboard_card(
                "Dispositivo",
                device_title,
                device_body,
                tone="neutral",
                variant="header",
                icon_class="fa-mobile",
            ),
            self._build_device_test_dashboard_card(
                "Última actividad",
                update_title,
                update_body,
                tone="neutral",
                variant="header",
                icon_class="fa-clock-o",
            ),
        )

    def _build_device_test_results_summary_html(self, ok_count, fail_count, pending_count, unavailable_count):
        self.ensure_one()
        return Markup(
            '<div style="display:flex;flex-direction:column;gap:12px;">'
            '%s%s%s%s'
            "</div>"
        ) % (
            self._build_device_test_dashboard_card(
                "Correctas",
                str(ok_count),
                "Pruebas completadas correctamente",
                tone="success",
                variant="compact",
                icon_class="fa-check",
            ),
            self._build_device_test_dashboard_card(
                "Fallidas",
                str(fail_count),
                "Pruebas con fallo confirmado o error",
                tone="danger",
                variant="compact",
                icon_class="fa-times",
            ),
            self._build_device_test_dashboard_card(
                "Pendientes",
                str(pending_count),
                "Pruebas aún no cerradas del todo",
                tone="warning",
                variant="compact",
                icon_class="fa-clock-o",
            ),
            self._build_device_test_dashboard_card(
                "No disponibles",
                str(unavailable_count),
                "Funciones que el dispositivo no expone",
                tone="neutral",
                variant="compact",
                icon_class="fa-ban",
            ),
        )

    def _build_device_test_categories_html(
        self,
        audio_summary,
        sensor_summary,
        thermal_summary,
        diagnostic_summary,
        battery_summary,
        network_summary,
        environment_summary,
    ):
        self.ensure_one()
        return Markup(
            '<div class="row g-3">'
            '<div class="col-lg-6">%s</div>'
            '<div class="col-lg-6">%s</div>'
            '<div class="col-lg-6">%s</div>'
            '<div class="col-lg-6">%s</div>'
            '<div class="col-lg-6">%s</div>'
            '<div class="col-lg-6">%s</div>'
            "</div>"
        ) % (
            self._build_device_test_dashboard_card(
                "Audio",
                "Altavoz y auricular",
                audio_summary,
                tone="success" if "fallo" not in audio_summary.lower() else "danger",
                variant="compact",
                icon_class="fa-volume-up",
            ),
            self._build_device_test_dashboard_card(
                "Sensores",
                "Proximidad, acelerómetro y giroscopio",
                sensor_summary,
                tone="success" if "fallo" not in sensor_summary.lower() else "danger",
                variant="compact",
                icon_class="fa-sliders",
            ),
            self._build_device_test_dashboard_card(
                "Térmico",
                "Información térmica",
                thermal_summary,
                tone="neutral",
                variant="compact",
                icon_class="fa-thermometer-half",
            ),
            self._build_device_test_dashboard_card(
                "Diagnóstico",
                "Diagnóstico básico recibido",
                diagnostic_summary,
                tone="info",
                variant="compact",
                icon_class="fa-flask",
            ),
            self._build_device_test_dashboard_card(
                "Batería",
                "Nivel de batería",
                battery_summary,
                tone="neutral",
                variant="compact",
                icon_class="fa-battery-half",
            ),
            self._build_device_test_dashboard_card(
                "Red y entorno",
                network_summary,
                environment_summary,
                tone="neutral",
                variant="compact",
                icon_class="fa-wifi",
            ),
        )

    def _build_device_test_environment_html(self, session):
        self.ensure_one()
        if not session:
            return False
        network = session.last_network_type or "Sin red registrada"
        battery = "%s%%" % session.last_battery_level if session.last_battery_level is not None else "Sin dato"
        storage_parts = []
        if session.last_storage_free_mb is not None:
            storage_parts.append("Libre %s MB" % session.last_storage_free_mb)
        if session.last_storage_total_mb is not None:
            storage_parts.append("Total %s MB" % session.last_storage_total_mb)
        storage_text = " · ".join(storage_parts) if storage_parts else "Sin almacenamiento reportado"
        thermal_text = session.last_thermal_status or "Sin estado térmico"
        if session.last_battery_temperature_c is not None:
            thermal_text = "%s · %.2f C" % (thermal_text, session.last_battery_temperature_c)
        return Markup(
            '<div class="row g-3">'
            '<div class="col-lg-4">%s</div>'
            '<div class="col-lg-4">%s</div>'
            '<div class="col-lg-4">%s</div>'
            "</div>"
        ) % (
            self._build_device_test_dashboard_card("Batería", battery, "Último nivel recibido desde Android", tone="neutral"),
            self._build_device_test_dashboard_card("Red", network, "Último tipo de conexión registrado", tone="neutral"),
            self._build_device_test_dashboard_card("Entorno", thermal_text, storage_text, tone="neutral"),
        )

    def _prepare_device_test_footer_payload(self):
        self.ensure_one()
        active_run = self._get_device_test_active_run()
        pairing_payload = self._get_device_test_pairing_payload(active_run)
        download_url = self._get_device_test_download_url()
        status_payload = self._get_device_test_footer_status_payload(active_run)
        public_base_url = self._get_device_test_public_base_url()
        return {
            "repair_order_id": self.id,
            "repair_order_name": self.display_name,
            "has_active_run": bool(active_run),
            "run_id": active_run.id if active_run else False,
            "run_name": active_run.display_name if active_run else "",
            "run_count": len(self.x_device_test_run_ids),
            "state": active_run.state if active_run else False,
            "state_label": status_payload["label"],
            "status_tone": status_payload["tone"],
            "session_id": active_run.session_id.id if active_run and active_run.session_id else False,
            "session_name": active_run.session_id.display_name if active_run and active_run.session_id else "",
            "pairing_code": active_run.pairing_code if active_run else "",
            "pairing_token_display": (
                active_run.pairing_token if active_run and active_run.show_pairing_token else self._get_device_test_masked_pairing_token(active_run)
            ),
            "show_pairing_token": bool(active_run and active_run.show_pairing_token),
            "download_url": download_url,
            "download_qr_url": self._get_device_test_qr_url(download_url),
            "pairing_qr_url": self._get_device_test_qr_url(pairing_payload),
            "public_base_url": public_base_url,
            "public_base_url_configured": bool(public_base_url),
            "pairing_ready": bool(active_run and pairing_payload),
            "can_start_run": not active_run,
            "can_open_run": bool(active_run),
            "can_restart_pairing": bool(active_run),
            "prepare_summary": "Descargar APK y vincular la app con esta reparación.",
            "operations_summary": "Control del run vinculado y acceso rápido a la revisión operativa.",
        }

    @api.depends(
        "x_device_test_run_ids",
        "x_device_test_run_ids.state",
        "x_device_test_run_ids.session_id",
        "x_device_test_run_ids.show_pairing_token",
        "x_device_test_run_ids.pairing_token",
        "x_device_test_run_ids.pairing_code",
        "x_device_test_run_ids.result_ids",
        "x_device_test_run_ids.result_ids.status",
        "x_device_test_run_ids.log_ids",
        "x_device_test_run_ids.log_ids.status",
        "x_device_test_run_ids.session_id.manufacturer",
        "x_device_test_run_ids.session_id.model",
        "x_device_test_run_ids.session_id.android_version",
        "x_device_test_run_ids.session_id.sdk_int",
        "x_device_test_run_ids.session_id.app_version",
        "x_device_test_run_ids.session_id.device_uuid",
        "x_device_test_run_ids.session_id.last_ping_at",
        "x_device_test_run_ids.session_id.last_diagnostic_at",
        "x_device_test_run_ids.session_id.last_test_at",
        "x_device_test_run_ids.session_id.last_status",
        "x_device_test_run_ids.session_id.last_message",
        "x_device_test_run_ids.session_id.last_battery_level",
        "x_device_test_run_ids.session_id.last_network_type",
        "x_device_test_run_ids.session_id.last_storage_free_mb",
        "x_device_test_run_ids.session_id.last_storage_total_mb",
        "x_device_test_run_ids.session_id.last_battery_temperature_c",
        "x_device_test_run_ids.session_id.last_thermal_status",
    )
    def _compute_device_test_run_data(self):
        for record in self:
            active_run = record._get_device_test_active_run()
            pairing_payload = record._get_device_test_pairing_payload(active_run)
            download_url = record._get_device_test_download_url()
            session = active_run.session_id if active_run else self.env["wex.device.test.session"]
            result_ids = active_run.result_ids if active_run else self.env["wex.device.test.result"]
            log_ids = active_run.log_ids if active_run else self.env["wex.device.test.log"]
            audio_results = result_ids.filtered(lambda result: result.test_type in ("speaker", "earpiece"))
            sensor_results = result_ids.filtered(
                lambda result: result.test_type in ("proximity", "accelerometer", "gyroscope")
            )
            thermal_results = result_ids.filtered(lambda result: result.test_type == "thermal_info")
            ok_count = 0
            fail_count = 0
            pending_count = 0
            unavailable_count = 0
            for result in result_ids:
                bucket = record._get_device_test_result_bucket(result.status)
                if bucket == "ok":
                    ok_count += 1
                elif bucket == "fail":
                    fail_count += 1
                elif bucket == "unavailable":
                    unavailable_count += 1
                else:
                    pending_count += 1
            latest_update_at = max(
                [
                    value
                    for value in [
                        session.last_test_at,
                        session.last_diagnostic_at,
                        session.last_ping_at,
                        active_run.paired_at if active_run else False,
                        active_run.started_at if active_run else False,
                    ]
                    if value
                ],
                default=False,
            )
            record.x_device_test_active_run_id = active_run
            record.x_device_test_run_count = len(record.x_device_test_run_ids)
            record.x_device_test_download_url = download_url
            record.x_device_test_download_qr_html = record._build_device_test_qr_html(
                record._get_device_test_qr_url(download_url),
                "APK download QR",
            )
            record.x_device_test_pairing_code = active_run.pairing_code or False
            record.x_device_test_pairing_token = active_run.pairing_token or False
            record.x_device_test_session_id = session
            record.x_device_test_result_ids = result_ids
            record.x_device_test_log_ids = log_ids
            record.x_device_test_result_count = len(result_ids)
            record.x_device_test_log_count = len(log_ids)
            record.x_device_test_show_pairing_token = bool(active_run.show_pairing_token)
            record.x_device_test_state = active_run.state or False
            record.x_device_test_pairing_payload = pairing_payload
            record.x_device_test_pairing_qr_html = record._build_device_test_qr_html(
                record._get_device_test_qr_url(pairing_payload),
                "Repair pairing QR",
            )
            record.x_device_test_show_preparation_panel = not active_run or active_run.state == "pending_pairing"
            record.x_device_test_show_operations_panel = bool(
                active_run and active_run.state in ("paired", "in_progress")
            )
            record.x_device_test_footer_allowed = record._has_device_test_access()
            record.x_device_test_device_uuid = session.device_uuid or False
            record.x_device_test_device_manufacturer = session.manufacturer or False
            record.x_device_test_device_model = session.model or False
            record.x_device_test_android_version = session.android_version or False
            record.x_device_test_sdk_int = session.sdk_int or False
            record.x_device_test_app_version = session.app_version or False
            record.x_device_test_last_ping_at = session.last_ping_at or False
            record.x_device_test_last_diagnostic_at = session.last_diagnostic_at or False
            record.x_device_test_last_test_at = session.last_test_at or False
            record.x_device_test_last_status = session.last_status or False
            record.x_device_test_last_message = session.last_message or False
            record.x_device_test_last_battery_level = session.last_battery_level
            record.x_device_test_last_network_type = session.last_network_type or False
            record.x_device_test_last_storage_free_mb = session.last_storage_free_mb
            record.x_device_test_last_storage_total_mb = session.last_storage_total_mb
            record.x_device_test_last_battery_temperature_c = session.last_battery_temperature_c
            record.x_device_test_last_thermal_status = session.last_thermal_status or False
            record.x_device_test_results_ok_count = ok_count
            record.x_device_test_results_fail_count = fail_count
            record.x_device_test_results_pending_count = pending_count
            record.x_device_test_results_unavailable_count = unavailable_count
            record.x_device_test_latest_update_at = latest_update_at or False
            record.x_device_test_audio_summary = record._format_device_test_category_summary(
                "Audio",
                audio_results,
            )
            record.x_device_test_sensor_summary = record._format_device_test_category_summary(
                "Sensores",
                sensor_results,
            )
            record.x_device_test_thermal_summary = record._format_device_test_category_summary(
                "Térmico",
                thermal_results,
            )
            if session.last_diagnostic_at:
                record.x_device_test_diagnostic_summary = (
                    "Diagnóstico recibido el %s"
                    % record._format_device_test_datetime(session.last_diagnostic_at)
                )
            else:
                record.x_device_test_diagnostic_summary = "Diagnóstico pendiente"
            record.x_device_test_overview_html = record._build_device_test_overview_html(
                active_run,
                session,
                latest_update_at,
            ) if session else False
            record.x_device_test_results_summary_html = record._build_device_test_results_summary_html(
                ok_count,
                fail_count,
                pending_count,
                unavailable_count,
            ) if session else False
            battery_summary = (
                "%s%% recibido desde Android" % session.last_battery_level
                if session.last_battery_level is not None
                else "Sin nivel reportado"
            )
            network_summary = session.last_network_type or "Sin red registrada"
            storage_parts = []
            if session.last_storage_free_mb is not None:
                storage_parts.append("Libre %s MB" % session.last_storage_free_mb)
            if session.last_storage_total_mb is not None:
                storage_parts.append("Total %s MB" % session.last_storage_total_mb)
            environment_summary = " · ".join(storage_parts) if storage_parts else "Sin almacenamiento reportado"
            if session.last_thermal_status:
                environment_summary = "%s · %s" % (session.last_thermal_status, environment_summary)
            record.x_device_test_categories_html = record._build_device_test_categories_html(
                record.x_device_test_audio_summary,
                record.x_device_test_sensor_summary,
                record.x_device_test_thermal_summary,
                record.x_device_test_diagnostic_summary,
                battery_summary,
                network_summary,
                environment_summary,
            ) if session else False
            record.x_device_test_environment_html = record._build_device_test_environment_html(session)

    def action_get_device_test_footer_data(self):
        self.ensure_one()
        self._ensure_device_test_access()
        return self._prepare_device_test_footer_payload()

    def action_start_device_test_run(self):
        self.ensure_one()
        active_run = self._get_device_test_active_run()
        if active_run:
            return self.action_open_device_test_run()

        run = self.env["wex.device.test.run"].create(
            {
                "repair_order_id": self.id,
                "user_id": self.env.user.id,
            }
        )
        run.action_start_pairing()
        return run._get_open_action()

    def action_footer_start_device_test_run(self):
        self.ensure_one()
        self._ensure_device_test_access()
        active_run = self._get_device_test_active_run()
        if not active_run:
            active_run = self.env["wex.device.test.run"].create(
                {
                    "repair_order_id": self.id,
                    "user_id": self.env.user.id,
                }
            )
            active_run.action_start_pairing()
        return self._prepare_device_test_footer_payload()

    def action_open_device_test_run(self):
        self.ensure_one()
        active_run = self.x_device_test_active_run_id or self._get_device_test_active_run()
        if not active_run and self.x_device_test_run_ids:
            active_run = self.x_device_test_run_ids.sorted(
                key=lambda run: (run.started_at or fields.Datetime.now(), run.id),
                reverse=True,
            )[:1]
        if not active_run:
            return False
        return active_run._get_open_action()

    def action_restart_active_device_test_pairing(self):
        self.ensure_one()
        active_run = self.x_device_test_active_run_id or self._get_device_test_active_run()
        if active_run:
            active_run.action_start_pairing()
        return False

    def action_footer_restart_active_device_test_pairing(self):
        self.ensure_one()
        self._ensure_device_test_access()
        active_run = self.x_device_test_active_run_id or self._get_device_test_active_run()
        if active_run:
            active_run.action_start_pairing()
        return self._prepare_device_test_footer_payload()

    def action_show_active_device_test_token(self):
        self.ensure_one()
        active_run = self.x_device_test_active_run_id or self._get_device_test_active_run()
        if active_run:
            active_run.action_show_pairing_token()
        return False

    def action_footer_show_active_device_test_token(self):
        self.ensure_one()
        self._ensure_device_test_access()
        active_run = self.x_device_test_active_run_id or self._get_device_test_active_run()
        if active_run:
            active_run.action_show_pairing_token()
        return self._prepare_device_test_footer_payload()

    def action_hide_active_device_test_token(self):
        self.ensure_one()
        active_run = self.x_device_test_active_run_id or self._get_device_test_active_run()
        if active_run:
            active_run.action_hide_pairing_token()
        return False

    def action_footer_hide_active_device_test_token(self):
        self.ensure_one()
        self._ensure_device_test_access()
        active_run = self.x_device_test_active_run_id or self._get_device_test_active_run()
        if active_run:
            active_run.action_hide_pairing_token()
        return self._prepare_device_test_footer_payload()
