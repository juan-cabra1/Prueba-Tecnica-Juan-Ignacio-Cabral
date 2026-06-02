# Technical Design — Asistente RAG de soporte técnico

> **What to build** — engineering spec and contracts.
> For *why* these decisions were made, see [`SPEC.md`](../SPEC.md).
> For agent instructions, see [`CLAUDE.md`](../CLAUDE.md).

---

## Canonical Data Model

All 4 source formats (.txt, .md, .json, .pdf) represent the same entity: an error/incident record.
Normalise everything to one schema before indexing.

```python
class Registro(BaseModel):
    codigo: str | None          # e.g. ERR-DB-001; None when source has no code
    titulo: str
    categoria: str
    mensaje_usuario: str
    causas: list[str]
    solucion: list[str]
    palabras_clave: list[str]
    nivel_soporte: str | None   # only json source provides this
    source_file: str
```

---

## Chunking Rules (one record = one chunk)

### JSON (`Documentación 4.json`)
- Top-level metadata (`software`, `modulo`) propagates to each record in `contenido[]`.
- Each item in `contenido[]` is one `Registro`. Fields map 1:1 to the canonical schema.

### Markdown (`Documentación 3.md`)
- Split on `#` (H1 = one error record).
- `##` headers map to schema fields:
  - `## Código` → `codigo`
  - `## Categoría` → `categoria`
  - `## Mensaje mostrado al usuario` → `mensaje_usuario`
  - `## Causas posibles` → `causas`
  - `## Solución recomendada` → `solucion`
  - `## Palabras clave` → `palabras_clave`

### Plain text (`Documentación 2.txt`)
- Split on regex `\d+\.\d+\s+Error:` (sections 3.2, 3.3, ...).
- Labels to normalise (synonyms → canonical field):
  - `Mensaje mostrado` → `mensaje_usuario`
  - `Causas posibles` → `causas`
  - `Solución` → `solucion`
- **No `codigo` in this source.** Dedup will backfill from JSON when a match is found.

### PDF (`Documentación 1.pdf`)
- Extract text via pdfplumber or PyMuPDF; then apply pattern `\d+\.\d+` for section splits.
- **Edge case**: first record ("El catálogo carga lentamente") has no section number.
  The regex will miss it — the parser must handle this headerless leading block explicitly.
- Labels: `Posibles causas` → `causas`, `Acciones recomendadas` → `solucion`.
- Last block "Contacto de soporte técnico" is global metadata, not a record.
  Store as collection-level metadata (email, hours, support levels 1–3).
- **No `codigo` in this source.**

---

## Cross-Source Deduplication

**Known exact duplicates** (confirmed by inspection):

| Canonical code | Sources            | Match signal                                              |
|----------------|--------------------|-----------------------------------------------------------|
| `ERR-DB-001`   | JSON ↔ TXT 3.2     | Same `mensaje_usuario`: "Error de conexión con el servidor de datos." |
| `ERR-CAT-001`  | JSON ↔ TXT 3.3     | Same `mensaje_usuario`: "Ya existe un material registrado con este código." |

**Dedup strategy** (pandas):
1. Load all normalised records into a DataFrame.
2. Deduplicate by `codigo` when both sides have one.
3. For records without `codigo` (TXT, PDF): match by normalised title similarity
   (exact or near-exact string match after lowercasing + stripping punctuation).
4. On merge: keep the JSON record as the canonical version (it has `nivel_soporte` and `palabras_clave`).
   **Backfill `codigo` into the merged record** from the JSON side.
5. Report `duplicados_removidos` count in the ingest response.

Expected result: **12 unique records** from 14 raw records.

---

## Embeddings — Prefix Handling (critical)

`intfloat/multilingual-e5-small` was trained with prefixes and degrades silently without them.
The `E5Embedder` class **makes it impossible to forget them**:

```python
class E5Embedder:
    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(f"query: {text}", normalize_embeddings=True).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(
            [f"passage: {t}" for t in texts], normalize_embeddings=True
        ).tolist()
```

- Ingest always calls `embed_documents` (prefix `passage:`).
- Retrieve always calls `embed_query` (prefix `query:`).
- **No other code calls the model directly.**

---

## Text to Embed vs Context Payload (two distinct fields)

