from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """
    Ajusta el formato del identificador SAT para las órdenes de reparación
    sin resetear el contador existente.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Modelo de órdenes de reparación
    RepairOrder = env["mrp.repair"]

    # Obtenemos una orden cualquiera para acceder a su secuencia
    repair = RepairOrder.search([], limit=1)

    if not repair or not repair.sequence_id:
        return  # nada que hacer, evitamos romper nada

    seq = repair.sequence_id

    values = {
        "prefix": "SAT%(y)s",
        "padding": 6,
        "suffix": False,
    }

    seq.write(values)
