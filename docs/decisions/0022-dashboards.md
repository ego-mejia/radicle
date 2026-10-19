# 0022. Dashboards

- Fecha: 2026-10-19
- Estado: aceptada
- Afecta: build spec etapa 3 (3.7)

- La visibilidad reutiliza el enum de los filtros guardados (`private`, `project`, `instance`) con las mismas reglas: compartir con la instancia es solo para admins de instancia y compartir con un proyecto exige ser miembro.
- Edita el dueño. El "Summary" de cada proyecto (uno por proyecto, garantizado por un índice único parcial) es del usuario de sistema y lo editan los admins del proyecto; no se borra ni cambia de visibilidad. La migración `0016` lo crea para los proyectos existentes y `create_project` para los nuevos, con seis widgets (abiertos, bloqueados, creados vs resueltos, abiertos por área, bloqueados con su bloqueador y mis tickets).
- `GET /widgets/{id}/data` calcula cada widget con los permisos de quien ve: el RQL se compila para ese usuario y los conteos solo incluyen tickets que puede ver. Los bloqueadores que se listan también son solo los visibles.
- La configuración de cada widget se valida al guardar (tipo, claves obligatorias, RQL que parsea, campo de distribución y layout dentro de 12 columnas). El layout se guarda en lote con `PATCH /dashboards/{id}` al soltar un drag o resize.
- UI con react-grid-layout 1.5 (la rama 1.x sigue mantenida y su API es estable); los estilos del placeholder y del handle de resize van con tokens del tema. Los widgets se refrescan cada 5 minutos (`refresh_seconds`) y tienen botón de refrescar; las gráficas reutilizan los componentes de reportes.
