# Wexplay Portal

## Objetivo

`wexplay_portal` es la capa puente entre el portal nativo de Odoo y los modulos de negocio Wexplay.

En esta primera fase solo cubre el portal B2B autenticado para clientes empresa:

- reutiliza el portal estandar de facturas de `account`
- expone un listado y detalle de SAT sobre `repair.order`
- prepara una entrada futura para mantenimiento IT

No implementa acceso por token, vistas publicas ni logica B2C.

## Documentacion de arquitectura

Las decisiones mas importantes de negocio, seguridad, limites de alcance y
restricciones del portal se documentan en:

- `ARCHITECTURE.md`

Ese documento debe tratarse como la referencia principal antes de abrir nuevas
iteraciones del portal.

## Dependencias

- `portal`
- `website`
- `account`
- `wexplay_repair`

No declara dependencias Python externas.

## Decisiones clave

- No se mete logica portal dentro de `wexplay_repair`.
- La seguridad de SAT se apoya en ACL de solo lectura para portal + record rule por partner comercial.
- Los controladores no usan `sudo()`.
- Las vistas portal solo muestran campos seguros y evitan notas internas, chatter, followers y adjuntos.
- La integracion IT es opcional de verdad: solo aparece la entrada si existe el campo `x_is_it_maintenance_customer` y esta activado.

## Rutas

- `/my/invoices`: portal estandar de facturas reutilizado
- `/my/repairs`: listado SAT
- `/my/repairs/<id>`: detalle SAT
- `/my/it-maintenance`: placeholder de futura integracion

## Limites del MVP

- Sin documentos SAT descargables desde portal
- Sin adjuntos
- Sin chatter
- Sin firmas ni consentimientos
- Sin funcionalidad operativa de mantenimiento IT

## Check de seguridad aplicado

- acceso por URL manual a SAT ajenos: bloqueado por dominio y record rule
- listados cruzados entre clientes: bloqueados por partner comercial
- sin `sudo()` en controladores portal
- sin exponer relaciones indirectas sensibles
- sin contadores globales fuera del dominio accesible
