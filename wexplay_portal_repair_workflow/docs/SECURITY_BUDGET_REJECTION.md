# SECURITY ANALYSIS — Motivo de rechazo

Fecha: 2026-11-01. Autor/revisor: Codex. Cambio: portal autenticado.

## Grupos, modelos y reglas
base.group_portal aporta texto solo sobre SAT autorizado por commercial_partner_id y estado pendiente. base.group_user consulta la nota interna. Sin modelos, campos, ACL, grupos o record rules nuevos. repair.order conserva la validación de acceso del portal; mail.message se crea exclusivamente desde el backend encapsulado.

## Ruta y validaciones
POST /my/repairs/<int:repair_id>/budget/reject, auth=user y CSRF nativo. El controlador aplica búsqueda autorizada (404 ajeno), el modelo comprueba grupo portal y pertenencia, y vuelve a hacerlo en cursor aislado antes de escribir. Motivo: str opcional, hasta 4000 caracteres, strip; valor no válido falla antes del workflow.

## Privilegios y SQL
Se reutiliza el cursor superusuario preexistente tras acceso validado, sobre un SAT concreto. SQL parametrizado exclusivamente para bloqueo de esa fila, justificado en ADR-001. No hay endpoint de chatter, DMS, adjuntos, token ni acceso público nuevo.

## Texto y datos personales
Markup solo envuelve estructura HTML constante; interpolación y join de Markup escapan motivo y nombre. Saltos de línea se representan con br seguros. Nota mail.mt_note sin destinatarios explícitos y mail_create_nosubscribe; el contacto portal queda como autor sin suscripción automática. El texto se conserva según política existente del chatter; no se copia a logs ni eventos. Sin ficheros, secretos, APIs externas o cambios de consentimiento.

## Riesgos y verificación
Tests de partner ajeno, texto malicioso, longitud, doble envío y rollback incluidos. La nota interna no habilita lectura del chatter al portal. Concurrencia real entre cursores verificada. Pendiente prueba HTTP con sesión real en navegador de desarrollo.
