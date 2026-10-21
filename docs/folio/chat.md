# Chat de los docs (Folio 4.5)

El chat responde preguntas solo con lo que dicen los docs que puede ver quien pregunta, y cita cada afirmación con `[n]` a la sección exacta.

## Cómo responde

1. **Recuperación** (`folio/services/retrieval.py`):
   - Usa la búsqueda híbrida de la fase 1, pero sobre secciones en lugar de páginas.
   - Aplica la visibilidad del lector en el SQL, igual que la búsqueda.
   - Fusiona el texto completo y los embeddings con RRF.
   - Re-rankea: Verified ×1.15 y Outdated ×0.85; sube la sección cuyo encabezado nombra las palabras de la pregunta; ninguna página ocupa más de 3 lugares.
   - Pasa al modelo las 8 mejores.
   - Un space con la IA apagada no manda sus páginas al modelo.
2. **Sin pasajes:** no se llama al modelo. La respuesta dice que los docs no lo cubren y a quién preguntar, en este orden:
   - el dueño de la página más cercana;
   - si no hay, los admins del space;
   - si no hay, un admin de Folio.
3. **Con pasajes:** el prompt de sistema obliga a:
   - usar solo los pasajes numerados;
   - citar cada afirmación;
   - decir cuando no está en los docs, sugiriendo a quién preguntar;
   - avisar si usa un doc marcado OUTDATED.
4. **Respuesta:** llega por SSE (`delta`, `done`, `error`). Las citas guardan nodo, versión, ancla y si el doc está Outdated.
5. **Uso:** `ai_calls` guarda tokens y latencia, sin contenido. La pregunta y la respuesta quedan solo en las sesiones de quien pregunta.

## API y MCP

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET | `/folio/chat/availability` | Si el chat está prendido y, si no, por qué |
| GET, POST | `/folio/chat/sessions` | Tus sesiones |
| GET | `/folio/chat/sessions/{id}` | Una sesión con sus mensajes |
| POST | `/folio/chat/sessions/{id}/messages` | Pregunta; respuesta en SSE; filtros `space`, `doc_type`, `audience` |
| POST | `/folio/chat/messages/{id}/feedback` | Pulgar arriba o abajo, con nota |
| GET | `/folio/admin/chat/unanswered` | Admins de Folio: preguntas sin cita o con pulgar abajo |

La tool del MCP `ask_docs` hace lo mismo y devuelve la respuesta con sus citas.

El chat se apaga en dos casos:

- No hay proveedor con modelo de chat.
- `features.folio_chat` es `false` en Admin, Proveedor de IA.

## Evaluación

`tests/eval/test_rag_eval.py` hace 50 preguntas sobre los docs de prueba de `tests/eval/rag_corpus.py`. Cada pregunta tiene la página y la sección que la responden.

| Métrica | Qué mide | Umbral | Medido (oct 2026) |
| --- | --- | --- | --- |
| recall@8 | La sección correcta está entre los 8 pasajes del modelo | 0.95 | 1.00 |
| Precisión de citas | La primera cita apunta a la sección correcta | 0.80 | 0.84 |

- **Modelo simulado:** la precisión de citas usa un modelo que cita el pasaje con más palabras en común con la pregunta. Mide el orden, la numeración y el mapeo de citas, no el juicio de un modelo real.
- **Solo texto:** CI no tiene proveedor de embeddings, así que la evaluación corre con búsqueda de texto. La búsqueda híbrida solo puede subir los números.
- **Si un cambio baja una métrica:** el test falla y lista las preguntas que no encontraron su sección.
