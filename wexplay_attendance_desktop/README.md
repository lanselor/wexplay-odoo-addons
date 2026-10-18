# Wexplay Attendance Desktop

Tarjeta de fichaje para el escritorio de aplicaciones Wexplay en Odoo 18 Community.
Muestra estado, fecha/hora de entrada y horas registradas hoy, con una acción
grande para registrar entrada o salida y confirmación del resultado.

## Instalación

1. Actualizar la lista de aplicaciones en el servidor de pruebas.
2. Instalar **Wexplay Attendance Desktop** (`wexplay_attendance_desktop`).
3. Recargar el navegador. El usuario necesita empleado vinculado y la opción
   nativa de fichaje desde la barra superior habilitada en su empresa.

No requiere actualizar ni modificar `web_responsive_app_customizer`. Instala como
dependencias ese personalizador y Asistencias. No crea modelos ni permisos nuevos.
Desinstalar esta integración recupera el comportamiento nativo de la barra.

## Uso

La tarjeta aparece al abrir el escritorio. Se actualiza al abrirlo, al volver a
la ventana y cada minuto mientras permanece visible. Las horas proceden de Odoo;
no son un cronómetro local. También sincroniza el control superior.

Si falla la conexión, actualizar el estado antes de repetir el fichaje: una
respuesta perdida no permite asegurar que el servidor no lo haya guardado.

En pantallas anchas se sitúa abajo a la derecha; en pantallas estrechas o bajas
aparece después de las aplicaciones y antes de las notas de actualización.
Durante la personalización del escritorio se oculta.

## Validación

Pruebas del servicio, sin escrituras en base de datos:

```text
node wexplay_attendance_desktop/tests/attendance_service.test.mjs
```

Ver `ARCHITECTURE.md` para alcance, decisiones y comprobaciones de instalación.

## Estado

Versión 18.0.1.0.0 aceptada por el usuario el 2026-10-18 tras confirmar su
funcionamiento. Cierre funcional completado. La confirmación no especifica
un despliegue en producción.
