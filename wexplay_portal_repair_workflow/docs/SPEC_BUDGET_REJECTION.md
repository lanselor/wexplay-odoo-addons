# SPEC — Motivo del rechazo de presupuesto

Fecha: 2026-11-01. Autor: Codex. Versión: 1.0. Estado: aprobada mediante el plan del chat y la petición de implementación.
Módulo: wexplay_portal_repair_workflow. ADR: ADR-001_BUDGET_REJECTION.md.

## Problema y contexto
Los rechazos del portal no explican por qué el cliente descarta la reparación. Ya existe una modal de confirmación y un workflow backend aislado; se amplían sin cambiar las reglas SAT.

## Usuarios y solución
El cliente B2B autenticado puede aportar un comentario opcional al rechazar su presupuesto. El equipo interno consulta el comentario en el chatter del SAT.

## Reglas de negocio
| ID | Regla | Condición | Acción | Origen |
|---|---|---|---|---|
| REJ001 | Motivo opcional | Confirmar rechazo | Guardar texto o indicar ausencia de motivo | Plan aprobado |
| REJ002 | Sugerencias editables | Elegir motivo | Autocompletar solo si vacío o sin cambios personales | Plan aprobado |
| REJ003 | Cancelación inocua | Cancelar modal | No enviar ni guardar | Plan aprobado |
| REJ004 | Nota interna | Rechazo válido | Una tarjeta con autor, origen y texto seguro | Plan aprobado |
| REJ005 | Atomicidad | Error al guardar nota | Revertir rechazo, cancelación comercial y evento | Plan aprobado |

## Caso principal
Abrir presupuesto pendiente, pulsar rechazar, elegir precio/sustitución/plazo/ya no necesario/otro, editar opcionalmente y confirmar. Queda rechazado con cotización cancelada, evento existente y nota interna. Cancelar permite volver sin cambios.

## Criterios de aceptación
- Selector con las cinco opciones del plan y texto libre editable, máximo 4000 caracteres en navegador y servidor.
- Cambiar sugerencia conserva texto personalizado; otro motivo permite escribir libremente.
- Sin motivo se registra explícitamente su ausencia.
- No se permite actuar sobre otro partner comercial ni repetir rechazo ya realizado.
- El contenido HTML se muestra como texto, preservando saltos de línea.
- La nota no notifica al cliente ni lo suscribe al chatter.
- Un fallo de la nota no deja un rechazo parcial.

## Fuera de alcance y dependencias
Sin campos/modelos nuevos, analítica de motivos, correo nuevo, cambios DMS o ampliaciones ACL. Dependencias existentes del módulo, sin nuevas integraciones OCA. No se cambia aceptación.

## Riesgos y pendientes
Concurrencia y privilegios: revalidar en transacción aislada y serializar rechazo por SAT. Prueba visual y HTTP integral pendientes en navegador de desarrollo; concurrencia real entre procesos verificada; no operar producción.
