from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Buscamos la secuencia RO por nombre (tu caso: sin "code")
    seq = env["ir.sequence"].sudo().search([
        ("name", "ilike", "Secuencia RO"),
    ], limit=1)

    if not seq:
        return

    # No tocamos number_next (contador). Solo formato.
    seq.write({
        "prefix": "SAT/%(y)s",
        "padding": 6,
        "suffix": False,
    })
