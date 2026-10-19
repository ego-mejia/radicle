# 0001. Frontend con styled-components y organización por carpetas

- Fecha: 2026-10-18
- Estado: aceptada
- Afecta: documento de control (Stack, UI y Repositorio)

## Contexto

El documento de control fija Tailwind CSS para estilos y `src/{routes,components,api,i18n,theme}` como estructura. Fernando pidió que el frontend se organice como el de vitaegap (sin copiar su estilo visual), con styled-components y componentes de máximo 500 líneas.

## Decisión

- Estilos con **styled-components** y CSS puro. Los tokens de la paleta lima viven en `src/styles/theme.ts` y llegan por `ThemeProvider`. No se usa Tailwind.
- Estructura de `src/`:
  - `components/`: compartidos (`layout/`, `ui/`, uno por carpeta).
  - `features/<dominio>/`: `components/`, `views/`, `hooks/`, `utils/`, `test/`, `api.ts`, `types.ts`.
  - `pages/`, `hooks/`, `contexts/`, `lib/`, `services/api/` (cliente generado de OpenAPI), `styles/`, `i18n/`, `test/`.
- **Una carpeta por componente**: `index.tsx` sin estilos, `style.ts` con los styled-components (`import * as S from './style'`) y sus tests al lado.
- **Máximo 500 líneas por archivo**, verificado por ESLint con `max-lines` (falla el lint).
- Radix UI primitives, dnd-kit y lucide-react siguen igual; se estilizan con styled-components.

## Consecuencias

- `src/theme/` del documento de control pasa a `src/styles/` y `src/api/` pasa a `src/services/api/`.
- El documento de control debe actualizar la fila UI del Stack.
