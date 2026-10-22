# 0045. Datos de las secciones Specs y Decisiones de arquitectura

Fecha: 2026-10-22 · Estado: aceptada · RAD-57 · completa la ADR 0044

## Contexto

La nueva portada de un space tiene secciones. Specs y Decisiones de arquitectura se muestran como tablas con filtros. Los specs se filtran por proyecto, feature, estado y dueño, y las decisiones por tema, proyecto y estado. La metadata de publicación no tenía feature, tema, estado de una decisión, ni a qué decisión reemplaza.

## Decisión

- **Specs.** Son las páginas publicadas con `doc_type = build-spec`.
  - **Proyecto:** el `docket_project` de la fase 4.4.
  - **Feature:** cada una de sus `docket_areas`. Un proyecto puede tener muchas áreas, y por eso el filtro de feature solo aparece una vez elegido el proyecto.
  - **Estado:** sale de los tickets que el spec creó (fase 4.3), con el acceso de quien lee en Docket.
    - `outdated` si la página venció.
    - `done` si todos sus tickets están terminados.
    - `live` si alguno empezó.
    - Si no, `planned`.
- **Decisiones de arquitectura.** Son las páginas publicadas con `doc_type = decision-log`. Se agregan tres campos opcionales de metadata. No llevan migración, porque la metadata es JSONB.
  - `decision_status`: `accepted`, `proposed` o `replaced`. Si falta, se toma como `accepted`.
  - `decision_topic`: el tema, de hasta 40 caracteres.
  - `decision_replaces`: el id de la decisión que esta reemplaza. La reemplazada se marca `replaced` sola.
- **Número.** El número de una decisión es su orden de primera publicación en el space (0001, 0002…). No se guarda: archivar una decisión vieja recorre los números de las siguientes, y lo aceptamos a cambio de no pedir un número a mano.
- **Rutas.** `GET /spaces/{key}/specs` y `GET /spaces/{key}/decisions` resuelven todo con la visibilidad de quien lee. Los conteos de los filtros solo cuentan páginas que puede abrir.

## Consecuencias

- Un space con más de 500 specs o decisiones solo lista las 500 más antiguas visibles. Si llega a pasar, se mueve el filtro a SQL.
- Las decisiones viejas sin campos nuevos aparecen como aceptadas y sin tema hasta que alguien las edite.
