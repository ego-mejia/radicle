# 0004. El admin de instancia actúa como admin en todos los proyectos

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 1 (Permisos, `GET /projects`)

## Contexto

La tabla de permisos le da al admin de instancia "sí" en todas las acciones de proyecto, pero también dice que un no miembro recibe 404. No aclara qué pasa con un admin de instancia que no es miembro, y la pantalla de Admin necesita listar y archivar todos los proyectos.

## Decisión

- El admin de instancia tiene rol efectivo `admin` en todos los proyectos, sea miembro o no.
- `GET /projects` y `/me` le muestran todos los proyectos con rol `admin`.
- `GET /projects` oculta los archivados salvo con `?include_archived=true`.
- Un viewer o member que intenta algo fuera de su rol recibe 403 con el rol que necesita (ya sabe que el proyecto existe). Un no miembro siempre recibe 404.
- Las áreas y milestones se identifican por nombre sin distinguir mayúsculas; también se acepta su UUID.
- `DELETE /areas/{name}` archiva; `PATCH` con `archived: false` la restaura.
