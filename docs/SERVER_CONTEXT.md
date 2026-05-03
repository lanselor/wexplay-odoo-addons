# Contexto del servidor Ubuntu Odoo 18

Fecha de validación: 2026-05-03

Este documento recoge el estado comprobado del servidor donde corre Odoo 18 de Wexplay. Sirve como contexto operativo para futuras decisiones sobre filestore, DMS, Docker, almacenamiento y crecimiento de adjuntos.

## Plataforma

- Hostname: `ubuntuodoo`
- Sistema operativo: Ubuntu 24.04.3 LTS
- Virtualización: KVM sobre Proxmox
- Arquitectura: x86-64
- Usuario usado para las comprobaciones: `wexplay`
- Ruta de trabajo observada: `/opt/odoo18/addons/wexplay-odoo-addons`

## Docker

Contenedores activos relevantes:

| Contenedor | Imagen | Estado | Uso |
| --- | --- | --- | --- |
| `odoo18` | `odoo18-odoo` | Activo | Odoo 18 |
| `odoo18-db` | `postgres:15` | Activo | PostgreSQL |

Puerto publicado:

- `0.0.0.0:8069 -> 8069/tcp`

Docker root dir:

- `/var/lib/docker`

El root de Docker está en el disco raíz del sistema, no en el disco de datos de 8 TB.

## Discos y montajes

Disco raíz:

- Dispositivo lógico: `/dev/mapper/ubuntu--vg-ubuntu--lv`
- Tamaño: 97 GB
- Usado en la comprobación: 14 GB
- Libre en la comprobación: 79 GB
- Punto de montaje: `/`

Disco de datos:

- Dispositivo: `/dev/sdb1`
- Tamaño: 7,3 TB
- Sistema de archivos: ext4
- Label: `odoo_data`
- UUID: `c0b0a2f7-6fba-457c-8cb8-7098c38f5466`
- Punto de montaje: `/mnt/odoo_data`
- Libre en la comprobación: 6,9 TB

Entrada persistente en `/etc/fstab`:

```text
UUID=c0b0a2f7-6fba-457c-8cb8-7098c38f5466 /mnt/odoo_data ext4 defaults,nofail 0 2
```

Validación de `fstab`:

- `findmnt --verify --verbose` no mostró errores de parseo.
- Mostró warnings por falta de permisos al detectar algunos tipos de filesystem, pero la entrada de `/mnt/odoo_data` resuelve correctamente a `/dev/sdb1`.

## Configuración de Odoo

Archivo de configuración dentro del contenedor:

- `/etc/odoo/odoo.conf`

Valores relevantes:

```ini
data_dir = /var/lib/odoo
db_host = db
db_user = odoo
list_db = false
proxy_mode = True
```

No se documentan contraseñas ni secretos.

## Montajes del contenedor Odoo

Montaje crítico:

```text
/mnt/odoo_data/odoo18 -> /var/lib/odoo
```

Esto significa que el `data_dir` de Odoo dentro del contenedor apunta físicamente al disco de datos de 7,3 TB.

Rutas relevantes:

| Dentro del contenedor | En Ubuntu Server |
| --- | --- |
| `/var/lib/odoo` | `/mnt/odoo_data/odoo18` |
| `/var/lib/odoo/filestore` | `/mnt/odoo_data/odoo18/filestore` |
| `/var/lib/odoo/filestore/wexplay_prod` | `/mnt/odoo_data/odoo18/filestore/wexplay_prod` |

Permisos observados dentro del contenedor:

```text
/var/lib/odoo                         odoo:odoo
/var/lib/odoo/filestore               odoo:odoo
/var/lib/odoo/filestore/wexplay_prod  odoo:odoo
```

El usuario dentro del contenedor Odoo es:

```text
uid=100(odoo) gid=101(odoo)
```

El usuario Ubuntu `wexplay` no tiene escritura directa en `/mnt/odoo_data/odoo18`, lo cual es esperable. Odoo sí puede escribir desde dentro del contenedor.

## Filestore

Filestore productivo:

```text
/mnt/odoo_data/odoo18/filestore/wexplay_prod
```

Bases detectadas en filestore:

- `postgres`
- `wexplay_prod`

Tamaños observados:

- `/mnt/odoo_data/odoo18`: 360 MB
- `/mnt/odoo_data/odoo18/filestore`: 277 MB
- `/mnt/odoo_data/odoo18/filestore/wexplay_prod`: 267 MB

Espacio visto desde Docker para `/var/lib/odoo`:

- Filesystem: `/dev/sdb1`
- Tamaño: 7,3 TB
- Libre: 6,9 TB

Conclusión: el filestore productivo de Odoo está en el disco de datos de 8 TB.

## PostgreSQL

Contenedor:

- `odoo18-db`

Imagen:

- `postgres:15`

Volumen:

```text
/var/lib/docker/volumes/odoo18_postgres-data/_data -> /var/lib/postgresql/data
```

