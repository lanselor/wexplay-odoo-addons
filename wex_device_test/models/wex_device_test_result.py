import json

from odoo import api, fields, models


class WexDeviceTestResult(models.Model):
    _name = "wex.device.test.result"
    _description = "Wex Device Test Result"
    _order = "executed_at desc, id desc"

    session_id = fields.Many2one(
        "wex.device.test.session",
        required=True,
        ondelete="cascade",
        index=True,
        readonly=True,
    )
    run_id = fields.Many2one(
        "wex.device.test.run",
        index=True,
        readonly=True,
        ondelete="set null",
    )
    test_type = fields.Selection(
        selection=[
            ("speaker", "Speaker"),
            ("earpiece", "Earpiece"),
            ("proximity", "Proximity"),
            ("accelerometer", "Accelerometer"),
            ("gyroscope", "Gyroscope"),
            ("thermal_info", "Thermal Info"),
        ],
        required=True,
        readonly=True,
    )
    status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("played", "Played"),
            ("confirmed_ok", "Confirmed OK"),
            ("confirmed_fail", "Confirmed Fail"),
            ("available", "Available"),
            ("not_available", "Not Available"),
            ("detected", "Detected"),
            ("not_detected", "Not Detected"),
            ("error", "Error"),
        ],
        required=True,
        readonly=True,
    )
    message = fields.Char(required=True, readonly=True)
    technical_details = fields.Text(readonly=True)
    measurement_json = fields.Text(readonly=True)
    executed_at = fields.Datetime(required=True, readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        readonly=True,
        index=True,
    )

    @api.model
    def _prepare_measurement_json(self, measurements):
        if not measurements:
            return False
        return json.dumps(measurements, sort_keys=True, ensure_ascii=False, indent=2)

    @api.model
    def create_result(
        self,
        session,
        test_type,
        status,
        message,
        executed_at,
        measurements=None,
        technical_details=None,
        run=None,
    ):
        return self.create(
            {
                "session_id": session.id,
                "run_id": run.id if run else False,
                "test_type": test_type,
                "status": status,
                "message": message,
                "technical_details": technical_details,
                "measurement_json": self._prepare_measurement_json(measurements),
                "executed_at": executed_at,
                "company_id": session.company_id.id,
            }
        )
