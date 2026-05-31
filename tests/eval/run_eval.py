#!/usr/bin/env python3
"""
Evaluation harness for the RAG retrieval system.

Usage:
    python -m tests.eval.run_eval

Prerequisites:
    - Stack must be running or docs must be ingested first
    - Run: curl -X POST http://localhost:8000/api/ingest

The script loads the vector store directly (no HTTP calls) for fast evaluation.
It prints metrics and a recommended threshold value.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import settings
from app.infrastructure.embedder.e5 import E5Embedder
from app.infrastructure.vector_store.chroma import ChromaVectorStore
from tests.eval.cases import IN_SCOPE_CASES, OUT_OF_SCOPE_CASES


def run_eval() -> int:
    embedder = E5Embedder(settings.model_name)
    store = ChromaVectorStore(settings.chroma_path, settings.collection_name)

    if store.count() == 0:
        print("ERROR: Vector store is empty. Run /api/ingest first.")
        return 1

    print(f"Vector store: {store.count()} records\n")

    # --- In-scope evaluation ---
    in_scope_hits = 0
    in_scope_scores = []

    print("=== IN-SCOPE CASES ===")
    for case in IN_SCOPE_CASES:
        embedding = embedder.embed_query(case.query)
        chunks = store.query(embedding, top_k=3)
        top_score = chunks[0].score if chunks else 0.0
        in_scope_scores.append(top_score)

        if case.expected_codigo is None:
            hit = bool(chunks)
        else:
            retrieved_codigos = [c.registro.codigo for c in chunks]
            hit = case.expected_codigo in retrieved_codigos

        status = "HIT " if hit else "MISS"
        if hit:
            in_scope_hits += 1
        print(f"  [{status}] score={top_score:.3f}  {case.description}")

    # --- Out-of-scope evaluation ---
    out_of_scope_scores = []
    out_of_scope_abstentions = 0

    print("\n=== OUT-OF-SCOPE CASES ===")
    for case in OUT_OF_SCOPE_CASES:
        embedding = embedder.embed_query(case.query)
        chunks = store.query(embedding, top_k=1)
        top_score = chunks[0].score if chunks else 0.0
        out_of_scope_scores.append(top_score)
        print(f"  score={top_score:.3f}  {case.description}")

    # --- Metrics ---
    hit_rate = in_scope_hits / len(IN_SCOPE_CASES)

    # recall@k: fraction of cases where expected_codigo appears anywhere in top-k
    codigos_cases = [c for c in IN_SCOPE_CASES if c.expected_codigo is not None]
    recall_hits = 0
    for case in codigos_cases:
        embedding = embedder.embed_query(case.query)
        chunks = store.query(embedding, top_k=settings.top_k)
        if case.expected_codigo in [c.registro.codigo for c in chunks]:
            recall_hits += 1
    recall_at_k = recall_hits / len(codigos_cases) if codigos_cases else 0.0

    print(f"\n=== METRICS ===")
    print(f"  Hit-rate:          {hit_rate:.0%} ({in_scope_hits}/{len(IN_SCOPE_CASES)})")
    print(f"  Recall@{settings.top_k}:         {recall_at_k:.0%} ({recall_hits}/{len(codigos_cases)} cases with known codigo)")
    print(f"  In-scope scores:   min={min(in_scope_scores):.3f}  max={max(in_scope_scores):.3f}  avg={sum(in_scope_scores)/len(in_scope_scores):.3f}")
    print(f"  Out-scope scores:  min={min(out_of_scope_scores):.3f}  max={max(out_of_scope_scores):.3f}  avg={sum(out_of_scope_scores)/len(out_of_scope_scores):.3f}")

    # Recommend threshold: midpoint between lowest in-scope and highest out-of-scope
    if in_scope_scores and out_of_scope_scores:
        gap_low = min(in_scope_scores)
        gap_high = max(out_of_scope_scores)
        if gap_low > gap_high:
            recommended = round((gap_low + gap_high) / 2, 2)
            print(f"\n  Recommended threshold: {recommended}  (clean separation)")
        else:
            recommended = round(gap_low * 0.95, 2)
            print(f"\n  WARNING: Score distributions overlap. Suggested threshold: {recommended}")
            print(f"  Consider adding more docs or tuning the embedding model.")

    return 0 if hit_rate >= 0.80 else 1


if __name__ == "__main__":
    sys.exit(run_eval())