| Field              | Purpose                                             | Content                                          |
|--------------------|-----------------------------------------------------|--------------------------------------------------|
| Embedded text      | Vector similarity search                            | `titulo + mensaje_usuario + causas + solucion + palabras_clave` (joined) |
| Context payload    | Returned to n8n for prompt construction             | Structured `Registro` with `codigo` and `source_file` for citation |

---

## Retrieval and Abstention

```
POST /api/retrieve  { "query": "string" }
```

1. Embed query with `embed_query` (prefix `query:`).
2. Query ChromaDB: `top-k = 3`, cosine similarity, normalised vectors.
3. Evaluate top-1 score against **calibrated threshold**:
   - Score ≥ threshold → `found: true`, return results.
   - Score < threshold → `found: false`, empty results, no LLM call.
4. Threshold is a **placeholder** in Slice 2; calibrated empirically in Slice 5 via the eval harness.

Response schema:
```json
// found
{ "found": true,  "results": [{ "codigo": "...", "titulo": "...", "context": "...", "score": 0.87, "source": "..." }] }
// not found
{ "found": false, "results": [], "message": "No se encontró información relevante en la documentación." }
```

---

## API Contract

### `POST /api/ingest`

- Reads all files in `/docs` directory.
- Parses, normalises, deduplicates, embeds, and indexes.
- Returns:
  ```json
  { "documentos": 4, "chunks": 12, "duplicados_removidos": 2 }
  ```
- Input validation: no request body required. Errors → controlled response, no 500.

### `POST /api/retrieve`

- Request: `{ "query": "string" }` — empty string → 422 (Pydantic).
- Response: see Retrieval schema above.
- All errors → controlled response, no raw 500.

---

## n8n Workflow

**Trigger**: HTTP Webhook — receives `{ "question": "string" }`.

**Flow**:
1. Validate query (empty → HTTP 400 immediately, no retrieve call).
2. Call `POST /api/retrieve { "query": question }`.
3. If `found: false` → return abstention message (HTTP 404). Do not call the LLM.
4. If `found: true` (HTTP 200):
   - Route to the configured LLM provider via `LLM_PROVIDER` env var (default: `openai`).
     - `openai`: `n8n-nodes-base.openAi`, model `gpt-4o-mini` (satisfies brief requirement).
     - `anthropic`: `@n8n/n8n-nodes-langchain.anthropic`, model `claude-haiku-4-5-20251001`.
   - Build grounded prompt:
     ```
     System: Answer ONLY from the provided context. Cite the error code (e.g. ERR-DB-001)
             when available. If the answer is not in the context, say so explicitly.
     Context: {formatted results from /retrieve}
     User: {question}
     ```
   - Call LLM (configured timeout + error branch).
   - Return the response with `{answer, found: true}`.

**HTTP status codes**:
- `200` — answer found and generated.
- `404` — abstention (no relevant document above threshold). No LLM call.
- `400` — empty or missing query.
- `502` — LLM or retrieve API error.
- `504` — timeout.

**Error handling in n8n**:
- LLM node: configure timeout + dedicated error branch → HTTP 502/504.
- Error branch returns a controlled message (never a raw exception).

**Export**: workflow saved to `/n8n_workflows/` as JSON.

---

## Evaluation Harness

**Location**: `tests/eval/`

**Test cases** (~8–10):
- In-scope questions mapped to expected `codigo` (e.g. "no puedo conectar a la BD" → `ERR-DB-001`).
- Out-of-scope from the problem statement: "¿Cómo reinicio el servicio de autenticación?", "El sistema devuelve error 502".

**Metrics** (`tests/eval/run_eval.py`):
- Hit-rate: fraction of in-scope queries where expected `codigo` is in top-k results.
- Recall@k: fraction where expected code is retrieved at all within top-k.
- Top-1 score distribution: histogram / summary of in-scope vs out-of-scope scores.

**Dual purpose**:
1. Calibrate the abstention threshold: choose the value that maximally separates in-scope from out-of-scope top-1 scores.
2. Demo in the technical interview: show that the system abstains on out-of-scope queries without calling the LLM.

---

## Deliverables Checklist

- [ ] `README.md` — local setup instructions (`docker compose up`)
- [ ] `.env.example` — `OPENAI_API_KEY` and any other required variables
- [ ] `n8n_workflows/` — exported workflow JSON
- [ ] Python source code (`app/`)
- [ ] `docker-compose.yml` — FastAPI + n8n + persistent Chroma volume
- [ ] `tests/` — unit tests + eval harness
