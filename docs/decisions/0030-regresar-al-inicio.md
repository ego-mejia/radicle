# 0030. Regresar al primer estado desde revisión y QA

- Fecha: 2026-10-20
- Estado: aceptada
- Afecta: build spec etapa 1 (workflows default)

Con los workflows del spec, un ticket en In Review (o QA Verified) solo podía avanzar o regresar un paso, así que en el board no se podía arrastrar a To Do: la columna aparecía bloqueada y el menú de estado no ofrecía To Do.

- Se agregan tres transiciones al template "Radicle default": **Back to To Do** (Task, In Review → To Do), **Back to Reported** (Bug, QA Verified → Reported) y **Back to New** (Draft, In Review → New).
- La migración `0023` las agrega al template (sube su versión) y a los proyectos ligados que estaban en la versión anterior. Los proyectos independientes no se tocan: sus admins las pueden agregar en el editor de workflows.
- `DEFAULT_WORKFLOWS` en código queda igual que el template, y un test lo verifica.
