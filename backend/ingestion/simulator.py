"""Time-series ingestion simulator (v2: channel-aware).

Replays AdventureWorks sales day by day into the app database, as if the data
were arriving live, and injects labeled anomalies (ground truth for evaluation).

Sales are split by channel:
  - online:   many small orders every day -> a continuous stream we monitor
  - reseller: few huge batch orders (only ~40 days in 3 years) -> stored, not monitored
Anomalies are injected only into the online channel.

Usage (run from backend/):
    python -m ingestion.simulator --days 7                   # ingest the next 7 days
    python -m ingestion.simulator --days 30 --all --detect   # replay everything, detecting per batch
    python -m ingestion.simulator --reset                    # wipe the stream and start over
"""
import argparse
import random
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import text
from database import app_engine, aw_engine

ANOMALY_RATE = 0.02        # about 2% of online rows that have sales get an anomaly
SEED = 42                  # change this to generate a different set of anomalies
CHANNELS = ["online", "reseller"]
INJECT_CHANNEL = "online"  # anomalies are injected into (and detected on) this channel only

TERRITORY_SQL = text('SELECT territoryid, name, "group" FROM sales.salesterritory ORDER BY territoryid')
RANGE_SQL = text("SELECT MIN(orderdate)::date, MAX(orderdate)::date FROM sales.salesorderheader")
DAILY_SQL = text("""
    SELECT soh.orderdate::date AS d, soh.territoryid AS tid,
           CASE WHEN soh.onlineorderflag THEN 'online' ELSE 'reseller' END AS ch,
           COUNT(*) AS orders, ROUND(SUM(soh.totaldue)::numeric, 2) AS revenue
    FROM sales.salesorderheader soh
    WHERE soh.orderdate::date BETWEEN :start AND :end
    GROUP BY 1, 2, 3
""")


def maybe_inject(d, tid, channel, revenue, orders):
    """Decide (reproducibly) whether this day x territory x channel gets an anomaly."""
    if channel != INJECT_CHANNEL:
        return revenue, orders, None
    rng = random.Random(f"{SEED}-{d.isoformat()}-{tid}")
    if revenue <= 0 or rng.random() >= ANOMALY_RATE:
        return revenue, orders, None
    kind = rng.choice(["spike", "drop", "outage"])
    if kind == "spike":
        new_rev = revenue * Decimal(str(round(rng.uniform(3, 5), 2)))
    elif kind == "drop":
        new_rev = revenue * Decimal(str(round(rng.uniform(0.05, 0.2), 2)))
    else:  # outage
        new_rev, orders = Decimal("0"), 0
    return new_rev.quantize(Decimal("0.01")), orders, kind


def reset():
    with app_engine.begin() as app:
        app.execute(text("TRUNCATE stream_daily_sales, injected_anomalies, detected_anomalies RESTART IDENTITY"))
        app.execute(text("UPDATE ingestion_state SET last_ingested_date = NULL, updated_at = now() WHERE id = 1"))
    print("Stream reset: all ingested data, ground truth and detections cleared, watermark empty.")


def ingest(days: int):
    # 1) Where did the last run stop?
    with app_engine.connect() as app:
        watermark = app.execute(text("SELECT last_ingested_date FROM ingestion_state WHERE id = 1")).scalar()

    # 2) Read the next batch from AdventureWorks (read-only connection)
    with aw_engine.connect() as aw:
        first_day, last_day = aw.execute(RANGE_SQL).one()
        start = first_day if watermark is None else watermark + timedelta(days=1)
        if start > last_day:
            print(f"Stream is fully caught up (last day {last_day}). Use --reset to replay again.")
            return None
        end = min(start + timedelta(days=days - 1), last_day)
        territories = aw.execute(TERRITORY_SQL).all()
        actual = {(r.d, r.tid, r.ch): (r.revenue, r.orders)
                  for r in aw.execute(DAILY_SQL, {"start": start, "end": end})}

    # 3) One row per day x territory x channel (zero-filled), injecting anomalies
    stream_rows, anomaly_rows = [], []
    d = start
    while d <= end:
        for tid, name, group in territories:
            for ch in CHANNELS:
                revenue, orders = actual.get((d, tid, ch), (Decimal("0.00"), 0))
                new_rev, new_orders, kind = maybe_inject(d, tid, ch, revenue, orders)
                stream_rows.append({"sale_date": d, "territory_id": tid, "channel": ch,
                                    "territory_name": name, "region_group": group,
                                    "order_count": new_orders, "revenue": new_rev})
                if kind:
                    anomaly_rows.append({"sale_date": d, "territory_id": tid, "channel": ch,
                                         "anomaly_type": kind, "original_revenue": revenue,
                                         "injected_revenue": new_rev})
        d += timedelta(days=1)

    # 4) Write everything in ONE transaction (all or nothing)
    with app_engine.begin() as app:
        app.execute(text("""
            INSERT INTO stream_daily_sales
                (sale_date, territory_id, channel, territory_name, region_group, order_count, revenue)
            VALUES (:sale_date, :territory_id, :channel, :territory_name, :region_group, :order_count, :revenue)
            ON CONFLICT (sale_date, territory_id, channel) DO NOTHING
        """), stream_rows)
        if anomaly_rows:
            app.execute(text("""
                INSERT INTO injected_anomalies
                    (sale_date, territory_id, channel, anomaly_type, original_revenue, injected_revenue)
                VALUES (:sale_date, :territory_id, :channel, :anomaly_type, :original_revenue, :injected_revenue)
            """), anomaly_rows)
        app.execute(text("UPDATE ingestion_state SET last_ingested_date = :end, updated_at = now() WHERE id = 1"),
                    {"end": end})

    n_days = (end - start).days + 1
    print(f"Ingested {start} -> {end}: {len(stream_rows)} rows "
          f"({n_days} days x {len(territories)} territories x {len(CHANNELS)} channels)")
    print(f"Anomalies injected this batch: {len(anomaly_rows)}")
    for a in anomaly_rows:
        print(f"   {a['sale_date']}  territory {a['territory_id']:>2}  {a['channel']:<8} {a['anomaly_type']:<7} "
              f"{a['original_revenue']} -> {a['injected_revenue']}")
    print(f"Watermark is now {end}")
    return start, end


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Replay AdventureWorks sales as a live stream.")
    p.add_argument("--days", type=int, default=7, help="how many days to ingest per batch")
    p.add_argument("--reset", action="store_true", help="clear the stream and start over")
    p.add_argument("--detect", action="store_true", help="run the anomaly detector on each new batch")
    p.add_argument("--all", action="store_true", help="keep ingesting batches until caught up")
    args = p.parse_args()
    if args.reset:
        reset()
    else:
        while True:
            batch = ingest(args.days)
            if batch and args.detect:
                from ingestion.detector import detect_range
                detect_range(*batch)
            if not (args.all and batch):
                break
