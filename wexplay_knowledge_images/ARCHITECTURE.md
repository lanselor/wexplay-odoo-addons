# Wexplay Knowledge Images - Architecture

## Objetivo

`wexplay_knowledge_images` añade soporte opcional de imagenes embebidas
para `wex.knowledge.article`, usando OCA DMS como almacenamiento real.

## Responsabilidades

- guardar el binario real en `dms.file`
- vincular cada imagen a un articulo mediante un modelo funcional propio
- generar una URL interna estable para incrustacion en `body_html`
- heredar permisos de lectura desde el articulo
- exponer ajustes DMS propios del dominio knowledge

## Que no hace

- no convierte `wex_knowledge` en dependiente de DMS
- no reescribe el editor HTML estandar
- no usa portal como capa de acceso en esta fase
- no soporta aun archivos descargables genericos

## Estructura DMS

La estructura objetivo es:

- `KNOWLEDGE/<ARTICULO>/IMAGES`

La raiz y el storage se configuran por compañia.
