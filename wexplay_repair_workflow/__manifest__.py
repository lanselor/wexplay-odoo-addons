# -*- coding: utf-8 -*-
{
    "name": "Wexplay - Repair Workflow",
    "version": "18.0.1.0.0",
    "category": "Repair",
    "summary": "Subflujo de diagnóstico y presupuesto para SAT en reparaciones",
    "description": """
Subflujo de presupuesto/diagnóstico para repair.order en Odoo 18 Community.

Incluye:
- flujo de presupuesto
- sincronización de ubicación SAT
- decisión Mesa Pegado al finalizar
- acción Pendiente de repuesto desde la pestaña Piezas
    """,
    "author": "Wexplay",
    "license": "LGPL-3",
    "depends": [
        "repair",
        "mail",
        "wexplay_repair",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/repair_order_views.xml",
        "wizard/finish_repair_glue_choice_views.xml",
        "wizard/waiting_spare_confirm_views.xml",
    ],
    "installable": True,
    "application": False,
}