Esto significa que PostgreSQL vive bajo `/var/lib/docker`, en el disco raíz de 97 GB, no en el disco de datos de 8 TB.

Tamaño lógico observado de la base:

- Base `wexplay_prod`: 186 MB
- Tabla `ir_attachment`: 22 MB

Conclusión: actualmente PostgreSQL es pequeño y tiene margen suficiente en el disco raíz, pero conviene vigilar el crecimiento de `/` y `/var/lib/docker`.

## Adjuntos Odoo

Storage efectivo de adjuntos:

```text
ir_attachment.location = file
```

No hay valor explícito en `ir_config_parameter`, por lo que Odoo usa el valor por defecto `file`.

Resumen observado en `ir_attachment`:

| Métrica | Valor |
| --- | ---: |
| Total adjuntos | 1.843 |
| Adjuntos en filestore | 1.622 |
| Adjuntos en base de datos (`db_datas`) | 0 |
| Peso lógico total | 286 MB |

Conclusión: los adjuntos pesados no están guardándose dentro de PostgreSQL.

## Imágenes de producto

Adjuntos detectados para imágenes de producto:

| Modelo | Campo | Total | En filestore | En base de datos |
| --- | --- | ---: | ---: | ---: |
| `product.template` | `image_1920` | 7 | 7 | 0 |
| `product.template` | `image_1024` | 7 | 7 | 0 |
| `product.template` | `image_512` | 7 | 7 | 0 |
| `product.template` | `image_256` | 7 | 7 | 0 |
| `product.template` | `image_128` | 7 | 7 | 0 |

Conclusión: las imágenes nativas de producto se están almacenando en filestore, no en PostgreSQL.

## DMS

Adjuntos detectados para `dms.file`:

| Campo | Total | En filestore | En base de datos | Peso lógico |
| --- | ---: | ---: | ---: | ---: |
| `content_file` | 109 | 109 | 0 | 32 MB |
| `image_1920` | 102 | 102 | 0 | 64 MB |
| `image_1024` | 102 | 102 | 0 | 22 MB |
| `image_512` | 102 | 102 | 0 | 7 MB |
| `image_256` | 102 | 102 | 0 | 2 MB |
| `image_128` | 102 | 102 | 0 | 640 kB |

Conclusión: DMS también está usando filestore para los binarios, no PostgreSQL.

## Consistencia DB / filestore

Comprobación realizada sobre `wexplay_prod`:

- Referencias `ir_attachment.store_fname` revisadas: 1.622
- Archivos físicos faltantes: 0
- Adjuntos con `db_datas`: 0

La diferencia entre archivos físicos y adjuntos referenciados no se considera error por sí misma. Odoo puede deduplicar archivos físicos por checksum, haciendo que varios adjuntos apunten al mismo contenido físico.

## Valoración

La configuración actual es correcta para separar almacenamiento pesado de PostgreSQL:

- Odoo usa `data_dir = /var/lib/odoo`.
- `/var/lib/odoo` está montado en el disco de datos de 8 TB.
- `ir_attachment.location` efectivo es `file`.
- No hay adjuntos pesados guardados en `db_datas`.
- El filestore productivo está en `/mnt/odoo_data`.
- DMS y las imágenes nativas de producto usan filestore.

El uso de DMS no es necesario para evitar que las imágenes saturen PostgreSQL. Esa parte ya la resuelve Odoo con filestore. DMS aporta valor principalmente como capa de gestión documental humana: carpetas, nombres, navegación, trazabilidad y orden operativo.

## Riesgos y vigilancia

Riesgos principales:

- PostgreSQL vive en el disco raíz de 97 GB.
- Docker root dir también vive en el disco raíz.
- Si la base crece mucho por contabilidad, stock, chatter, logs, índices o módulos, `/` puede convertirse en el punto limitante.
- Backups deben incluir siempre base de datos y filestore. Uno sin el otro no permite una restauración completa.

Comandos de vigilancia recomendados:

```bash
df -h / /var/lib/docker /mnt/odoo_data
du -sh /mnt/odoo_data/odoo18/filestore
docker exec odoo18-db psql -U odoo -d wexplay_prod -c "SELECT pg_size_pretty(pg_database_size('wexplay_prod')) AS database_size;"
docker exec odoo18-db psql -U odoo -d wexplay_prod -c "SELECT COUNT(*) FILTER (WHERE db_datas IS NOT NULL) AS adjuntos_en_db, COUNT(*) FILTER (WHERE store_fname IS NOT NULL) AS adjuntos_en_filestore FROM ir_attachment;"
```

Regla operativa:

- No cambiar `ir_attachment.location` a `db`.
- No mover ni borrar manualmente archivos del filestore.
- Cualquier migración de filestore debe hacerse junto con la base de datos y con Odoo parado.
- Antes de cambios grandes de almacenamiento, validar siempre DB + filestore juntos.
