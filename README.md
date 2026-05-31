# Prueba Técnica – Juan Ignacio Cabral

Asistente RAG de soporte técnico para MineCatalog.

## Requisitos

- Docker y Docker Compose
- Python 3.11+ (solo para tests locales)

## Levantar el stack

```bash
cp .env.example .env
# Completar OPENAI_API_KEY en .env
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

## Tests

```bash
pip install -e ".[dev]"
pytest tests/unit/
```
