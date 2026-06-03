# Arquitectura del sistema — RAG Support Assistant

## Contexto y objetivo

Se construyó un asistente de soporte técnico basado en Retrieval-Augmented Generation (RAG)
para responder preguntas sobre documentación técnica interna de MineCatalog.
El objetivo es entregar respuestas grounded — es decir, respaldadas exclusivamente
por documentación indexada — evitando que el sistema invente información.

El sistema atiende consultas en lenguaje natural y devuelve una respuesta generada
por un LLM, acompañada de los fragmentos de documentación recuperados y un indicador
explícito de si se encontró información relevante (`found: true/false`).

---

## Vista de arquitectura

El sistema se divide en dos subsistemas con responsabilidades bien delimitadas:

- **FastAPI** maneja la capa de Machine Learning: embeddings, retrieval y abstención.
- **n8n** maneja la orquestación: validación de entrada, llamada al LLM y construcción de la respuesta.

```
┌─────────────────────────────────────────────────────────┐
│                        n8n                              │
│  Webhook → Empty Query? → HTTP Request → Found?         │
│              → LLM Provider → OpenAI/Anthropic → Resp.  │
└──────────────────────┬──────────────────────────────────┘
                       │ POST /api/retrieve
┌──────────────────────▼──────────────────────────────────┐
│                     FastAPI                             │
│                                                         │
│  interface/     ← Pydantic schemas, HTTP endpoints      │
│  application/   ← IngestUseCase, RetrieveUseCase        │
│  infrastructure/← E5Embedder, ChromaVectorStore,        │
│                   parsers (txt/md/json/pdf), dedup      │
│  domain/        ← Registro (entidad), ports (Embedder,  │
│                   VectorStore) — sin dependencias ext.  │
└─────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              ChromaDB (persistente)                     │
│  Colección con embeddings normalizados, métrica coseno  │
└─────────────────────────────────────────────────────────┘
```

**División de responsabilidades:**

| Subsistema | Responsabilidad |
|------------|----------------|
| FastAPI    | Embeddings locales, retrieval semántico, lógica de abstención, ingesta y dedup |
| n8n        | Orquestación del flujo, llamada al LLM, construcción y entrega de la respuesta HTTP |

Esta separación permite reemplazar el proveedor de LLM sin tocar el código Python,
y permite testear el retrieval de forma aislada, sin dependencias externas de API.

---

## Decisiones clave

### 1. Embeddings locales (multilingual-e5-small) en lugar de OpenAI Embeddings

| Campo | Detalle |
|-------|---------|
| **Decisión** | Usar `intfloat/multilingual-e5-small` ejecutado localmente vía `sentence-transformers` |
| **Alternativa** | `text-embedding-ada-002` u otro modelo de OpenAI vía API |
| **Rationale** | Cero costo por llamada, sin latencia de red, sin dependencia de API key para la capa ML. El corpus es pequeño y está en español; el modelo e5 multilingüe cubre el dominio. La calidad observada en el harness de evaluación fue suficiente para el baseline. |

---

### 2. multilingual-e5-small en lugar de paraphrase-MiniLM o similares

| Campo | Detalle |
|-------|---------|
| **Decisión** | Elegir un modelo e5 (asimetría query/passage) en lugar de modelos simétricos como MiniLM |
| **Alternativa** | `paraphrase-MiniLM-L6-v2` u otros modelos simétricos |
| **Rationale** | Los modelos e5 están diseñados para búsqueda asimétrica: una query corta del usuario se compara contra pasajes más largos de documentación. MiniLM y modelos simétricos optimizan para similitud entre textos del mismo tipo y longitud, lo que degrada el retrieval en escenarios query-vs-documento. La distinción semántica de prefijos (`query:` vs `passage:`) es el mecanismo que lo hace posible. |

---

### 3. E5Embedder encapsula los prefijos query/passage

| Campo | Detalle |
|-------|---------|
| **Decisión** | El prefijo `"query: "` y `"passage: "` se agregan dentro de `E5Embedder`, no en el caller |
| **Alternativa** | Que cada caso de uso o parser agregue el prefijo manualmente antes de llamar al embedder |
| **Rationale** | Si el prefijo es responsabilidad del caller, cualquier punto de entrada nuevo puede olvidarlo y producir embeddings incompatibles con el índice, degradando el retrieval sin error visible. Al encapsular el prefijo en el embedder, la invariante se mantiene por construcción: es imposible obtener un embedding sin el prefijo correcto. |

---

### 4. ChromaDB con métrica coseno y embeddings normalizados

