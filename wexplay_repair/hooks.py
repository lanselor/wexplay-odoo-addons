from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    repair_picking_types = env["stock.picking.type"].sudo().search([
        ("code", "=", "repair_operation"),
    ])
    sequences = repair_picking_types.mapped("sequence_id").exists()

    if not sequences:
        return

    sequences.write({
        "prefix": "SAT/%(y)s",
        "padding": 6,
        "suffix": False,
    })
