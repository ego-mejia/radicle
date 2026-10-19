# 0006. Detalles del servidor MCP

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 1 (MCP)

## SDK

Se usa el SDK oficial `mcp` 2.x, donde `FastMCP` se llama `MCPServer`. El cliente de pruebas es el `Client` del mismo SDK conectado por Streamable HTTP a la app en memoria.

## Transporte

- `/mcp` corre en modo stateless con respuestas JSON: cada petición trae su token y no hay sesiones que limpiar. Funciona igual detrás de varios procesos.
- Antes de que el MCP vea la petición, `/mcp` valida el token llamando a `/api/v1/me` en proceso: sin token, token desconocido o revocado responde 401 con un mensaje claro.
- La protección contra DNS rebinding del SDK queda apagada: solo aplica a credenciales que el navegador manda solo (cookies) y aquí la credencial es un header `Authorization`.

## Tools

- `update_ticket` recibe los cambios en un objeto `changes`. Así se distingue "no enviado" de `null` (que limpia el campo), cosa que no se puede con parámetros sueltos.
- Sin `expected_version`, `update_ticket` lee la versión actual y, si alguien escribió en medio, reintenta una vez: gana el último cambio, como pide el spec.
- El SDK antepone "Error executing tool <nombre>:" al mensaje de error; el resto es el `detail` de la API, con las opciones válidas.
- Hay 19 tools: `add_collaborator` y `remove_collaborator` son dos, como en la tabla del spec.
