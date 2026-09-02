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
