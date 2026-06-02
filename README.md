# Prueba Técnica – Juan Ignacio Cabral

Asistente RAG de soporte técnico para UNILINK.

## Requisitos

- Docker y Docker Compose
- Python 3.11+ (solo para tests locales)

## Levantar el stack

```bash
cp .env.example .env
# Completar OPENAI_API_KEY (o ANTHROPIC_API_KEY si usás LLM_PROVIDER=anthropic)
docker compose up --build
```

La API queda disponible en `http://localhost:8000`.
n8n queda disponible en `http://localhost:5678`.

## Importar el workflow de n8n

1. Abrí `http://localhost:5678`
2. Ir a **Workflows → Import from file**
3. Seleccioná `n8n_workflows/rag_support_workflow.json`
4. Activá el workflow

## Ingestar la documentación

```bash
curl -X POST http://localhost:8000/api/ingest
```

## Probar el asistente

Via n8n webhook:
```bash
curl -X POST http://localhost:5678/webhook/rag-support \
  -H "Content-Type: application/json" \
  -d '{"query": "No puedo conectar a la base de datos"}'
```

Via API directa:
```bash
curl -X POST http://localhost:8000/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "No puedo conectar a la base de datos"}'
```

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Proveedor LLM del workflow n8n (`openai` o `anthropic`) |
| `OPENAI_API_KEY` | — | Requerido si `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | — | Requerido si `LLM_PROVIDER=anthropic` |
| `RAG_THRESHOLD` | `0.80` | Umbral de similitud coseno para abstención |
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
