# 0031. Permisos de MCP por agente

- Fecha: 2026-10-20
- Estado: aceptada
- Afecta: build spec etapa 1 (agentes y MCP), etapa 4 (permisos)

Un admin quiere crear un agente (un LLM o un worker) y decidir con checks qué puede hacer por MCP, por ejemplo un agente que solo lee o uno que solo triagea el Buzón.

- `users.mcp_tools` (arreglo de texto, solo agentes): las tools que puede llamar. `NULL` significa todas, que es el default y lo que tenían los agentes existentes.
- El catálogo vive en `radicle/core/mcp_catalog.py`: cada tool con su grupo (contexto, encontrar trabajo, tickets, colaboración, archivos y tiempo, planeación, Buzón) y si solo lee. Un test verifica que coincide con las tools registradas.
- El servidor MCP (`RadicleMCPServer`) esconde las tools no permitidas en `tools/list` y rechaza su llamada con un error que dice cómo prenderla. Es un límite adicional: la matriz de permisos del proyecto y los niveles de seguridad siguen aplicando a lo que sí puede llamar.
- API: `mcp_tools` en `POST /agents` y `PATCH /users/{handle}` (422 `not_an_agent` para personas, 422 `unknown_mcp_tool` para nombres inválidos) y `GET /mcp/tools` con el catálogo, solo para admins de instancia. Los cambios quedan en el audit log como `agent.update` con antes y después.
- UI: en Admin → Users se puede crear una persona o un agente; cada agente tiene una sección "MCP permissions" con checks por tool, agrupados, y atajos para todo o solo lectura.
