# Arquitectura del módulo Wexplay - Product Code Rules

## 1. Propósito

Este módulo genera automáticamente referencias internas de productos (`default_code`) basadas en la categoría del producto y reglas de codificación predefinidas. Utiliza secuencias independientes por categoría para asegurar la unicidad de los códigos.

## 2. Flujos de negocio principales

Los flujos de negocio principales son:

1.  **Creación de reglas de codificación:** Los usuarios crean reglas que asocian una categoría de producto con un prefijo y una secuencia.
2.  **Generación automática de códigos al crear productos:** Cuando se crea un nuevo producto, el módulo asigna automáticamente un código interno basado en la regla correspondiente a su categoría.
3.  **Actualización automática de códigos al modificar productos:** Si se modifica la categoría de un producto o se elimina su código interno, el módulo reasigna automáticamente un nuevo código (si existe una regla para la nueva categoría).
4.  **Duplicación de productos:** Al duplicar un producto, el módulo asegura que el nuevo producto reciba un nuevo código, evitando duplicados.

## 3. Modelos y responsabilidades

*   **`wex.product.code.rule`:** Define las reglas de codificación de productos.  Sus responsabilidades incluyen:
    *   Almacenar la configuración de cada regla (categoría, prefijo, secuencia).
    *   Validar la configuración.
    *   Generar el siguiente código disponible basado en la secuencia asociada.
    *   Buscar la regla que corresponde a una categoría.
    *   Generar códigos para los productos que no tienen código en esa categoría.
*   **`product.template` (Extendido):** El modelo de plantilla de producto se extiende para:
    *   Asignar un código por defecto si está vacío y la categoría tiene una regla asociada.
    *   Reasignar el código por defecto si se cambia la categoría o si el código por defecto se elimina.
    *   Forzar la generación de un nuevo código al duplicar un producto.

## 4. Extensiones sobre el estándar de Odoo 18

*   **Nuevo modelo `wex.product.code.rule`:** Este modelo permite definir reglas para la generación automática de códigos de producto.
*   **Extensión del modelo `product.template`:** Se extiende el modelo de plantilla de producto para implementar la lógica de asignación y reasignación automática de códigos.
*   **Interfaz de usuario para la gestión de reglas:** El módulo proporciona una interfaz de usuario para crear y gestionar las reglas de codificación.

## 5. Decisiones de diseño relevantes

*   **Uso de secuencias independientes por categoría:** Esta decisión permite asegurar la unicidad de los códigos generados, incluso si existen múltiples reglas.
*   **Generación automática de códigos en la creación y modificación de productos:** Esta decisión automatiza el proceso de asignación de códigos, reduciendo la necesidad de intervención manual.
*   **Forzar la generación de un nuevo código al duplicar productos:** Esta decisión evita la creación de productos duplicados con el mismo código.
*   **Restricción SQL para asegurar unicidad de reglas por categoría y compañía:** Evita la creación de reglas conflictivas.
