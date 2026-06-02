# Spec y decisiones de diseño — Prueba Técnica UNILINK

Documento de referencia. El CLAUDE.md tiene el "qué hacer"; este tiene el "por qué".

## 1. Requisitos del enunciado (destilados a acciones)
- **Ingesta:** leer `.txt / .md / .pdf / .json` de `/docs`, limpiar texto, eliminar ruido,
  chunkear. Soportar múltiples documentos, contenido desordenado, caracteres especiales y
  documentos largos.
- **Workflow n8n:** recibe preguntas de usuario por webhook HTTP.
- **Retrieval:** buscar info relevante, usar SOLO contenido relacionado con la consulta,
  generar respuesta contextual. No inventar. Si la info no existe, indicarlo explícitamente.
- **IA:** usar la API de OpenAI. Se evalúa calidad del contexto, manejo de prompts,
  organización del flujo, eficiencia de retrieval, claridad de las respuestas.
- **Python:** chunking, limpieza, embeddings, indexación, búsqueda semántica, normalización.
- **Errores:** preguntas sin respuesta, errores de API, timeouts, inputs vacíos.
- **Deploy:** local. README, `.env.example`, instrucciones claras. Entregar workflows n8n +
  código fuente + documentación. Repo público `Prueba Técnica – Juan Ignacio Cabral`.

## 2. Qué se evalúa de verdad (priorizar)
1. Grounding / no alucinar (+ abstención explícita cuando no hay respuesta).
2. Chunking lógico, no por caracteres.
3. Calidad del contexto enviado al modelo + manejo de prompts.
4. Manejo de errores.

## 3. Decisiones y por qué (para defender)
- **Proveedor LLM configurable (default OpenAI).** El brief exige OpenAI API; se cumple
  con el flag `LLM_PROVIDER=openai` (default). Anthropic Claude Haiku queda disponible
  como alternativa opt-in (`LLM_PROVIDER=anthropic`) — útil en contextos sin cuota de
  OpenAI. Ambas ramas usan el mismo system prompt y producen la misma forma de respuesta
  `{answer, found}`. La inteligencia de retrieval (e5 + Chroma) es independiente del proveedor.
- **Status codes REST diferenciados.** El webhook devuelve 200 / 404 / 400 / 502 / 504 según
  el resultado. Un 200 siempre, independientemente del outcome, es información perdida para
  el consumidor. El 404 en abstención es deliberado: la pregunta fue válida, el recurso
  no existe en la base de conocimiento.
- **Embeddings locales (e5-small) en vez de OpenAI.** Retrieval offline, sin costo y en
  español; OpenAI queda solo para la generación. Muestra criterio ML (elección de modelo,
  multilingüe) y robustece el "levantar local".
- **e5 vs MiniLM.** e5 es un modelo de retrieval **asimétrico** (entrenado con el esquema
  query/passage) — es la herramienta correcta para "pregunta corta → documento que la
  responde". El único riesgo (olvidar el prefijo) se neutraliza encapsulando el embedder.
- **Abstención en FastAPI, no en n8n.** El threshold es una decisión de calibración ML:
  vive en Python, donde se testea. n8n queda como orquestación pura y solo rutea sobre el
  flag `found`.
- **Threshold calibrado, no mágico.** Se mide la separación entre preguntas in-scope y
  out-of-scope sobre el harness y se elige el umbral que mejor las separa. (Las preguntas de
  ejemplo del enunciado son parcialmente out-of-scope a propósito — testean la abstención.)
- **Esquema canónico + dedup.** Los 4 formatos son la misma entidad; hay duplicados reales
  cross-source. Normalizar a un esquema único y deduplicar antes de indexar demuestra
  madurez de data engineering y responde al "contenido desordenado" del enunciado.
- **Clean architecture pragmática.** Se abstrae donde se justifica (embedder, vector store),
  no por dogma. Cada interfaz tiene que poder defenderse.

## 4. Nota técnica: por qué el threshold se calibra
La similitud coseno mide el ángulo entre vectores, no su magnitud. e5 tiende a comprimir los
scores en una banda alta y angosta (anisotropía), así que la separación entre lo relevante y
lo irrelevante puede ser chica. Por eso el umbral no se adivina: se calibra empíricamente
sobre datos propios. El valor absoluto del coseno no significa nada por sí solo; lo que
importa es el ranking relativo y la separación entre grupos.

## 5. Talking points para la presentación
- "El threshold no lo inventé: lo calibré midiendo la separación entre preguntas in-scope y
  out-of-scope sobre el set de evaluación."
- "Las 4 fuentes son la misma entidad disfrazada; las normalicé a un esquema canónico y
  deduplico antes de indexar."
- "Hice imposible olvidar el prefijo de e5 encapsulándolo en `embed_query` / `embed_documents`."
- "La abstención se decide en FastAPI con scores; n8n solo orquesta. La inteligencia del
  retrieval vive en Python, testeable."
- "No metí hybrid ni rerank porque el corpus no lo justifica; los tengo medidos como next step."
- **Demo de cierre (status codes):** mostrar una pregunta out-of-scope (p. ej. "error 502")
  y que el sistema responde con HTTP 404, `found:false`, sin llamar al LLM. Contrastar con
  una pregunta in-scope que retorna HTTP 200 con respuesta grounded.
- "El proveedor LLM es configurable: cumplo con OpenAI por defecto (requisito del brief)
  pero la arquitectura no lo accopla — con una variable de entorno se puede cambiar a Anthropic."

## 6. Next steps (si preguntan "¿cómo lo escalarías?")
- **Hybrid search** (denso + BM25) para matches de término/código exacto, donde el denso
  flaquea — las `palabras_clave` curadas lo están pidiendo.
- **Rerank** con un cross-encoder si la separación de scores quedara pobre.
- Métricas de retrieval (recall@k, separación) corriendo en CI.
