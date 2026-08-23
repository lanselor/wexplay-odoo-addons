# -*- coding: utf-8 -*-

from odoo import _, fields, models


class RepairSatReportNotesWizard(models.TransientModel):
    _name = "wex.repair.sat.report.notes.wizard"
    _description = "Notas complementarias del informe SAT"

    repair_id = fields.Many2one(
        "repair.order",
        string="Orden de reparación",
        required=True,
        readonly=True,
    )
    notes = fields.Text(string="Notas complementarias")

    def action_save(self):
        self.ensure_one()
        repair = self.repair_id
        current_notes = repair.x_sat_report_notes or ""
        updated_notes = self.notes or ""
        if current_notes == updated_notes:
            return {"type": "ir.actions.act_window_close"}

        repair.write({"x_sat_report_notes": updated_notes or False})
        repair._regenerate_sat_report_after_notes_update()
        return {"type": "ir.actions.act_window_close"}
