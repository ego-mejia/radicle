"""The test docs and the 50 questions the RAG evaluation asks of them (Folio 4.5).

Each question names the page and section that answer it. The questions are written the way
people ask, not copied from the text, so retrieval has to bridge the wording.
"""

DOCS: dict[str, str] = {
    "Conecta un agente": """Cómo dar acceso a un agente de IA.

# Crea el agente

Un admin crea el agente en Admin, Agentes, con su handle y su rol.

# Conecta por MCP

Copia el token del agente y configúralo en tu cliente MCP con el encabezado Authorization Bearer.

# Permisos del agente

Limita las tools del agente por grupo: lectura de docs, escritura, tickets.
""",
    "Despliegue con Docker": """Cómo instalar Radicle en un servidor propio.

# Requisitos

Necesitas Docker Compose y un servidor con 2 GB de memoria.

# Variables de entorno

Define RADICLE_SECRET_KEY con 32 caracteres y RADICLE_BASE_URL con la dirección pública.

# Actualizar la versión

Para actualizar, haz git pull y vuelve a levantar los contenedores con docker compose up.

# Respaldos

Respalda la base de datos Postgres cada noche con pg_dump.
""",
    "Política de vacaciones": """Días libres del equipo.

# Días por año

Cada persona tiene 20 días hábiles de vacaciones por año, más los feriados oficiales.

# Cómo pedirlas

Pide tus vacaciones con dos semanas de anticipación a tu líder en el calendario del equipo.

# Días no usados

Hasta 5 días no usados pasan al año siguiente; el resto se pierde en marzo.
""",
    "Guía de estilo de código": """Cómo escribimos código.

# Nombres

Variables y funciones en inglés, con nombres que digan qué hacen, sin abreviaturas.

# Pruebas

Cada endpoint lleva una prueba feliz, una de error y una de permisos contra Postgres real.

# Revisiones

Un pull request hace una sola cosa y tiene menos de 500 líneas.
""",
    "Onboarding de ingeniería": """La primera semana de una persona nueva en ingeniería.

# Primer día

Recibes tu laptop, tus accesos a GitHub y una sesión con tu buddy.

# Ambiente local

Clona el repositorio y corre el script de setup; levanta Postgres con docker.

# Primer ticket

Tu primer ticket es un bug pequeño etiquetado good-first-issue.
""",
    "Gastos y reembolsos": """Cómo pedir que la empresa te devuelva un gasto.

# Qué se reembolsa

Se reembolsan viajes de trabajo, comidas con clientes y cursos aprobados.

# Cómo pedir un reembolso

Sube la factura al sistema de gastos dentro de los 30 días siguientes a la compra.

# Tarjeta corporativa

La tarjeta corporativa es solo para gastos del equipo; los gastos personales están prohibidos.
""",
    "Seguridad de cuentas": """Cómo proteger tu cuenta.

# Contraseñas

Usa un gestor de contraseñas y una contraseña distinta por servicio, de al menos 14 caracteres.

# Doble factor

Activa la autenticación de dos factores con una app, no con SMS.

# Reportar un incidente

Si sospechas de un acceso indebido, avisa en el canal de seguridad en menos de una hora.
""",
    "Búsqueda en Folio": """Cómo encontrar documentos.

# Búsqueda por palabras

Escribe palabras o una pregunta en la barra; los resultados llevan a la sección exacta.

# Consultas RQL

Filtra con RQL, por ejemplo space = docs AND doc_type = how-to.

# Búsqueda semántica

Con un proveedor de embeddings la búsqueda entiende el significado, no solo las palabras.
""",
    "Publicar una página": """Cómo publicar en Folio.

# Metadata obligatoria

Antes de publicar llena la descripción, el tipo de documento y el dueño.

# Versiones

Cada publicación crea una versión inmutable que puedes comparar y restaurar.

# Aprobación de agentes

Lo que escribe un agente espera la aprobación de un admin antes de publicarse.
""",
    "Reuniones del equipo": """Cómo y cuándo nos reunimos.

# Daily

La daily es a las 9:30, dura 15 minutos y cada quien dice en qué está y qué lo bloquea.

# Retrospectiva

Cada dos semanas hacemos una retrospectiva para revisar qué salió bien y qué mejorar.

# Minutas

Las minutas se escriben en Folio con el template de meeting notes el mismo día.
""",
    "Guardias e incidentes": """La rotación de guardia y cómo responder a una caída.

# Rotación

La guardia rota cada semana entre las personas de backend; el calendario está en PagerDuty.

# Severidades

Una caída total es severidad uno; se atiende en menos de 15 minutos a cualquier hora.

# Postmortem

Después de cada incidente de severidad uno se escribe un postmortem sin culpables en 5 días.
""",
    "Tickets en Docket": """Cómo trabajar con tickets.

# Crear un ticket

Crea un ticket con un título claro, el proyecto y el tipo: tarea, bug o idea.

# Estados

Un ticket pasa por To Do, In Progress, In Review y Done.

# Milestones

Agrupa los tickets de una entrega en un milestone con fecha.
""",
}