| Campo | Detalle |
|-------|---------|
| **Decisión** | ChromaDB con `hnsw:space=cosine` y embeddings normalizados (L2 norm = 1) |
| **Alternativa** | FAISS (producto punto), Qdrant, Pinecone, etc. |
| **Rationale** | ChromaDB es persistente por defecto, no requiere infraestructura adicional y se integra directamente en el proceso Python. La similitud coseno es la métrica estándar para embeddings semánticos. La normalización previa (incluida en `sentence-transformers` con `normalize_embeddings=True`) hace que producto punto y coseno sean equivalentes, asegurando comparabilidad entre query embeddings y document embeddings. |

---

### 5. Chunking lógico: un registro de error = un chunk

| Campo | Detalle |
|-------|---------|
| **Decisión** | Cada registro de error (con código, título, causas y solución) es un chunk indivisible |
| **Alternativa** | Chunking por caracteres o ventana deslizante (estrategia común en RAG genérico) |
| **Rationale** | El corpus es documentación técnica estructurada. Cortar un registro a mitad de la lista de causas destruye la coherencia semántica del chunk y degrada el retrieval. Un registro completo es la unidad de información mínima coherente. El chunking por caracteres tiene sentido para documentos de prosa continua, no para registros estructurados. |

---

### 6. Esquema canónico (Registro) + deduplicación cross-source con Pandas

| Campo | Detalle |
|-------|---------|
| **Decisión** | Normalizar todas las fuentes a la entidad `Registro` antes de indexar; deduplicar por código o hash de contenido usando Pandas |
| **Alternativa** | Indexar directamente desde cada parser sin normalizar; detectar duplicados en el vector store |
| **Rationale** | La deduplicación en el vector store (por similitud) es costosa y aproximada. Detectarla antes de indexar, sobre datos normalizados, es exacta y barata. El esquema canónico desacopla los parsers del vector store: agregar un nuevo formato (XML, CSV) solo requiere implementar el parser sin tocar la lógica de almacenamiento. |

---

### 7. Lógica de abstención en FastAPI (threshold 0.85), no en n8n ni en el prompt

| Campo | Detalle |
|-------|---------|
| **Decisión** | Si el score del top-1 resultado es menor que 0.85, FastAPI retorna `found: false` sin enviar contexto al LLM |
| **Alternativa** | Delegar la decisión de abstención al prompt del LLM ("si no tenés información, decí que no sabés") o a n8n mediante un nodo IF sobre la respuesta del LLM |
| **Rationale** | La abstención vía prompt es inestable: el LLM puede ignorar la instrucción e inventar una respuesta plausible. La abstención vía score es determinista, testeable con pytest y calibrable con el harness de evaluación. Vive donde se puede medir. El threshold 0.85 fue seleccionado empíricamente sobre el corpus; es configurable vía `RAG_THRESHOLD`. Nota: los embeddings e5 comprimen los scores en una banda estrecha por anisotropía del coseno — lo que importa es la separación relativa entre scores, no el valor absoluto. |

---

### 8. Anisotropía del coseno con embeddings e5

| Campo | Detalle |
|-------|---------|
| **Decisión** | El threshold se calibra empíricamente sobre el corpus real, no se establece a 0.5 o 0.7 por convención |
| **Alternativa** | Usar un umbral arbitrario "intuitivo" (ej. 0.7 = "70% de similitud") |
| **Rationale** | Los modelos de embedding no producen scores distribuidos uniformemente en [0, 1]. E5 y modelos similares sufren anisotropía: los embeddings se concentran en un cono del espacio vectorial y los scores coseno se comprimen en una banda estrecha (ej. 0.75–0.95). Un score de 0.80 puede ser "no relevante" y 0.85 puede ser "muy relevante" para el mismo corpus. La única forma de calibrar el threshold correctamente es medir separación relativa sobre ejemplos reales. |

---

### 9. HTTP status codes diferenciados (200/404/400/502/504) desde n8n

| Campo | Detalle |
|-------|---------|
| **Decisión** | n8n devuelve status codes REST semánticos: 200 (encontrado), 404 (abstención), 400 (query vacía), 502 (error LLM), 504 (timeout) |
| **Alternativa** | Devolver siempre HTTP 200 con un campo `status` en el body (patrón "always-200") |
| **Rationale** | Los status codes REST existen para que clientes e infraestructura (load balancers, monitores, alertas) puedan reaccionar sin parsear el body. El patrón always-200 es un antipatrón que rompe la semántica HTTP y complica el monitoreo. El costo de implementarlo correctamente en n8n es bajo. |

---

