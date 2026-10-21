# Folio: whiteboards

Un nodo de tipo `whiteboard` es una escena de Excalidraw (fase 3.5). Sigue los permisos del nodo: quien lo ve la lee, quien lo puede editar dibuja. Nunca se publica ni tiene draft: se lee como está, igual que un live doc o una database.

## Dónde vive la escena

Mientras se dibuja, la escena vive en el Y.Doc del nodo (`folio_ydocs` y `folio_yupdates`, ADR 0039), en un `Y.Map("elements")`: la llave es el id del elemento y el valor el elemento de Excalidraw tal cual. Dos personas que mueven elementos distintos no se pisan; si mueven el mismo, gana la versión más alta del elemento, como en Excalidraw.

`folio_whiteboards` guarda la lectura en JSON de esa escena (sin los elementos borrados) y el texto de sus elementos, para quien solo lee, para los bloques incrustados y para la búsqueda.

## Búsqueda

El texto de los elementos (textos y nombres de frames, uno por línea) entra al índice como el de una página publicada, pero sin versión (`folio_chunks.version_id` queda vacío): se reindexa cuando cambia el texto, no cuando se mueve un elemento. Borrar el texto lo saca del índice.

## En la app

- **Página del whiteboard:** quien puede editar entra a la sala y dibuja con los demás; ve sus avatares y sus punteros con nombre. Quien solo lee ve la escena guardada, refrescada cada 10 s. Arriba: exportar PNG o SVG.
- **Bloque en páginas:** `/` → Whiteboard pide cuál; se guarda cuando ya tiene uno. En Markdown `::whiteboard{id=<uuid>}`. Se ve solo para leer, con link al whiteboard; quien no lo puede ver ve un aviso.
- **Fuera de alcance:** imágenes (la herramienta está apagada y los archivos no se sincronizan) y tools del MCP.
- **Fuentes:** Excalidraw 0.18.1; sus fuentes se copian al build (`/assets/excalidraw/fonts`), así que una instalación sin internet las sirve sola.
