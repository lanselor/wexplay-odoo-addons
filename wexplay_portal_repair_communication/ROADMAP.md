# Roadmap tecnico - Wexplay Portal Repair Communication

## Fase 1 - Base documental y frontera modular

Objetivo: dejar fijada la arquitectura antes de implementar logica.

- Crear modulo propio `wexplay_portal_repair_communication`.
- Documentar que el modulo es dueno de la conversacion.
- Separar de forma explicita chatter interno y conversacion SAT-cliente.
- Fijar unidad funcional: un hilo por `repair.order`.
- Fijar ownership y fallback: responsable, gerente, administrador.

## Fase 2 - Modelo funcional v1

Objetivo: construir la verdad funcional de la conversacion.

- Crear el modelo de conversacion SAT.
- Crear el modelo de mensajes de conversacion.
- Guardar estado operativo de respuesta.
- Guardar ultimas fechas de interaccion cliente y tecnico.
- Preparar proyeccion a superficies portal y backend sin duplicar la logica.

## Fase 3 - Portal cliente v1

Objetivo: permitir al cliente escribir desde su SAT en portal.

- Burbuja contextual inferior derecha en la ficha SAT.
- Historial completo de conversacion del SAT.
- Composer simple de mensaje.
- Respeto estricto de seguridad por `commercial_partner_id`.
- Desactivar escritura cuando el SAT quede fuera de garantia.

## Fase 4 - Backend tecnico v1

Objetivo: dar visibilidad real al tecnico sin depender del chatter bruto.

- Mostrar panel inferior especifico en `repair.order`.
- Separar visualmente chatter Odoo y conversacion SAT.
- Abrir la conversacion al tecnico como chat normal de Odoo.
- Mostrar lateral contextual con informacion relevante del SAT.
- Anadir menu `Conversaciones pendientes` en `Portal clientes`.

## Fase 5 - Endurecimiento v1.1

Objetivo: cerrar riesgos operativos y de seguridad.

- Probar cambio de responsable con conversacion ya viva.
- Probar fallback a gerente y a administrador.
- Revisar datos sensibles en portal y lateral.
- Validar que no se mezclan logs del chatter con mensajes SAT.
- Revisar ergonomia de lectura del historico por fecha.

## Fase 6 - V2 obligatoria

Objetivo: evitar mensajes olvidados aunque el tecnico haya visto la conversacion.

- Relanzar aviso si un mensaje del cliente queda sin responder durante X tiempo.
- Permitir marcar `No es necesaria contestacion`.
- Mantener la conversacion como pendiente hasta responder o marcarla.
- Estudiar acciones rapidas desde el panel lateral del chat.

## Fuera de alcance por ahora

- adjuntos
- reglas completas de intercambio documental
- integracion nueva con WhatsApp
- acciones masivas o automatizaciones complejas de SLA
