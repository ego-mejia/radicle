# Plugins (Folio 5.7, ADR 0043)

Un plugin es un manifiesto JSON que el admin de la instancia instala en **Admin → Plugins**. En Folio agrega bloques al editor con el hook `folio.register_blocks`. Cada bloque se dibuja en el mismo sandbox que el bloque Visual: sin red, sin cookies ni storage, y sin acceso a la página.

## Manifiesto

```json
{
  "key": "acme.countdown",
  "name": "Cuenta regresiva",
  "version": "1.0.0",
  "description": "Días que faltan para una fecha.",
  "author": "Acme",
  "hooks": {
    "folio.register_blocks": [
      {
        "type": "countdown",
        "name": "Cuenta regresiva",
        "description": "Cuántos días faltan.",
        "icon": "⏳",
        "fields": [
          {"key": "title", "label": "Título", "kind": "text", "default": "Lanzamiento"},
          {"key": "date", "label": "Fecha", "kind": "date", "required": true}
        ],
        "html": "<div id=\"out\"></div><script>const d = window.radicle.data; …</script>"
      }
    ]
  }
}
```

- `key`: minúsculas con puntos o guiones. `version`: semver.
- **Instalar y actualizar:** instalar una `key` que ya existe actualiza el plugin y conserva si está encendido o apagado.
- **Bloques:** de 1 a 20 por plugin. Su `type` va en minúsculas y no se repite dentro del plugin.
- **Campos:** hasta 20 por bloque. Su `kind` es `text`, `textarea`, `number`, `date` o `select` (este con `options`). Ningún campo se puede llamar `id`.
- **`html`:** pasa las mismas revisiones que un Visual:
  - sin `fetch`, XHR, WebSocket ni recursos externos;
  - sin `parent`, `top` ni `opener`;
  - solo tokens `--rdc-*`;
  - hasta 512 KB.

  Los valores de los campos llegan como `window.radicle.data`.

## En las páginas

- En el editor, `/` muestra los bloques de los plugins encendidos.
- El bloque pide sus campos mientras está seleccionado o mientras le falta uno obligatorio.
- En Markdown se escribe `::plugin{id=acme.countdown/countdown date=2026-12-15 title="V1"}`.
- **Plugin apagado:** su bloque sale del `/`. Las páginas que ya lo usan lo conservan, y quien lee ve un aviso hasta que se vuelva a encender.

## Ejemplo incluido

`radicle.countdown` (`backend/radicle/folio/plugins/countdown.json`) se instala con un clic desde Admin → Plugins → Ejemplos.

## API

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET | `/api/v1/admin/plugins` | Instalados, hooks conocidos y ejemplos |
| POST | `/api/v1/admin/plugins` | `{manifest}`: instalar o actualizar |
| POST | `/api/v1/admin/plugins/examples/{key}` | Instalar un ejemplo |
| PATCH | `/api/v1/admin/plugins/{key}` | `{enabled}` |
| DELETE | `/api/v1/admin/plugins/{key}` | Quitarlo |
| GET | `/api/v1/folio/plugin-blocks` | Los bloques de los plugins encendidos |

Instalar, cambiar y quitar plugins queda en el audit log como `plugin.install`, `plugin.update` y `plugin.delete`.
