# 0007. Detalles de la UI web

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 1 (UI) y documento de control (Stack)

## Rutas

TanStack Router con rutas definidas en código (`src/router.tsx`), sin el plugin de rutas por archivo: la organización de carpetas sigue la de vitaegap ([0001](0001-frontend-styled-components.md)) y no la que impondría el plugin. Los filtros del board, la query de la lista y el ticket abierto en panel lateral viven en la URL (`?type=bug&t=PA-4`, `?q=...`).

## Board

- Antes de arrastrar se piden las transiciones del ticket; las columnas sin transición válida se atenúan y no aceptan la tarjeta.
- Una transición con resolution única se aplica sola; varias transiciones o varias resolutions abren un selector.
- Done muestra lo resuelto en los últimos 14 días, con link a la lista con todo lo hecho.

## Formularios y accesibilidad

`Field` asocia la etiqueta al control con `htmlFor` en lugar de envolverlo en `<label>`. Envolverlo hacía que el nombre accesible incluyera el valor elegido ("Area —") y, en grupos de botones, que cada botón se llamara como el grupo. Los grupos (tipo de ticket) usan `role="group"` con `aria-labelledby`.

## Checklist

La vista de markdown ubica cada item del checklist por su línea en el texto, con la misma regla que el backend (`src/lib/checklist.ts`), y no por orden de render: React puede renderizar un componente dos veces en modo estricto.

## Pruebas E2E

Playwright corre contra Radicle real levantado con `docker compose` en una base limpia (`frontend/e2e/stage1.spec.ts`), no contra un mock. En CI es el job `e2e`.
