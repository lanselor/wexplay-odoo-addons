# AGENTS.md

## Objetivo del proyecto
Módulo Odoo 18 Community para gestionar el servicio de mantenimiento preventivo, correctivo y soporte IT básico que Wexplay presta a empresas, incluyendo clientes del servicio, activos IT, visitas, revisiones, servicios, credenciales e informes.

## Plataforma y contexto
- Odoo 18 Community
- On-premise
- Proyecto Wexplay
- Sin Studio
- Multi-company compatible

## Principios
- Priorizar claridad, simplicidad y mantenibilidad
- No introducir complejidad innecesaria
- No añadir funcionalidades no pedidas
- Mantener código fácil de retocar manualmente después
- Evitar hacks y soluciones frágiles
- Separar bien responsabilidades
- Mantener coherencia con otros módulos Wexplay

## Convenciones de código
- Código en inglés
- Comentarios en español
- Nombres claros y directos
- Evitar helpers genéricos innecesarios
- Evitar abstracciones excesivas
- Mantener cambios pequeños y revisables

## Arquitectura
- Organizar claramente por:
  - models
  - security
  - views
  - reports
  - wizard si hace falta
  - static solo cuando aporte valor real
- Separar claramente:
  - dominio de negocio
  - ORM
  - seguridad
  - configuración
  - reportes
  - frontend OWL solo si realmente aporta valor
- Evitar sobreingeniería
- Usar abstracciones ligeras solo donde aporten valor real

## Reglas funcionales clave
- Solo forman parte del sistema los `res.partner` con `x_is_it_maintenance_customer = True`
- Un activo IT debe tener identidad propia
- La visita es la unidad operativa principal
- El historial de revisiones debe normalizarse en modelo propio
- Los servicios IT deben modelarse aparte de los activos
- Las credenciales no deben tratarse como simples textos visibles
- La generación de códigos internos debe ser automática y mantenible
- El dashboard debe ser útil, no ornamental
- El informe base debe salir de la visita realizada

## MVP
- extensión de contactos
- clientes del servicio
- activos
- revisiones
- visitas
- líneas de visita
- servicios
- credenciales
- checklist por plantilla
- dashboard base
- informe QWeb por visita
- seguridad base
- menús y vistas funcionales

## Seguridad
- Crear grupos específicos del módulo
- Restringir credenciales por grupos
- No mostrar secretos en vistas lista
- Ocultar secretos por defecto en formulario
- Preparar la arquitectura para cifrado futuro
- No asumir que la ocultación visual equivale a seguridad completa

## Dependencias
- Evitar dependencias innecesarias
- Justificar cualquier dependencia no estándar antes de introducirla
- No usar Studio

## UI
- Mantener vistas limpias y operativas
- Evitar frontend complejo salvo necesidad real
- Usar OWL solo si aporta valor claro, por ejemplo dashboard
- Priorizar ergonomía real de trabajo diario

## Reportes
- Usar QWeb
- Diseños claros y profesionales
- Mantener separada la lógica de negocio del render del reporte

## Flujo de trabajo
- Antes de cambios grandes, explicar el plan
- Implementar por fases pequeñas
- Mantener el módulo instalable en cada fase razonable
- Añadir tests para lógica crítica cuando proceda
- No cambiar arquitectura sin explicarlo primero

## Qué evitar
- lógica de negocio importante dispersa en JS
- modelos ambiguos que mezclen varias responsabilidades
- hardcodes innecesarios
- sobreingeniería
- generar toda la v2 dentro de la v1

## UI y estilo visual
- Mantener la base visual nativa de Odoo 18
- No reemplazar completamente la estética de Odoo
- Integrar la identidad visual de los módulos personalizados de Wexplay ya existentes
- Buscar una estética híbrida:
  - Odoo reconocible
  - interfaz más cuidada, jerárquica y profesional
- Usar SCSS propio solo cuando aporte valor real
- Evitar estilos frágiles, hacks visuales o sobrecarga estética
- Mantener consistencia entre formularios, listas, dashboards y bloques funcionales
- Priorizar paneles claros, separación visual limpia y buena legibilidad