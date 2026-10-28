"""Build one text description per AdventureWorks table, generated from the
PostgreSQL catalog: columns + types, table/column comments, and foreign keys.
These descriptions are what gets embedded and retrieved for RAG.
"""
from collections import defaultdict

from sqlalchemy import text
from database import aw_engine

SCHEMAS = ["sales", "production", "person", "purchasing", "humanresources"]

TABLES_SQL = text("""
    SELECT table_schema, table_name,
           obj_description(format('%I.%I', table_schema, table_name)::regclass, 'pg_class') AS comment
    FROM information_schema.tables
    WHERE table_schema = ANY(:schemas) AND table_type = 'BASE TABLE'
    ORDER BY 1, 2
""")
COLUMNS_SQL = text("""
    SELECT table_schema, table_name, column_name, data_type,
           col_description(format('%I.%I', table_schema, table_name)::regclass, ordinal_position) AS comment
    FROM information_schema.columns
    WHERE table_schema = ANY(:schemas)
    ORDER BY table_schema, table_name, ordinal_position
""")
FKEYS_SQL = text("""
    SELECT conrelid::regclass::text AS tbl, pg_get_constraintdef(oid) AS def
    FROM pg_constraint
    WHERE contype = 'f' AND connamespace::regnamespace::text = ANY(:schemas)
""")


def build_docs(notes: dict | None = None, max_comment: int = 80) -> list:
    """Return [{'table': 'schema.table', 'doc': '...'}] for every table."""
    notes = notes or {}
    p = {"schemas": SCHEMAS}
    with aw_engine.connect() as c:
        tables = c.execute(TABLES_SQL, p).all()
        cols = c.execute(COLUMNS_SQL, p).all()
        fkeys = c.execute(FKEYS_SQL, p).all()

    cols_by = defaultdict(list)
    for r in cols:
        desc = f"{r.column_name} ({r.data_type})"
        if r.comment:
            desc += f" - {r.comment[:max_comment]}"
        cols_by[f"{r.table_schema}.{r.table_name}"].append(desc)

    joins_by = defaultdict(list)
    for r in fkeys:
        joins_by[r.tbl].append(r.def_.replace("FOREIGN KEY ", "").replace(" REFERENCES ", " -> ")
                               if hasattr(r, "def_") else r[1].replace("FOREIGN KEY ", "").replace(" REFERENCES ", " -> "))

    docs = []
    for t in tables:
        name = f"{t.table_schema}.{t.table_name}"
        parts = [f"Table: {name}"]
        if t.comment:
            parts.append(f"Description: {t.comment}")
        parts.append("Columns: " + "; ".join(cols_by[name]))
        if joins_by[name]:
            parts.append("Joins: " + "; ".join(joins_by[name]))
        if name in notes:
            parts.append("Notes: " + notes[name])
        docs.append({"table": name, "doc": "\n".join(parts)})
    return docs


if __name__ == "__main__":
    docs = build_docs()
    lengths = [len(d["doc"]) for d in docs]
    print(f"Tables documented: {len(docs)}")
    print(f"Doc length: avg {sum(lengths) // len(lengths)} chars, max {max(lengths)} chars")
    print(f"Tables with a description comment: {sum('Description:' in d['doc'] for d in docs)}")
    print(f"Tables with join info: {sum('Joins:' in d['doc'] for d in docs)}")
    for name in ("humanresources.employee", "sales.customer"):
        print("\n" + "-" * 70)
        print(next(d["doc"] for d in docs if d["table"] == name))
