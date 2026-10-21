# 0041. Vista previa de la home con los permisos del admin (Folio 3.2)

- Fecha: 2026-10-21
- Estado: aceptada
- Afecta: build spec de Folio fase 3 (entregable 3.2)

El spec pide que el borrador del layout tenga una vista previa "como lo ve un reader". Folio no tiene un reader genérico: lo que alguien ve depende de sus grants en cada espacio, de sus grupos, de las restricciones de cada página y de su propio espacio personal.

## Decisión

- `POST /api/v1/folio/admin/home/preview` recibe un layout, lo valida igual que el borrador (422 con el bloque y la posición del error de RQL) y lo resuelve con `home_blocks.resolve`, el mismo código de `GET /home`, con los permisos de quien lo pide. No guarda nada.
- La vista previa se ve con el render de la home de los readers (grid de 12 columnas, sin controles del editor) y deja fuera los bloques vacíos y el chat, como la home real.
- El panel avisa que cada reader ve solo lo que puede: un bloque fijado a una página restringida desaparece para quien no la ve.

## Por qué

- Simular a otro usuario obliga a cruzar sus permisos con los del admin para no mostrar su espacio personal ni su "Para ti", que son solo suyos. Es una regla nueva de acceso para una vista previa.
- Lo que el admin necesita revisar antes de publicar es el armado: qué bloques hay, dónde y con qué contenido. Que cada lector vea solo lo suyo ya lo cubren los tests de `GET /home`, bloque por bloque.

## Consecuencias

- Si hace falta "ver como" un usuario concreto, se agrega después como parámetro, con la intersección de permisos y sus tests de fuga.
