# Prueba Técnica – Juan Ignacio Cabral

Asistente RAG de soporte técnico para MineCatalog.

> Decisiones de arquitectura y tradeoffs → [`ARQUITECTURA.md`](ARQUITECTURA.md)

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

Primero, copiá `.env.example` a `.env` según tu OS:

```bash
# macOS / Linux / Git Bash
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env

# Windows cmd
copy .env.example .env
```

> El `.env` es **opcional**: todas las variables tienen defaults razonables. Solo lo necesitás si querés ajustar `RAG_THRESHOLD` o `RAG_TOP_K`. No se configura ninguna API key aquí — esas van en n8n (paso 3).

```bash
docker compose up --build
```

> La primera vez que se buildea tarda **10–15 minutos** descargando dependencias (PyTorch, ChromaDB, etc.). Las siguientes veces son instantáneas gracias al cache de Docker.
> Una vez que los contenedores estén levantados, esperá unos segundos a que la API esté lista antes de continuar con el paso 3.

La API queda disponible en `http://localhost:8000`.
n8n queda disponible en `http://localhost:5678`.

### 3. Ingestar la documentación

```bash
curl -X POST http://localhost:8000/api/ingest
```

> La primera vez tarda **3–5 minutos** por la descarga del modelo de embeddings. Mientras esperás, continuá con los pasos 4 y 5.

### 4. Configurar credenciales en n8n

Las API keys del LLM se configuran directamente en la UI de n8n (no en `.env`):

1. Abrí `http://localhost:5678`
2. En el Overview, andá a la pestaña **Credentials** (al lado de Workflows)
3. Hacé click en **Create Credential** (botón naranja, arriba a la derecha)
4. Seleccioná el proveedor:
   - **OpenAI API** → Continue → pegá tu `OPENAI_API_KEY` → Base URL: `https://api.openai.com/v1` → **Save**
   - **Anthropic API** → Continue → pegá tu `ANTHROPIC_API_KEY` → **Save**
5. Repetí el proceso para el otro proveedor si lo vas a usar

> El sistema fue probado con **Anthropic Claude Haiku**. El nodo OpenAI está configurado con `gpt-4o-mini` y el mismo system prompt, pero requiere que completes la credencial y verifiques el path de respuesta (`$json.message.content`) corriendo el nodo una vez.

### 5. Importar el workflow de n8n

1. Pestaña **Workflows** → botón naranja **Create Workflow** (arriba a la derecha)
2. En el canvas vacío, abrí el menú **⋮** (arriba a la derecha) → **Import from File**
3. Seleccioná `n8n_workflows/RAG Support Assistant.json`
4. Si aparecen nodos en rojo: hacé click en cada uno para abrirlo — el error desaparece al abrirlo (comportamiento normal de n8n al importar)
5. Click derecho en el canvas → **Tidy up workflow** para ordenar los nodos

### 6. Seleccionar el proveedor LLM

El workflow tiene un nodo **IF** llamado "LLM Provider" que rutea a OpenAI o Anthropic:

1. Abrí el nodo **LLM Provider** en el workflow
2. Cambiá el valor hardcodeado a `openai` o `anthropic`
3. Guardá el workflow
4. **Desactivá el nodo del proveedor que NO vas a usar**: hacé click derecho sobre el nodo LLM que no elegiste (Anthropic u OpenAI) → **Deactivate**. Si no lo hacés, n8n detecta el nodo sin credencial y no te deja publicar el workflow.

### 7. Probar el asistente

Hay dos modos de webhook — la diferencia importa:

- **Test** (`/webhook-test/...`): n8n registra el listener por **una sola request** cuando apretás el botón **"Test workflow"** en la UI. Útil para debug puntual.
- **Producción** (`/webhook/...`): el endpoint vive **de forma continua** una vez que publicás el workflow. Para publicarlo: hacé click en el botón **Publish** (arriba a la derecha), escribí un nombre y confirmá con el botón naranja. El botón "Execute workflow" del centro **no** activa producción.

> **Antes de publicar:** asegurate de haber completado el paso 3 (ingestar docs) y el paso 4 (credenciales). Si algún nodo no tiene credencial seteada, la publicación falla silenciosamente y el webhook de producción no responde.

**Modo test** (apretá "Test workflow" en n8n, luego enviá esta request):
```bash
curl -X POST http://localhost:5678/webhook-test/rag-support \
  -H "Content-Type: application/json" \
  -d '{"query": "No puedo conectar a la base de datos"}'
```

**Modo producción** (hay que hacer publish del workflow n8n, luego enviá):
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

## Mini UI (sin Postman)

Con el stack levantado y el workflow de n8n **Active** (paso 7), abrí `http://localhost:8000/` en el browser.

Escribí tu consulta y hacé click en **Enviar**. La UI muestra:
- La respuesta generada por el LLM (`answer`)
- Si se encontró información relevante (`found`)
- El código de estado lógico (`statusCode`) y el JSON crudo completo

> **Prerequisito**: el workflow de n8n debe estar **Active** con credenciales cargadas (igual que el modo producción del paso 7). La UI pega directamente al webhook de producción.

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
