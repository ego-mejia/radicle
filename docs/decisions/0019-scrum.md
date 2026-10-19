# 0019. Scrum: sprints, compromiso y reporte

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 3 (3.3)

- `sprint_tickets` guarda cada estancia de un ticket en un sprint: sacarlo pone `removed_at`, volver a meterlo es otra fila. Así el reporte sabe qué se sacó y qué se agregó después de iniciar (`added_after_start`).
- "Un ticket en a lo más un sprint no cerrado" lo garantiza la base de datos con un índice único parcial. Como un índice no puede mirar otra tabla, `sprint_tickets.sprint_closed` copia el estado cerrado del sprint; se marca al cerrar. Meter un ticket a otro sprint abierto lo saca del anterior (con evento `sprint_removed`).
- Al cerrar, los terminados se quedan en el sprint cerrado (RQL `sprint = "Sprint 4"` los encuentra) y los no terminados salen con `removed_at` igual al cierre; van al siguiente sprint future elegido o regresan al backlog con `#backlog` (por default).
- El sprint report se calcula en vivo mientras el sprint está activo y se guarda en `sprints.report` al cerrar, para que no cambie después. La meta cumplida (`goal_met`) se marca a mano y también actualiza el reporte guardado. La API quita del reporte los tickets que quien lo ve no puede ver.
- Un board Scrum muestra solo los tickets del sprint activo, incluidos los terminados (sin la ventana de días de Done). Sin sprint activo, el board avisa y lleva al backlog.
- RQL: `sprint = active` y `sprint = future` (sin comillas) son estados; cualquier otro valor es un nombre de sprint. `sprint IS EMPTY` es "en ningún sprint abierto". `start` es la fecha de inicio del ticket (`start_date`), que ahora se edita como `due_date` y viaja con ella en las screens.
- El snapshot diario guarda el sprint en que estaba cada ticket al final del día.
