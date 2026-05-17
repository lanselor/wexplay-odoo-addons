from odoo import fields, models, _
from odoo.exceptions import UserError


class WexTeardownRejectWizard(models.TransientModel):
    _name = "wex.teardown.reject.wizard"
    _description = "Asistente de rechazo de pieza"

    line_id = fields.Many2one("wex.teardown.line", string="Pieza", required=True, ondelete="cascade")
    qc_state = fields.Selection(
        [
            ("fail", "No apta"),
            ("not_applicable", "No recuperada / No aplica"),
        ],
        string="Resultado del control",
        default="fail",
        required=True,
    )
    discard_reason = fields.Selection(
        [
            ("broken", "Rota"),
            ("missing", "No recuperada"),
            ("not_useful", "No útil"),
            ("duplicate", "Duplicada"),
            ("other", "Otro"),
        ],
        string="Motivo de descarte",
        required=True,
        default="broken",
    )
    qc_notes = fields.Text(string="Notas de control de calidad")
    discard_notes = fields.Text(string="Notas de descarte")

    def action_confirm_rejection(self):
        self.ensure_one()
        if not self.line_id:
            raise UserError(_("No se ha encontrado la pieza a rechazar."))
        self.line_id._mark_qc(self.qc_state)
        self.line_id.write(
            {
                "discard_reason": self.discard_reason,
                "qc_notes": self.qc_notes,
                "discard_notes": self.discard_notes,
            }
        )
        return {"type": "ir.actions.act_window_close"}
