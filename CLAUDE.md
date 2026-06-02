# Proyecto: Asistente RAG de soporte técnico — Prueba Técnica UNILINK

Asistente automatizado que responde preguntas de soporte usando documentación técnica
interna, vía RAG. FastAPI hace la ingesta + retrieval (parte ML); n8n orquesta y genera
la respuesta con LLM configurable (OpenAI por defecto, Anthropic opt-in). Todo levanta local con Docker.

> Engineering spec → [`DESIGN.md`](DESIGN.md)
> Design decisions (for the interview) → [`SPEC.md`](SPEC.md)

## Reglas NO negociables

1. **Grounding / no alucinar.** La respuesta nunca inventa. Si no hay contexto relevante,
   responde explícitamente que no encuentra la información. La decisión de abstención vive
   en FastAPI con un threshold calibrado, no en n8n ni en el prompt.
2. **Chunking lógico.** Un registro de error = un chunk. No dividir por caracteres.
3. **Manejo de errores.** Nunca un 500 crudo. Timeouts, inputs vacíos y errores de API
   se capturan y se devuelven como respuestas controladas.
4. **Deploy local.** `docker compose up` levanta todo el stack.

## Stack

- **FastAPI** (Python 3.11+) — endpoints `/api/ingest` y `/api/retrieve`
- **sentence-transformers** `intfloat/multilingual-e5-small` — embeddings locales, sin costo
- **ChromaDB** — vector store persistente, métrica coseno, embeddings normalizados
- **Pandas** — normalización y dedup antes de indexar
- **n8n** — orquestación + llamada a LLM configurable: OpenAI gpt-4o-mini (default, cumple brief) o Anthropic Claude Haiku (opt-in vía `LLM_PROVIDER`)
- **Docker + docker compose** — FastAPI + n8n en un solo stack
- **pytest** — unit tests + harness de evaluación

## Arquitectura (capas pragmáticas)

```
domain/          → Registro (esquema canónico), ports: Embedder, VectorStore
application/     → IngestUseCase, RetrieveUseCase
infrastructure/  → parsers (txt/md/json/pdf), E5Embedder, ChromaVectorStore, dedup
interface/       → FastAPI app, Pydantic schemas
```

Abstracciones solo donde se justifican: embedder (encapsula prefijos e5) y vector store
(testeable con mock). Nada más sin razón concreta.

## Workflow de desarrollo

- **Vertical slices en orden estricto:** Scaffolding → Ingest → Retrieve → n8n → Errores → Harness.
  Cada slice andando antes de pasar al siguiente.
- **Antes de codear, inspeccioná los archivos de `/docs`** y reportá estructura + duplicados.
- **No agregar hybrid search ni rerank** salvo que el harness demuestre que el baseline no separa.
- Leer `docs/DESIGN.md` para el "qué construir". Leer `SPEC.md` para el "por qué".

Strict TDD Mode: enabled
