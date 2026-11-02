# Plan de ejecución — Motivo de rechazo

Fecha: 2026-11-01. Autor: Codex. Plan aprobado en chat. SPEC: SPEC_BUDGET_REJECTION.md. Arquitectura: ADR-001_BUDGET_REJECTION.md y ../ARCHITECTURE.md.

## Objetivo y alcance
Obtener feedback opcional al rechazar, con tarjeta interna y sin modelos nuevos. Sin analítica ni cambios de aceptación.

## Archivos y fases
1. Servidor (esfuerzo pequeño): models/repair_order.py valida, ejecuta y publica; controllers/portal.py recoge texto. Métodos: _check_portal_rejection_reason, _post_portal_budget_rejection, _apply_portal_budget_workflow_action; ampliar action_portal_reject_budget y _run_portal_budget_workflow_action.
2. Interfaz (esfuerzo pequeño): views/portal_repair_workflow_templates.xml amplía modal; nuevo static/src/js/portal_budget_rejection.js gestiona sugerencias/envío; __manifest__.py registra asset y versión.
3. Verificación (esfuerzo medio): tests/test_portal_budget_workflow.py cubre rechazo y seguridad. Migrar sus tests y test_portal_dashboard.py de SavepointCase inexistente en Odoo 18 a TransactionCase.
4. Documentación (esfuerzo pequeño): docs/SPEC_BUDGET_REJECTION.md, docs/ADR-001_BUDGET_REJECTION.md, docs/SECURITY_BUDGET_REJECTION.md, este plan y docs/TEST_BUDGET_REJECTION.md; actualizar ARCHITECTURE.md, ficha YAML/HTML y changelog raíz.

## Dependencias y rollback
Dependencias actuales, disponibles en local; sin instalaciones externas nuevas. Revertir archivos del cambio y actualizar módulo/assets; conservar mensajes históricos, sin desinstalar ni destruir datos. Copias previas en archivos obsoletos/2026-11-01. No tocar producción.

## Revisión
Codex revisa diff, sintaxis, límites de privilegios y pruebas. Evidencia y límites en TEST_BUDGET_REJECTION.md.
