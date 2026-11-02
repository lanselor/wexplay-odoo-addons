# ADR-001 — Rechazo y comentario en la transacción backend existente

Fecha: 2026-11-01. Estado: aceptado. Autor/revisor: Codex. Módulo: wexplay_portal_repair_workflow.

## Contexto
El presupuesto se procesa con Environment superusuario y cursor separado para evitar recomputaciones comerciales con permisos portal. Publicar después desde el controlador podría dejar un rechazo sin comentario.

## Decisión y razonamiento
Pasar el texto normalizado como argumento explícito, sin añadirlo al contexto ni a logs. Ejecutar workflow, evento y nota interna dentro del mismo cursor y antes del commit ya existente. Revalidar acceso comercial y estado con el usuario real cargado en ese cursor. Se mantiene el aislamiento existente; no se añaden commits.

Una consulta SQL parametrizada SELECT FOR UPDATE bloquea únicamente la fila SAT para serializar rechazos concurrentes. Es una operación de bloqueo sin equivalente ORM, no una consulta de negocio; se invalidan valores ORM antes de validar. En aislamiento repeatable read, un conflicto de serialización revierte la operación; no se captura como éxito. Dos solicitudes no deben publicar dos notas.

## Alternativas descartadas
Guardar texto en campo SAT duplica la fuente de verdad solicitada. Publicar fuera de la transacción no garantiza atomicidad. Rehacer todo el aislamiento comercial ampliaría el alcance.

## Consecuencias
Sin migración de datos. Rollback de código y actualización del módulo conserva notas históricas. Los tests transaccionales sustituyen únicamente la apertura de cursor por la misma unidad de ejecución backend sobre fixtures sin confirmar; no validan por sí solos concurrencia real entre procesos.
