# 0035. Autorización genérica: asíncrona y sin caché para Docket (Folio 0.2)

- Fecha: 2026-10-20
- Estado: aceptada
- Afecta: build spec de Folio fase 0 (entregable 0.2)

El spec define `authorize(user, app, permission, resource)` y `visible(user, app, model)` en `platform/authz.py`, con un proveedor por app, y pide que los grupos de un usuario se resuelvan una vez por petición con caché de máximo 60 s.

- **Asíncrona y con sesión.** Las firmas reales son `await authorize(db, user, app, permission, resource=None)` y `visible(user, app, model)`. Revisar permisos lee la base (matriz del proyecto, grupos), así que `check` recibe la sesión. `visible` sigue siendo síncrona porque solo arma un filtro SQL.
- **`Decision`** trae `allowed`, `reason` y `status` (403 o 404). `Decision.raise_if_denied()` la convierte en el `ProblemError` correspondiente, con el mismo mensaje accionable de siempre.
- **App desconocida falla cerrado:** `allowed=False`, 404, y el motivo dice qué apps están registradas.
- **Proveedor de Docket.** Envuelve el `authorize` y el `visible_tickets_clause` de siempre sin cambiar su lógica. Las rutas de Docket los siguen llamando directo; el proveedor es la puerta para que otra app (Folio en la fase 4) pregunte por tickets.
- **Caché de grupos solo para quien la pide.** `platform.groups.group_ids(db, user)` cachea los grupos de cada usuario 60 s en el proceso. La usa el proveedor de Folio. Docket no la usa: su filtro resuelve los grupos dentro del mismo SQL, y el criterio de su etapa 4 ("pérdida inmediata al salir del grupo") sigue cumpliéndose. Así se cumple el spec sin debilitar un test de Docket.
