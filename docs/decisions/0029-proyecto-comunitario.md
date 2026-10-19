# 0029. Proyecto comunitario: AGPL-3.0, README en inglés y PRs chicos

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: documento de control (Repositorio y convenciones, Supuestos a confirmar)

## Licencia

Se confirma **AGPL-3.0-only**. El objetivo es que nadie pueda montar Radicle en su nube, modificarlo para su empresa y no compartir los cambios: la sección 13 de la AGPL obliga a ofrecer el código fuente a quien use la versión modificada por red, y eso incluye a los empleados de una empresa que lo hospeda para sí. No impide el uso comercial ni el uso interno sin cambios.

Revisión de compatibilidad de las dependencias de producción (2026-10-19):

- Backend (73 paquetes): MIT, BSD, Apache-2.0, ISC, PSF, MPL-2.0 y Unlicense, todas compatibles con AGPLv3. psycopg es LGPL-3.0, también compatible.
- Frontend (341 paquetes): MIT, ISC, BSD, Apache-2.0, 0BSD, Unlicense y MPL-2.0/Apache-2.0. Las fuentes Inter y JetBrains Mono son OFL-1.1, que permite empaquetarlas con software de cualquier licencia. `khroma` no declara licencia en su `package.json`, pero su repositorio es MIT.
- Keycloak (Apache-2.0) solo se usa en tests.

Todo el código es del autor del proyecto, así que puede licenciarlo así. Las contribuciones entran con la misma licencia (inbound = outbound), como dice `CONTRIBUTING.md`.

## Idioma de la documentación

El `README.md` y `CONTRIBUTING.md` van en **inglés**, porque son la puerta de entrada para la comunidad. Hay una traducción en `README.es.md`. Los documentos internos (`docs/`: documento de control, build specs, ADRs y progreso) siguen en español.

## Ramas y tamaño de los PRs

- Ramas `tipo/descripcion-corta` con tipos `feat` (algo nuevo), `minor` (cambios menores), `fix` (bugs), `refactor` (reordenar sin cambiar la funcionalidad) y `docs` (solo documentación). Reemplaza el formato `feat/1.x-nombre` de las etapas.
- Cada PR hace una sola cosa, trae sus tests y cambia menos de 500 líneas en menos de 100 archivos, sin contar archivos generados (lockfiles, `openapi.json`, `schema.d.ts`, `tsconfig.tsbuildinfo`) ni imágenes de `docs/images/`.
- `scripts/pr-size.sh` lo revisa en CI (workflow `PR size`), junto con el nombre de la rama.
- Los commits siguen Conventional Commits y los PRs se integran con squash merge.
