# 0046. Editar visuales y organizar spaces desde el MCP de Folio

Fecha: 2026-11-01 · Estado: aceptada · Folio, después de la navegación nueva

## Contexto

Un agente ya podía agregar un Visual a un borrador (`insert_visual`, Folio 3.3), pero no cambiarlo. Para arreglar un SVG tenía que reescribir todo el borrador en Markdown con `update_draft`, con el riesgo de romper el resto de la página. Tampoco podía crear un space ni una carpeta: solo páginas. El caso real: documentar los cursos de una maestría con visuales interactivos que se ajustan varias veces, agrupados por space y por materia. El spec de la fase 3 solo pide insertar y validar visuales.

## Decisión

**Visuales por índice.** Cada visual del borrador tiene un índice: su orden en el documento, desde 0, contando también los que están dentro de otros bloques (una cita, una columna).

- REST `GET /folio/nodes/{id}/visuals` (sin el código) y `GET`, `PATCH` (solo los campos enviados) y `DELETE` en `/visuals/{index}`; en el MCP, `list_visuals`, `get_visual`, `update_visual` y `remove_visual`.
- Piden poder editar la página, como `POST /blocks`, porque leen el borrador. Un `PATCH` vuelve a pasar por `require_valid` y un índice fuera de rango da 422 con cuántos visuales hay.

**Organizar.** `create_space` (llama a `POST /folio/spaces`, pide el rol creator) y `create_folder` (llama a `POST /folio/nodes` con `kind=folder`). Son los mismos endpoints de la web, así que siguen sus permisos.

**Visuales interactivos.** La guía `folio://guide/visuals` suma una sección y un segundo starter en HTML con botones y un deslizador que redibujan un SVG. No cambia el sandbox: los scripts ya corrían dentro del iframe.

## Consecuencias

Un agente edita un visual sin tocar el resto del borrador. El índice cambia si alguien agrega o quita visuales antes, así que el agente debe llamar `list_visuals` justo antes de editar. Un id estable por visual queda para cuando haga falta.
