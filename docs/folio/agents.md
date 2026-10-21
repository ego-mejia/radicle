# Agentes que escriben en Folio desde un codebase (Folio 4.7)

Un agente como Claude Code se conecta a `/mcp/folio` con su token y escribe docs a partir del código en el que trabaja. Todo lo que escribe termina en `submit_for_publication`: queda pendiente hasta que un admin de Folio lo aprueba en la cola.

## Conectar

```bash
claude mcp add --transport http radicle-folio https://radicle.example.com/mcp/folio \
  --header "Authorization: Bearer rdc_..."
```

El agente necesita rol `creator` en Folio y permiso `create` en el space donde va a escribir (Admin → Folio → Permisos).

## Prompts

El servidor publica tres prompts del MCP. Cada uno es una receta que el agente sigue con las tools de Folio (y las de Docket en `/mcp` si las tiene).

| Prompt | Argumentos | Qué produce |
| --- | --- | --- |
| `weekly_changes_post` | `space`, `since`, `until` (default `HEAD`), `repo` | Blog post con los cambios de `git log since..until` agrupados por área, un diagrama Mermaid de lo que cambió y los tickets de Docket ligados a su sección |
| `document_module` | `space`, `module` | Página de referencia del módulo: para qué sirve, su API en tabla, un ejemplo, errores y un diagrama de con quién habla |
| `build_spec_from_discussion` | `space`, `title`, `discussion` | Build spec creado desde el template, con solo lo que la conversación decidió y las preguntas abiertas aparte |

En Claude Code se usan como comandos: `/mcp__radicle-folio__weekly_changes_post eng v1.4`.

## Qué hace cada receta

Todas empiezan igual: `whoami`, `search_docs` para no duplicar un doc (si existe, se cambia con `update_draft`) y `get_metadata_schema` para llenar la metadata obligatoria. Todas terminan con `get_page` para revisar el borrador y `submit_for_publication` con una nota de dónde salió el contenido.

- Los tickets se escriben como `:ticket[PA-4]` en el Markdown, así se ven con su estado en vivo, y se ligan a su sección con `link_ticket`.
- Los diagramas se agregan con `insert_diagram` después del encabezado que toca. Para visuales más elaborados ver el recurso `folio://guide/visuals`.

## Límites

- Los prompts solo dan instrucciones; el agente corre `git` en su propia máquina. Radicle nunca lee el repositorio.
- Las tools que un admin le apague al agente (Admin → Usuarios → Permisos del MCP) siguen apagadas aunque el prompt las nombre.
- Un test revisa que cada tool que nombran los prompts exista (`tests/mcp/test_folio_mcp_prompts.py`).
