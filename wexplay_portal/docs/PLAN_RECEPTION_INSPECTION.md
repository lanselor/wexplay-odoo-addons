# Portal inspection implementation plan

- models/repair_order.py: _get_portal_reception_inspection_values authorizes repair
  access; _get_portal_signed_reception_inspection resolves the optional frozen
  source; _prepare_portal_inspection_values returns explicit safe display values.
- controllers/portal.py: add the prepared values after existing authorized lookup.
- views/portal_templates.xml: card inside Ficha, native details/summary for faces.
- static/src/scss/portal.scss: scoped source/tag/figure styles and mobile stacking.
- tests: ORM access, source precedence, empty and legacy data, field restrictions,
  HTTP foreign SAT/anonymous access and safe escaping in rendered Ficha.
- Update architecture/decisions/changelog/ficha; test isolated DBs with and without
  consent, then visually review the real portal page. No production deployment.

## Confirmación final — 17/10/2026

Funcionamiento confirmado por el usuario tras la integración completa. La
[guía consolidada](../../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md) recoge las
reglas vigentes y sus diferencias documentales. Los resultados de pruebas descritos
corresponden a las ejecuciones anteriores; no se han repetido en esta tarea de
documentación. No se registra como realizada una prueba física específica de tablet.
