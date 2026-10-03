# Data Setup: AdventureWorks

The primary enterprise dataset is Microsoft's **AdventureWorks** (OLTP), ported to PostgreSQL.
It contains 68 tables across 5 schemas (person, humanresources, production, purchasing, sales),
representing a fictional bicycle-parts wholesaler (~20k customers, ~500 products, ~31k sales orders).

## Source
- Loader scripts: https://github.com/lorint/AdventureWorks-for-Postgres
- Raw CSV data: https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks-oltp-install-script.zip

## Load Steps (reproducible)
1. Clone loader into a scratch folder (outside this repo):
   `git clone https://github.com/lorint/AdventureWorks-for-Postgres.git`
2. Download and unzip the Microsoft CSV data into that folder.
3. Preprocess CSVs for Postgres: `ruby update_csvs.rb`
4. Ensure the project's Postgres container is running (see main README).
5. Create the database:
   `PGPASSWORD=<pw> psql -h localhost -p 5433 -U copilot_user -d analytics_copilot -c 'CREATE DATABASE "Adventureworks";'`
6. Load all tables:
   `PGPASSWORD=<pw> psql -h localhost -p 5433 -U copilot_user -d Adventureworks < install.sql`

## Verification
- `\dt (humanresources|person|production|purchasing|sales).*` should list 68 tables.
- Sample query: revenue by year from `sales.salesorderheader`.

## Notes
- Raw data files are intentionally NOT committed to this repo (large, freely downloadable).
- AdventureWorks lives in its own `Adventureworks` database, kept separate from the
  `analytics_copilot` application database (raw/source layer vs. application layer).

## Read-Only Role (Defense-in-Depth Security)

The Data Agent connects to AdventureWorks using a read-only PostgreSQL role, so that
even if application-layer SQL validation were bypassed, the database itself rejects writes.

To create the role (run once, as the main user, against the Adventureworks DB):

```sql
CREATE ROLE copilot_readonly WITH LOGIN PASSWORD '<readonly-password>';
GRANT CONNECT ON DATABASE "Adventureworks" TO copilot_readonly;
GRANT USAGE ON SCHEMA sales, production, person, purchasing, humanresources TO copilot_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA sales, production, person, purchasing, humanresources TO copilot_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA sales, production, person, purchasing, humanresources GRANT SELECT ON TABLES TO copilot_readonly;
```

The credentials are stored in `.env` as `AW_READONLY_USER` / `AW_READONLY_PASSWORD`,
and `database.py` uses them for the AdventureWorks (`aw_engine`) connection.
