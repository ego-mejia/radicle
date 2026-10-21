# 0036. El frontend compartido se queda en las carpetas comunes (Folio 0.4)

- Fecha: 2026-10-20
- Estado: aceptada
- Afecta: build spec de Folio fase 0 (entregable 0.4), [0001](0001-frontend-styled-components.md)

El spec de la 0.4 pide un paquete `frontend/src/platform` con el tema, los componentes, la auth, el cliente API y el switch de suite.

- No se crea `src/platform`. Lo compartido ya vive en las carpetas comunes de la estructura acordada en [0001](0001-frontend-styled-components.md): `src/components/{ui,layout,icons}`, `src/styles` (tema), `src/services/api` (cliente generado), `src/hooks`, `src/contexts` y `src/lib`. Moverlo todo a `src/platform` tocaría casi todo el frontend sin cambiar nada para quien lo usa.
- Lo de cada app va en `src/features/<dominio>` y su shell en `src/pages`: Docket en `pages/AppPage`, Folio en `pages/FolioPage` y `features/folio`.
- El switch de suite es `components/layout/SuiteSwitch`. `lib/suite.ts` sabe a qué app pertenece una ruta y recuerda la última página de cada app por usuario; `hooks/useSuiteApps` y `hooks/useSuiteShortcuts` dan las apps visibles y los atajos `g d` / `g f`.
- La regla de dependencias del backend tiene su equivalente aquí: `features/folio` no importa de los `features` de Docket; lo común sube a las carpetas compartidas.
