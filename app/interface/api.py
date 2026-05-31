"""FastAPI application — interface layer.

Wires the domain use cases to HTTP endpoints via dependency injection.
"""

from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.application.ingest import IngestResult, IngestUseCase
from app.application.retrieve import RetrieveUseCase
from app.config import Settings
from app.domain.ports import Embedder, VectorStore
from app.interface.schemas import IngestResponse, RetrieveRequest, RetrieveResponse, ResultItem

app = FastAPI(title="RAG Support Assistant")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler — ensures no raw 500 ever reaches the caller."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Ocurrió un error interno. Por favor intentá de nuevo.",
        },
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_embedder() -> Embedder:
    from app.infrastructure.embedder.e5 import E5Embedder

    return E5Embedder(get_settings().model_name)


@lru_cache
def get_store() -> VectorStore:
    from app.infrastructure.vector_store.chroma import ChromaVectorStore

    s = get_settings()
    return ChromaVectorStore(s.chroma_path, s.collection_name)


def get_ingest_uc(
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> IngestUseCase:
    from app.infrastructure.dedup.pandas_dedup import PandasDeduplicator
    from app.infrastructure.parsers.json import JsonParser
    from app.infrastructure.parsers.md import MdParser
    from app.infrastructure.parsers.pdf import PdfParser
    from app.infrastructure.parsers.txt import TxtParser

    parsers = {
        ".txt": TxtParser(),
        ".md": MdParser(),
        ".json": JsonParser(),
        ".pdf": PdfParser(),
    }
    return IngestUseCase(
        parsers=parsers,
        embedder=embedder,
        store=store,
        dedup=PandasDeduplicator(),
        docs_path=Path(settings.docs_path),
    )


@app.post("/api/ingest", response_model=IngestResponse)
def ingest(use_case: IngestUseCase = Depends(get_ingest_uc)) -> IngestResponse:
    """Parse, deduplicate, embed, and index all documentation files."""
    try:
        result: IngestResult = use_case.execute()
        return IngestResponse(
            documentos=result.documentos,
            chunks=result.chunks,
            duplicados_removidos=result.duplicados_removidos,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "ingest_failed", "message": str(exc)},
        ) from exc


@app.post("/api/retrieve", response_model=RetrieveResponse)
def retrieve(
    request: RetrieveRequest,
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> RetrieveResponse:
    """Retrieve relevant documentation chunks for a query.

    Returns ``found: true`` with results when the top-1 similarity meets
    the configured threshold, or ``found: false`` (abstention) otherwise.
    """
    try:
        use_case = RetrieveUseCase(
            embedder=embedder,
            store=store,
            threshold=settings.threshold,
            top_k=settings.top_k,
        )
        result = use_case.execute(request.query)
        return RetrieveResponse(
            found=result.found,
            results=[
                ResultItem(
                    codigo=item.codigo,
                    titulo=item.titulo,
                    context=item.context,
                    score=item.score,
                    source=item.source,
                )
                for item in result.results
            ],
            message=result.message,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "retrieve_failed", "message": str(exc)},
        ) from exc
