# 0039. Tiempo real con pycrdt, sin pycrdt-websocket (Folio 2.2)

- Fecha: 2026-10-21
- Estado: aceptada
- Afecta: build spec de Folio fase 2 (entregables 2.2 y 2.5)

El spec pide un room de pycrdt-websocket por nodo. pycrdt-websocket trae su propio servidor ASGI y su propio almacenamiento (`YStore` en archivos o SQLite). Para Folio necesitamos que el room viva dentro de FastAPI y siga las reglas de la app: la misma sesión o token, solo quien puede editar, máximo 50 editores, updates en Postgres (`folio_yupdates`, compactados en `folio_ydocs`), cambios de agentes por REST o MCP aplicados al documento vivo y límite de frecuencia de awareness.

## Decisión

- Usamos **pycrdt** (el CRDT, compatible con Yjs) y su implementación del protocolo de sincronización y awareness (`create_sync_message`, `handle_sync_message`, `create_update_message`, `YMessageType`), pero el room es nuestro: `folio/services/collab.py`.
- El navegador usa `y-websocket` (`WebsocketProvider`) y TipTap Collaboration; hablan el mismo protocolo, así que no hay nada propio en el cliente.
- El documento vive en `XmlFragment("default")` con la misma forma que escribe y-prosemirror: un `XmlElement` por nodo con sus atributos, el texto en `XmlText` con las marcas como atributos de formato. `folio/services/ydoc.py` convierte entre ese fragmento y el JSON de TipTap que valida `schema.py`, en los dos sentidos.
- Los rooms viven en memoria del proceso de la app. La imagen corre un solo proceso de uvicorn; si algún día corre varios, los rooms tendrían que repartirse por nodo (por ejemplo con Postgres `LISTEN/NOTIFY`), y eso pediría otro ADR.

## Por qué

- Auth, permisos y persistencia quedan en los servicios, como el resto de Folio, y se prueban igual (testcontainers).
- Evitamos un segundo almacenamiento y un segundo servidor que habría que sincronizar con Postgres.