# (question, page, section): the section that answers it.
QUESTIONS: list[tuple[str, str, str]] = [
    ("¿Quién crea un agente nuevo?", "Conecta un agente", "Crea el agente"),
    ("¿Dónde pongo el token del agente en mi cliente MCP?", "Conecta un agente", "Conecta por MCP"),
    (
        "¿Cómo limito las tools que puede usar un agente?",
        "Conecta un agente",
        "Permisos del agente",
    ),
    ("¿Qué necesito para instalar Radicle con Docker?", "Despliegue con Docker", "Requisitos"),
    ("¿Cuánta memoria necesita el servidor?", "Despliegue con Docker", "Requisitos"),
    ("¿Qué variables de entorno hay que definir?", "Despliegue con Docker", "Variables de entorno"),
    (
        "¿Cuántos caracteres lleva RADICLE_SECRET_KEY?",
        "Despliegue con Docker",
        "Variables de entorno",
    ),
    (
        "¿Cómo actualizo Radicle a la versión nueva?",
        "Despliegue con Docker",
        "Actualizar la versión",
    ),
    ("¿Cada cuánto respaldamos la base de datos?", "Despliegue con Docker", "Respaldos"),
    ("¿Cuántos días de vacaciones tengo por año?", "Política de vacaciones", "Días por año"),
    ("¿Con cuánta anticipación pido vacaciones?", "Política de vacaciones", "Cómo pedirlas"),
    ("¿A quién le pido mis vacaciones?", "Política de vacaciones", "Cómo pedirlas"),
    (
        "¿Qué pasa con los días de vacaciones que no usé?",
        "Política de vacaciones",
        "Días no usados",
    ),
    ("¿En qué idioma nombramos variables y funciones?", "Guía de estilo de código", "Nombres"),
    ("¿Qué pruebas lleva cada endpoint?", "Guía de estilo de código", "Pruebas"),
    ("¿Las pruebas corren contra Postgres real?", "Guía de estilo de código", "Pruebas"),
    ("¿Qué tamaño máximo tiene un pull request?", "Guía de estilo de código", "Revisiones"),
    ("¿Qué recibo el primer día?", "Onboarding de ingeniería", "Primer día"),
    ("¿Quién es mi buddy y cuándo lo conozco?", "Onboarding de ingeniería", "Primer día"),
    ("¿Cómo levanto el ambiente local?", "Onboarding de ingeniería", "Ambiente local"),
    ("¿Cuál es mi primer ticket como persona nueva?", "Onboarding de ingeniería", "Primer ticket"),
    ("¿Qué gastos se reembolsan?", "Gastos y reembolsos", "Qué se reembolsa"),
    ("¿Me reembolsan un curso?", "Gastos y reembolsos", "Qué se reembolsa"),
    (
        "¿Cuántos días tengo para subir una factura?",
        "Gastos y reembolsos",
        "Cómo pedir un reembolso",
    ),
    (
        "¿Puedo usar la tarjeta corporativa para gastos personales?",
        "Gastos y reembolsos",
        "Tarjeta corporativa",
    ),
    ("¿Qué largo mínimo debe tener mi contraseña?", "Seguridad de cuentas", "Contraseñas"),
    ("¿Uso un gestor de contraseñas?", "Seguridad de cuentas", "Contraseñas"),
    ("¿Cómo activo la autenticación de dos factores?", "Seguridad de cuentas", "Doble factor"),
    ("¿Sirve el SMS como segundo factor?", "Seguridad de cuentas", "Doble factor"),
    (
        "¿Dónde reporto un acceso indebido a mi cuenta?",
        "Seguridad de cuentas",
        "Reportar un incidente",
    ),
    ("¿Cómo busco documentos por palabras?", "Búsqueda en Folio", "Búsqueda por palabras"),
    ("¿Cómo filtro documentos con RQL?", "Búsqueda en Folio", "Consultas RQL"),
    ("¿Qué hace la búsqueda semántica?", "Búsqueda en Folio", "Búsqueda semántica"),
    ("¿Qué metadata es obligatoria para publicar?", "Publicar una página", "Metadata obligatoria"),
    ("¿Puedo restaurar una versión anterior de una página?", "Publicar una página", "Versiones"),
    ("¿Quién aprueba lo que escribe un agente?", "Publicar una página", "Aprobación de agentes"),
    ("¿A qué hora es la daily?", "Reuniones del equipo", "Daily"),
    ("¿Cuánto dura la daily?", "Reuniones del equipo", "Daily"),
    ("¿Cada cuánto hacemos retrospectiva?", "Reuniones del equipo", "Retrospectiva"),
    ("¿Dónde escribo las minutas de una reunión?", "Reuniones del equipo", "Minutas"),
    ("¿Cada cuánto rota la guardia?", "Guardias e incidentes", "Rotación"),
    ("¿Dónde está el calendario de guardias?", "Guardias e incidentes", "Rotación"),
    ("¿Qué severidad tiene una caída total?", "Guardias e incidentes", "Severidades"),
    (
        "¿En cuánto tiempo se atiende un incidente de severidad uno?",
        "Guardias e incidentes",
        "Severidades",
    ),
    ("¿Cuándo escribimos un postmortem?", "Guardias e incidentes", "Postmortem"),
    ("¿Cómo creo un ticket en Docket?", "Tickets en Docket", "Crear un ticket"),
    ("¿Qué tipos de ticket hay?", "Tickets en Docket", "Crear un ticket"),
    ("¿Por qué estados pasa un ticket?", "Tickets en Docket", "Estados"),
    ("¿Cómo agrupo los tickets de una entrega?", "Tickets en Docket", "Milestones"),
    ("¿Los milestones tienen fecha?", "Tickets en Docket", "Milestones"),
]
