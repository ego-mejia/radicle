# 0009. Detalles de campos custom

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 2 (2.1)

- La key y el tipo de un campo no cambian después de crearlo. Cambiar el tipo obligaría a convertir o borrar valores; para eso se archiva el campo y se crea otro.
- `DELETE /projects/{key}/fields/{field_key}` archiva (los valores se conservan). `PATCH` con `archived: false` lo restaura y los valores vuelven a verse.
- Los valores de `select` se comparan sin importar mayúsculas y se guardan con la forma de la opción. Mandar el mismo valor que ya tiene el ticket no se revalida, así un valor de una opción eliminada sobrevive a otras ediciones.
- Si un ticket cambia de tipo o de área y un campo deja de aplicar, el valor se guarda pero no se muestra. Vuelve a verse si el ticket regresa.
- Los campos `user` aceptan cualquier miembro del proyecto (también viewers), a diferencia del assignee.
- En RQL, `text` y `select` comparan sin importar mayúsculas; `checkbox = false` incluye tickets sin valor. Si la misma key existe en varios proyectos con tipos distintos, manda el campo más antiguo.
- Además de lo que pide el spec, `text` acepta `!=` y `!~`, `number` y `date` aceptan `!=`, y `url` acepta `=` y `!=`.
