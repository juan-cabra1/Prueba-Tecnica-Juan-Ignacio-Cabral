# Prueba Técnica – Juan Ignacio Cabral

Asistente RAG de soporte técnico para MineCatalog.

## Requisitos

- Docker y Docker Compose
- Python 3.11+ (solo para tests locales)

## Setup paso a paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/juan-cabra1/Prueba-Tecnica-Juan-Ignacio-Cabral.git
cd Prueba-Tecnica-Juan-Ignacio-Cabral
```

### 2. Levantar el stack

```bash
cp .env.example .env
docker compose up --build
```

La API queda disponible en `http://localhost:8000`.
n8n queda disponible en `http://localhost:5678`.

### 3. Configurar credenciales en n8n

Las API keys del LLM se configuran directamente en n8n (no en `.env`):

1. Abrí `http://localhost:5678`
2. Ir a **Settings → Credentials → Add credential**
3. Según el proveedor que uses:
   - **OpenAI**: creá una credencial de tipo `OpenAI API` con tu `OPENAI_API_KEY`
   - **Anthropic**: creá una credencial de tipo `Anthropic API` con tu `ANTHROPIC_API_KEY`
4. Asignala al nodo correspondiente dentro del workflow

> El sistema fue probado con **Anthropic Claude Haiku**. El nodo OpenAI está configurado con `gpt-4o-mini` y el mismo system prompt, pero requiere que completes la credencial y verifiques el path de respuesta (`$json.message.content`) corriendo el nodo una vez.

### 4. Importar el workflow de n8n

1. Ir a **Workflows → Import from file**
2. Seleccioná `n8n_workflows/RAG Support Assistant.json`
3. Abrí cada nodo que muestre error en rojo — al abrirlo el error desaparece (comportamiento normal de n8n al importar)
4. Activá el workflow con el toggle superior derecho

### 5. Seleccionar el proveedor LLM

El workflow tiene un nodo Switch que rutea a OpenAI o Anthropic:

1. Abrí el nodo **LLM Provider** en el workflow
2. Cambiá el valor hardcodeado a `openai` o `anthropic`
3. Guardá el workflow

### 6. Ingestar la documentación

```bash
curl -X POST http://localhost:8000/api/ingest
```

> La primera vez tarda ~2 minutos por la descarga del modelo de embeddings.

### 7. Probar el asistente

**Modo test** (sin activar el workflow, click en "Test workflow" en n8n):
```bash
curl -X POST http://localhost:5678/webhook-test/rag-support \
  -H "Content-Type: application/json" \
  -d '{"query": "No puedo conectar a la base de datos"}'
```

**Modo producción** (workflow activado):
```bash
curl -X POST http://localhost:5678/webhook/rag-support \
  -H "Content-Type: application/json" \
  -d '{"query": "No puedo conectar a la base de datos"}'
```

**Via API directa** (bypass n8n, solo retrieval):
```bash
curl -X POST http://localhost:8000/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "No puedo conectar a la base de datos"}'
```

## Variables de entorno

Estas variables se configuran en `.env` y afectan al servicio FastAPI:

| Variable | Default | Descripción |
|---|---|---|
| `RAG_THRESHOLD` | `0.88` | Umbral de similitud coseno para abstención |
| `RAG_TOP_K` | `3` | Top-K resultados a recuperar |

## HTTP status codes del webhook

| Resultado | Código |
|---|---|
| Respuesta grounded encontrada | `200` |
| No hay información (abstención) | `404` |
| Query vacía o inválida | `400` |
| Error del LLM o de la API de retrieval | `502` |
| Timeout | `504` |

## Tests

```bash
pip install -e ".[dev]"
pytest tests/unit/
```

## Limitaciones conocidas

- **Stateless por diseño**: cada consulta es independiente, sin memoria de conversación. Para soporte multi-turn se requeriría gestión de sesiones y contexto histórico.
- **Retrieval denso con códigos exactos**: queries con solo el código de error (ej. `ERR-DB-001`) puntúan bajo en similitud semántica y pueden abstenar. Usar descripción en lenguaje natural mejora el retrieval.
- **Hybrid search no implementado**: el retrieval denso flaquea en matches de término exacto. Hybrid search (denso + BM25) es el next step natural si el corpus crece o se agregan más códigos de error.
