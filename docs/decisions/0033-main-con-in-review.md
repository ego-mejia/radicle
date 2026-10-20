# 0033. El board Main trae una columna In Review

- Fecha: 2026-10-20
- Estado: aceptada
- Afecta: build spec etapa 1 (Kanban básico por categoría) y etapa 3 (boards configurables)

Con tres columnas por categoría (To Do, In Progress, Done), In Review y QA Verified quedaban dentro de In Progress y no había a dónde arrastrar una tarjeta para mandarla a revisión.

- Main nace con To Do | In Progress | In Review | Done. In Review nombra los estados *in progress* que vienen después del primero de cada tipo, y cualquiera que se llame con "review" (In Review de Task y Draft, QA Verified de Bug).
- Los boards nuevos sin columnas propias usan las mismas cuatro.
- La migración `0025` actualiza los boards Main que seguían con las tres columnas originales; los que alguien configuró no se tocan.
- Depende de [0032](0032-columna-por-nombre-gana.md): un estado nombrado en In Review gana sobre la categoría de In Progress.