### 10. LLM configurable: OpenAI gpt-4o-mini (default) / Anthropic Haiku (opt-in)

| Campo | Detalle |
|-------|---------|
| **Decisión** | El workflow n8n tiene un nodo IF que rutea a OpenAI o Anthropic según una variable configurable |
| **Alternativa** | Hardcodear un único proveedor LLM |
| **Rationale** | Diferentes entornos o equipos pueden tener acceso a distintos proveedores. La configuración vía variable (sin redeployment) reduce la fricción de adopción. OpenAI gpt-4o-mini es el default por estar especificado en el brief; Anthropic Haiku es el opt-in validado durante el desarrollo. |

---

### 11. Frontera de credenciales: FastAPI sin API keys LLM; n8n las posee

| Campo | Detalle |
|-------|---------|
| **Decisión** | Las API keys del LLM (OpenAI, Anthropic) se configuran exclusivamente en la UI de n8n, no en `.env` ni en el código Python |
| **Alternativa** | Centralizar todas las configuraciones en `.env` y pasarlas al contenedor FastAPI |
| **Rationale** | FastAPI es la capa ML: no necesita keys LLM para embeddings ni retrieval. Concentrar credenciales en n8n reduce la superficie de exposición y aprovecha el vault de credenciales nativo de n8n, que almacena los valores cifrados. El `.env` solo contiene parámetros de tuning del retrieval (threshold, top_k). |

---

### 12. Clean architecture pragmática: abstraer solo donde se justifica

| Campo | Detalle |
|-------|---------|
| **Decisión** | Interfaces (Protocols) solo para `Embedder` y `VectorStore`; parsers son clases concretas sin Protocol compartido en producción |
| **Alternativa** | Definir Protocols para cada componente, incluyendo parsers, deduplicadores y casos de uso |
| **Rationale** | Una abstracción se justifica cuando hay más de una implementación real o cuando facilita el testing. `Embedder` tiene la implementación E5 (producción) y un fake en tests. `VectorStore` tiene ChromaDB (producción) y un fake en tests. Los parsers, en cambio, se seleccionan por extensión de archivo en tiempo de construcción del use case — no se intercambian en runtime. Abstraer todo agrega complejidad sin beneficio medible. |

---

### 13. No hybrid search ni reranking: corpus no lo justifica aún

| Campo | Detalle |
|-------|---------|
| **Decisión** | El retrieval usa solo búsqueda densa (embeddings), sin BM25 ni reranking |
| **Alternativa** | Hybrid search (denso + BM25), cross-encoder reranking |
| **Rationale** | El corpus actual es pequeño y estructurado. El harness de evaluación no mostró evidencia de que el retrieval denso falle sistemáticamente en matches de término exacto para el volumen actual. Implementar hybrid search agrega dependencias (BM25, índice invertido) y complejidad de fusión de scores. El criterio es: medir primero, optimizar después. El harness está diseñado precisamente para detectar cuándo el baseline no separa. |

---

## Limitaciones conocidas

1. **Sistema stateless por diseño**: cada consulta es independiente, sin memoria de conversación.
   Para soporte multi-turn se requeriría gestión de sesiones y contexto histórico, lo que
   incrementa la complejidad de la infraestructura (almacenamiento de sesiones, expiración, etc.).

2. **Retrieval denso limitado para códigos de error exactos**: queries que contienen solo el
   código de error (ej. `ERR-DB-001`) puntúan bajo en similitud semántica porque el embedding
   del código aislado difiere del embedding del registro completo. El retrieval mejora cuando la
   consulta usa lenguaje natural descriptivo. Hybrid search (denso + BM25) resolvería este caso,
   pero no se implementó por las razones descritas en la decisión 13.

---

## Próximos pasos

1. **Hybrid search (denso + BM25)**: integrar un índice de texto completo (BM25 o equivalente)
   junto al retrieval denso, con fusión de scores (Reciprocal Rank Fusion). Activar si el harness
   de evaluación detecta que queries con códigos exactos no alcanzan el threshold.

2. **Cross-encoder reranking**: después de recuperar los top-K candidatos por embeddings,
   aplicar un cross-encoder (ej. `cross-encoder/ms-marco-MiniLM-L-6-v2`) para reordenar
   por relevancia real antes de pasar el contexto al LLM. Activar si la precisión del top-1
   cae por debajo del objetivo en el harness.

3. **Métricas de evaluación en CI**: automatizar la ejecución del harness de evaluación en
   el pipeline de CI para detectar regresiones de retrieval cuando se actualice el corpus
   o se modifiquen los parámetros del embedder.
