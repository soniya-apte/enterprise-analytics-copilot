"""RAG store: embed the table descriptions into pgvector and retrieve the relevant ones.

Usage (run from backend/):  python -m rag.store     # (re)index + measure retrieval recall
"""
import re
from functools import lru_cache

from fastembed import TextEmbedding
from sqlalchemy import text

from database import app_engine
from rag.schema_docs import build_docs

MODEL_NAME = "BAAI/bge-small-en-v1.5"   # free local model, 384-dimensional embeddings
TOP_K = 6

# Only the notes the hand-written v1 context (agents/schema_context.py) already had,
# so the RAG experiment changes HOW schema knowledge is selected, not WHAT extra knowledge exists.
NOTES = {
    "sales.salesorderheader": "Order-level revenue: SUM(totaldue) (the full order amount). "
                              "Data spans 2022-2025 (orderdate).",
    "sales.salesorderdetail": "There is NO linetotal column. Line/product-level revenue: "
                              "SUM(orderqty * unitprice * (1 - unitpricediscount)).",
}


@lru_cache(maxsize=1)
def _model():
    return TextEmbedding(MODEL_NAME)   # loaded once, then reused


def _vec(v) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def index_schema() -> int:
    """Embed every table description and upsert it into the schema_embeddings table."""
    docs = build_docs(NOTES)
    vectors = list(_model().passage_embed([d["doc"] for d in docs]))
    with app_engine.begin() as c:
        c.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_embeddings (
                table_name TEXT PRIMARY KEY,
                doc        TEXT NOT NULL,
                embedding  vector(384) NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )"""))
        c.execute(text("""
            INSERT INTO schema_embeddings (table_name, doc, embedding)
            VALUES (:t, :d, CAST(:e AS vector))
            ON CONFLICT (table_name) DO UPDATE
                SET doc = EXCLUDED.doc, embedding = EXCLUDED.embedding, updated_at = now()
        """), [{"t": d["table"], "d": d["doc"], "e": _vec(v)} for d, v in zip(docs, vectors)])
    return len(docs)


def retrieve(question: str, k: int = TOP_K) -> list:
    """Return the k table descriptions most similar to the question (cosine similarity)."""
    q = _vec(next(iter(_model().query_embed([question]))))
    with app_engine.connect() as c:
        rows = c.execute(text("""
            SELECT table_name, doc, 1 - (embedding <=> CAST(:q AS vector)) AS similarity
            FROM schema_embeddings
            ORDER BY embedding <=> CAST(:q AS vector)
            LIMIT :k
        """), {"q": q, "k": k}).all()
    return [{"table": r.table_name, "doc": r.doc, "similarity": round(float(r.similarity), 3)}
            for r in rows]


TABLE_RE = re.compile(r"\b(sales|production|person|purchasing|humanresources)\.(\w+)")


def retrieval_recall(ks=(4, 6, 8, 10)) -> None:
    """For each benchmark question: are ALL tables used by its gold SQL in the top-k?"""
    from benchmark.questions import QUESTIONS
    needed = {q["id"]: {f"{s}.{t}" for s, t in TABLE_RE.findall(q["gold_sql"])} for q in QUESTIONS}
    ranked = {q["id"]: [r["table"] for r in retrieve(q["question"], k=max(ks))] for q in QUESTIONS}
    for k in ks:
        hits = sum(needed[i] <= set(ranked[i][:k]) for i in needed)
        print(f"Recall@{k:<2}: {hits}/{len(needed)} questions have ALL needed tables in the top {k}")
    k = TOP_K
    print(f"\nMisses at k={k} (needed table -> its rank, or 'not in top {max(ks)}'):")
    for q in QUESTIONS:
        missing = needed[q["id"]] - set(ranked[q["id"]][:k])
        if missing:
            where = {t: (ranked[q["id"]].index(t) + 1 if t in ranked[q["id"]] else "-") for t in missing}
            print(f"   {q['id']}: {where}   | {q['question']}")


if __name__ == "__main__":
    print(f"Indexed {index_schema()} table descriptions.\n")
    for qtext in ["How many employees were hired in each year?",
                  "What was the total purchasing spend (purchase orders) in each year?"]:
        print(qtext)
        for r in retrieve(qtext, k=4):
            print(f"   {r['similarity']:.3f}  {r['table']}")
    print()
    retrieval_recall()
