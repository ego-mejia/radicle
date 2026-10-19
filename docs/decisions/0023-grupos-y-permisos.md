# 0023. Grupos y matriz de permisos

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 4 (4.1)

- `core/permissions.py` tiene el catálogo (20 permisos con su default para member y viewer), el rol efectivo y `authorize()`. `ProjectAccess` vive ahí y trae los permisos efectivos; `services/access.project_access` y los cargadores (`load_ticket`, `load_board`, `load_sprint`, `load_comment`, `attachments.load`) reciben `permission=` y delegan en `authorize`. Ningún router ni tool revisa roles a mano.
- Orden de errores: 404 si no ve el proyecto (o el ticket), 403 `permission_denied` con el permiso faltante en `extra.permission` y un mensaje que dice cómo cambiarlo, 409 si el proyecto está archivado. El MCP muestra ese mismo mensaje.
- Rol efectivo = el más alto entre el directo y los de sus grupos; se calcula en cada request (sin caché), así que salir de un grupo quita el acceso de inmediato. `visible_project_ids` incluye los proyectos por grupo, y con él la búsqueda, boards, reportes y dashboards.
- La matriz guarda solo excepciones: un valor igual al default borra la fila. Admin no se puede editar.
- Los permisos `*_any` (borrar comentarios o archivos de otros, editar tiempo de otros) se deciden por dueño: lo propio pide el permiso base y lo ajeno el `*_any`, que ya no depende del base.
- Mapeo de acciones existentes: mover tarjeta a otra columna pide `ticket.transition` y reordenar `ticket.edit`; meter o sacar tickets de un sprint pide `ticket.edit` (planear) y crear, iniciar o cerrar sprints `sprint.manage`; clonar pide `ticket.create` en el destino; archivar sigue siendo solo de admin.
- Cambio de comportamiento: votar ahora lo pueden hacer los viewers (default del catálogo).
- `GET /me` y `GET /projects/{key}` devuelven los permisos efectivos; la UI decide qué botones mostrar con ellos (`lib/permissions.can`).
