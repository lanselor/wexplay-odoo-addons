# Test y revisión — Motivo del rechazo

Fecha: 2026-11-01. Ejecutor/revisor: Codex. Entorno: base nueva local wex_test_portal_rejection_02c5a6ed, datos ficticios; sin producción.

## Resultados
- Instalación limpia del módulo y dependencias: correcta.
- 15 tests del workflow: correctos, incluyendo aceptación existente, rechazo libre/vacío, límites, HTML escapado, partner ajeno, nota interna sin notificación al contacto, envío repetido y rollback si falla la nota.
- 3 tests del dashboard: correctos. Antes de ejecutarlos se retiraron eventos y estados pendientes de los fixtures confirmados de concurrencia; esos datos alteraban los contadores globales esperados.
- Dos peticiones reales concurrentes al método público con cursores independientes: un éxito y un bloqueo, exactamente una nota/evento, SAT rechazado y cotización cancelada.
- Fallo provocado de publicación usando el cursor aislado real: SAT pendiente, cotización en borrador y ningún evento/nota.
- JavaScript: sugerencias, cambio de opción, conservación de texto personalizado, otro motivo y bloqueo del segundo envío, correctos mediante ejecución del widget con DOM simulado.
- Sintaxis Python, XML, estructura del formulario, CSRF y diff --check: correctos.

## Ajustes de pruebas
SavepointCase ya no existe en Odoo 18 instalado; ambos archivos usan TransactionCase. Los tests ORM sustituyen la apertura de cursor para poder usar fixtures no confirmados y ejecutan la misma unidad de workflow real. Las comprobaciones adicionales de concurrencia y rollback usan el aislamiento real, sin esa sustitución.

## Revisión del diff
Aceptado: alcance limitado al módulo puente, sin nuevos permisos/modelos/campos ni dependencias, entrada escapada, SQL parametrizado de bloqueo justificado por ADR, workflow conservado. No se modificaron cambios ajenos en wex_payment_redsys.

## Límites
Pendiente revisión visual en navegador (escritorio/móvil) y prueba HTTP integral con sesión/CSRF. No se ha actualizado ningún servicio ni base de producción. Evidencias y scripts: addons-wexplay/_workspace/portal_rejection/.
