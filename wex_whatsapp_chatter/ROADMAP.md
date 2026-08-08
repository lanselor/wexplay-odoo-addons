# Roadmap tecnico - Wex WhatsApp Chatter

## Fase 0 - Documentacion e higiene

Objetivo: dejar el modulo entendible y limpiar artefactos sin alterar comportamiento funcional.

Estado: completada.

Tareas:

- Documentar objetivo, alcance y limites.
- Documentar arquitectura y responsabilidades.
- Documentar deuda detectada.
- Eliminar artefactos tecnicos generados fuera de fuente viva.
- Retirar logs debug de assets.

## Fase 1 - Modelos soportados y disponibilidad desde Contactos

Objetivo: asegurar que el modulo funciona de forma clara solo en modelos soportados y que Contactos esta incluido correctamente.

Estado: completada y validada funcionalmente.

Tareas:

- Confirmar `res.partner` como modelo soportado desde chatter y wizard.
- Revisar por que el boton o flujo puede no aparecer desde Contactos.
- Evitar apertura inconsistente desde modelos no soportados.
- Mantener `sale.order`, `account.move`, `repair.order` y `res.partner` como alcance actual.

## Fase 2 - Correccion del origen de telefono

Objetivo: corregir el bug detectado al cambiar entre `mobile`, `phone` y `custom`.

Estado: completada y validada funcionalmente.

Tareas:

- Revisar onchange de `partner_id`.
- Anadir onchange especifico de `phone_source`.
- Definir comportamiento esperado:
  - `mobile`: usar movil del contacto.
  - `phone`: usar telefono fijo del contacto.
  - `custom`: permitir escribir manualmente sin sobrescritura inesperada.
- Evitar que cambios de plantilla o documento pisen el telefono personalizado.

## Fase 3 - Separacion interna del wizard

Objetivo: reducir riesgo y mejorar mantenibilidad sin cambiar UX.

Estado: completada.

Tareas:

- Extraer resolucion del documento origen.
- Extraer normalizacion de telefono.
- Extraer render de plantillas.
- Extraer preparacion de nota chatter.
- Revisar divergencia entre `whatsapp.template.render_body()` y `_render_text()`.

## Fase 4 - Limpieza de vistas y ayuda de variables

Objetivo: hacer las vistas mas mantenibles.

Estado: completada parcialmente.

Tareas:

- Alinear variables documentadas con variables realmente soportadas. Completado.
- Implementar `${importe}` como alias real. Completado.
- Anadir `${referencia_cliente}` para SAT. Completado.
- Anadir `${notasreparacion}` para `repair.order.internal_notes`. Completado.
- Reducir estilos inline. Pendiente.
- Mover ayuda larga de variables a un componente o estructura mas mantenible si crece. Pendiente.

## Fase 5 - Enlaces de portal seguros

Objetivo: evitar envio accidental de enlaces de documentos de otro cliente y separar portal nativo de portal B2B Wexplay.

Estado: completada y validada funcionalmente.

Tareas:

- Anadir tipo de enlace a insertar.
- Filtrar cotizaciones y facturas por cliente.
- Validar en Python que el documento elegido pertenece al cliente.
- Mantener `wex_whatsapp_chatter` sin dependencia dura con `wexplay_portal`.
- Crear modulo puente opcional para enlace B2B SAT.

## Fase 6 - Seguridad visual del mensaje

Objetivo: reducir errores humanos antes de abrir WhatsApp.

Estado: completada y validada funcionalmente.

Tareas:

- Mostrar previsualizacion tipo WhatsApp.
- Bloquear apertura si quedan variables `${...}` sin resolver.
- Reforzar la trazabilidad visual del chatter con etiqueta reconocible.
- Implementar `${importe}` y posicionamiento de enlaces por placeholder.
- Mantener `${portal_url}` para portal nativo y `${enlaceportalB2B}` en modulo puente.

## Siguiente iteracion recomendada

Objetivo: mejorar mantenibilidad sin aumentar acoplamiento ni convertir el modulo en una API de mensajeria.

Tareas propuestas:

- Separar la ayuda de variables en una estructura mas facil de mantener si sigue creciendo.
- Revisar convergencia entre `whatsapp.template.render_body()` y `whatsapp.compose.wizard._render_text()`.
- Revisar el widget `wex_whatsapp_template_picker` antes de cada actualizacion de Odoo y reemplazar la copia del template Many2One cuando exista un punto de extension local suficiente.
- Centralizar o probar conjuntamente los grupos de plantilla definidos en Python y JavaScript antes de ampliar categorias.
- Refactorizar `whatsapp.compose.wizard.write()` a batch solo si el wizard pasa a reutilizarse en operaciones multiples; no adelantar esa complejidad para el flujo actual singleton.
- Evaluar historial/estadisticas internas de mensajes preparados sin afirmar envio real.
- Revisar permisos granulares si en el futuro hay plantillas sensibles por area o equipo.
- Mantener cualquier integracion nueva de portal, SAT u otros modulos mediante puente opcional cuando la dependencia no sea obligatoria.
