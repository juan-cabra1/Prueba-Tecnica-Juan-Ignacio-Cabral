"""FastAPI application — interface layer.

Wires the domain use cases to HTTP endpoints via dependency injection.
"""

from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI

from app.application.ingest import IngestResult, IngestUseCase
from app.config import Settings
from app.domain.ports import Embedder, VectorStore
from app.interface.schemas import IngestResponse

app = FastAPI(title="RAG Support Assistant")


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
def ingest(uc: IngestUseCase = Depends(get_ingest_uc)) -> IngestResponse:
    """Parse, deduplicate, embed, and index all documentation files."""
    result: IngestResult = uc.execute()
    return IngestResponse(
        documentos=result.documentos,
        chunks=result.chunks,
        duplicados_removidos=result.duplicados_removidos,
    )
