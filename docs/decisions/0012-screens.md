# 0012. Screens

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 2 (2.4)

- Campos que acepta una screen: `title`, `description_md`, `priority`, `area`, `milestone`, `assignee`, `collaborators`, `parent`, `due_date`, `estimate_hours`, `tags` y `cf.<key>`. La resolution y el comentario de una transición no son campos de screen; se piden aparte.
- Create: si hay screen, sus obligatorios mandan y el área deja de ser obligatoria por default (salvo que la screen la pida). Campos que no están en la screen se aceptan igual, porque al crear no hay nada que proteger.
- Edit: los campos fuera de la screen son de solo lectura para members; los admins del proyecto pueden editar cualquiera. Los obligatorios no se pueden vaciar. Quitar el área de un Task o Bug sigue prohibido con o sin screen.
- Transition: la petición puede traer `fields` con valores de la screen (`{"cf.environment": "prod"}`). Se guardan antes de los validators, como parte del mismo movimiento; un campo que no está en la screen da 422. Después todos los obligatorios deben tener valor en el ticket (si ya lo tenía, no hace falta mandarlo).
- `GET /projects/{key}/schema` sin screen regresa los defaults: en create todos los campos fijos más los custom que aplican al tipo, con título obligatorio y área obligatoria salvo en Drafts; en edit lo mismo sin obligatorios salvo el título; en una transición, ninguno.
- Los campos custom restringidos a ciertas áreas traen `areas` en el esquema para que el formulario los muestre solo con esas áreas.
- El mensaje de error es el mismo en UI, API y MCP porque sale del servicio: "A bug in PA needs: Environment (cf.environment). Fill them in and try again."
- `GET /tickets/{key}/transitions` agrega `has_screen` para que la UI sepa cuándo pedir campos.
