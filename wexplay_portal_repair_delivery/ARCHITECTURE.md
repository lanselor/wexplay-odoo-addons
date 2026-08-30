# Wexplay Portal - Repair Delivery

## Objetivo

`wexplay_portal_repair_delivery` es el modulo puente entre el portal B2B y la
logistica SAT de `wexplay_repair_delivery`.

Expone una pestana de consulta en la ficha de reparacion cuando la reparacion
tiene activa la gestion logistica. El cliente puede consultar exclusivamente
las operaciones de recogida y entrega creadas por Wexplay, descargar sus
etiquetas cuando existan y abrir el seguimiento externo de MRW cuando este
disponible.

Cuando la compañía activa los avisos automáticos, el módulo encola un correo
individual para cada usuario portal activo de la empresa comercial de la
reparación. El correo incluye datos operativos, seguimiento MRW y un enlace
autenticado al SAT; no adjunta la etiqueta. Un registro por operación y usuario
evita avisos duplicados. El envío manual del conector MRW sigue siendo un flujo
independiente para excepciones.

## Limites

El modulo no permite crear, modificar, cancelar ni solicitar operaciones
logisticas desde portal. Tampoco expone errores de integracion, numeros internos
de solicitud MRW ni adjuntos genericos.

El aviso automático solo se considera preparado cuando existe referencia MRW y
etiqueta. La configuración se controla por compañía desde Ajustes SAT y queda
desactivada por defecto.

## Seguridad

Todas las rutas parten de la reparacion visible para el `commercial_partner_id`
del usuario portal. La descarga valida ademas que la operacion solicitada es la
recogida o entrega de esa misma reparacion. El binario de la etiqueta solo se
lee dentro de un helper de modelo, despues de esa validacion, y nunca se publica
mediante una ruta generica de adjuntos.
