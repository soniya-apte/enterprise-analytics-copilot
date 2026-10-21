"""Live-stream monitor: a deterministic summary of what the streaming detector flagged.

No LLM here - every number comes straight from the database. The Reporting
Agent interprets the result. "Recent" is measured from the stream's watermark
(the last ingested day), never from today's date.
"""
from datetime import timedelta

from sqlalchemy import text
from database import app_engine

DETECTOR_NOTE = (
    "Detector: rolling 28-day robust z-score on log(daily online revenue) per territory, "
    "no look-ahead. In evaluation against injected anomalies it was reliable only for changes "
    "of about x10 or more (59% recall at x10); smaller changes are often indistinguishable from "
    "normal day-to-day variation, and most individual flags are false alarms (precision about 8-13%). "
    "Treat flags as leads to investigate, not confirmed problems."
)
DATA_QUALITY_NOTE = (
    "Known data issue: the final month of source data (June 2025) is incomplete, so zero-revenue "
    "'outage' flags in June 2025 most likely reflect missing data rather than real outages."
)


def get_stream_anomalies(days: int = 30, limit: int = 15) -> dict:
    """Summarize detector flags over the last `days` days of the stream."""
    with app_engine.connect() as c:
        watermark = c.execute(text("SELECT last_ingested_date FROM ingestion_state WHERE id = 1")).scalar()
        if watermark is None:
            return {"available": False, "note": "The live stream is empty - nothing has been ingested yet."}
        start = watermark - timedelta(days=days - 1)
        params = {"s": start, "e": watermark}

        counts = c.execute(text("""
            SELECT detected_type, COUNT(*) FROM detected_anomalies
            WHERE sale_date BETWEEN :s AND :e GROUP BY 1
        """), params).all()

        rows = c.execute(text("""
            SELECT d.sale_date, s.territory_name, d.channel, d.detected_type,
                   d.revenue, d.baseline_median, d.score
            FROM detected_anomalies d
            JOIN stream_daily_sales s USING (sale_date, territory_id, channel)
            WHERE d.sale_date BETWEEN :s AND :e
            ORDER BY d.sale_date DESC, s.territory_name
            LIMIT :lim
        """), {**params, "lim": limit}).all()

        days_ingested = c.execute(text("SELECT COUNT(DISTINCT sale_date) FROM stream_daily_sales")).scalar()

    flags = [{
        "date": str(r.sale_date),
        "territory": r.territory_name,
        "channel": r.channel,
        "type": r.detected_type,
        "revenue": float(r.revenue),
        "normal_baseline": float(r.baseline_median) if r.baseline_median is not None else None,
        "score": float(r.score) if r.score is not None else None,
    } for r in rows]

    return {
        "available": True,
        "stream_up_to": str(watermark),
        "window": f"{start} to {watermark} (last {days} days of the stream)",
        "days_ingested_total": days_ingested,
        "flag_counts": {t: n for t, n in counts},
        "total_flags": sum(n for _, n in counts),
        "recent_flags": flags,
        "detector_note": DETECTOR_NOTE,
        "data_quality_note": DATA_QUALITY_NOTE,
    }
