# 0015. Clonar, mover y edición masiva

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 2 (2.7)

- **Clonar:** reutiliza la creación normal de tickets, así respeta la screen de crear y numera igual. Sin `description` el clon conserva solo las líneas del checklist; sin `checklist_state` sus items salen desmarcados. Prioridad, fecha límite y estimación siempre se copian; el milestone se conserva si en el destino existe uno abierto con el mismo nombre; el padre se conserva dentro del mismo proyecto. Los colaboradores solo se copian si pueden ser asignados en el destino. Los adjuntos se copian como archivos nuevos.
- **Mover:** las keys viejas van a `ticket_key_aliases`. `load_ticket` resuelve el alias cuando la key vieja ya no existe, así cualquier endpoint (lectura o escritura) y el MCP funcionan con ella. `GET /tickets/{key}` marca `moved_from`. Los números nunca se reutilizan, por lo que una key vieja no choca con un ticket nuevo.
- Al mover: el assignee se quita si no es member en el destino; el padre se quita si no se mueve con el ticket; el milestone se conserva por nombre o el que se mande; los campos custom sin key igual en el destino se descartan y se nombran en el evento `moved`. Todo se valida antes de mover el primer ticket.
- **Bulk:** cada ticket corre en su propio savepoint dentro de la petición (hasta 100) o del job (más de 100), con la edición normal: screens, reglas de transición y permisos por proyecto. `dry_run` corre todo y deshace cada savepoint, así la vista previa dice exactamente qué fallaría. Un bulk como job responde 202 con el job; el worker hace commit cada 10 tickets para que el progreso se vea.
- El MCP `bulk_update` usa `dry_run=true` por default.
