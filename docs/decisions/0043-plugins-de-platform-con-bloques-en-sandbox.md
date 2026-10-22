# 0043. Plugins de platform con bloques del editor en sandbox

Fecha: 2026-10-21 · Estado: aceptada · Folio fase 5 (5.7)

## Contexto

La fase 5 pide un sistema de plugins en `platform` que Docket reuse en su etapa 5. En Folio el hook principal es `register_blocks`, que agrega bloques del editor "renderizados en sandbox como el Visual". El plugin de ejemplo agrega un bloque que se ve en un post. Si se desactiva un plugin, su bloque desaparece del editor. Fuera de alcance queda un marketplace público.

Radicle es self-hosted, y el admin instala lo que quiere. Aun así, un plugin no debería poder leer la página, las cookies ni la API con los permisos de quien lee. Tampoco debería correr código dentro del servidor.

## Decisión

**Formato.** Un plugin es un manifiesto JSON. No hay paquete ni código de servidor.

```json
{
  "key": "radicle.countdown",
  "name": "Cuenta regresiva",
  "version": "1.0.0",
  "description": "Días que faltan para una fecha.",
  "author": "Radicle",
  "hooks": {
    "folio.register_blocks": [
      {
        "type": "countdown",
        "name": "Cuenta regresiva",
        "description": "Cuántos días faltan para un lanzamiento.",
        "icon": "⏳",
        "fields": [
          {"key": "title", "label": "Título", "kind": "text"},
          {"key": "date", "label": "Fecha", "kind": "date", "required": true}
        ],
        "html": "<div id=\"out\"></div><script>…</script>"
      }
    ]
  }
}
```

- `key` es único en la instancia. `version` es semver.
- Cada entrada de `hooks` lleva el nombre de un hook que alguna app registró. Platform guarda el plugin y le pasa a cada app su parte para validarla (`plugins.hook("folio.register_blocks", validate)`). Un hook que nadie registró es un error.

**Bloques de Folio.**
- El bloque en el documento es `pluginBlock`, con `plugin`, `block` y `data`. `data` trae los valores de los campos, cada uno de hasta 2,000 caracteres.
- En Markdown se escribe `::plugin{id=radicle.countdown/countdown date=2026-12-15 title="Lanzamiento"}`.
- Se dibuja con el mismo `VisualFrame` del bloque Visual:
  - `sandbox="allow-scripts"` sin `allow-same-origin`;
  - la CSP sin red;
  - los tokens `--rdc-*` y el tema por `postMessage`;
  - alto hasta 2,000 px.
- Los valores llegan al HTML como `window.radicle.data`, en un `<script>` que Folio antepone con el JSON escapado.

**Modelo de confianza.**
- Solo el admin de la instancia instala, activa, desactiva y borra plugins.
- El código del plugin nunca corre en el servidor ni en la página de Radicle, solo dentro del iframe. Desde ahí no hay red, ni cookies, ni storage, ni acceso al documento que lo contiene, igual que un Visual (Folio 3.3).
- Un plugin no tiene permisos propios ni token.
- El HTML se limita a 512 KB por bloque, como un Visual.

**Activar y desactivar.**
- Un plugin desactivado no aparece en el `/` del editor, y sus bloques no se ofrecen.
- Los bloques que ya están en páginas se quedan en el documento. Al leer se muestra un aviso de que el bloque depende de un plugin apagado.
- Si se vuelve a activar, el bloque reaparece tal cual.

**Tabla `plugins`** (platform): `key` único, `name`, `version`, `description`, `author`, `manifest` jsonb, `enabled`, `installed_by`, `installed_at`, `updated_at`. Reinstalar la misma `key` reemplaza el manifiesto, para actualizarlo.

**Plugin de ejemplo.**
- Radicle trae `radicle.countdown` en el repo. El admin lo instala con un clic desde Admin → Plugins.
- Su bloque cuenta los días que faltan para una fecha, con una animación que respeta `prefers-reduced-motion`.

## Desviaciones del spec

- El spec habla de "plugins de platform" sin formato. Aquí un plugin es solo un manifiesto con HTML para el sandbox, sin código de servidor. Un plugin que necesite el servidor queda para cuando haya un caso real.
- Admin → Plugins vive en la pantalla de admin de platform. La de integraciones (ADR 0042) es otra pestaña de la misma pantalla.

## Consecuencias

Docket puede registrar sus propios hooks, como bloques de tablero o campos, sin tocar platform. Un plugin malicioso solo puede dibujar dentro de su iframe. Lo peor que hace es mostrar algo engañoso, y eso queda bajo la responsabilidad del admin que lo instaló.
