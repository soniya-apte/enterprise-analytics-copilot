import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load variables from the .env file in the project root
load_dotenv(dotenv_path="../.env")

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_HOST = "localhost"
ADVENTUREWORKS_DB = os.getenv("ADVENTUREWORKS_DB")

# Read-only credentials for the source data (defense-in-depth)
AW_RO_USER = os.getenv("AW_READONLY_USER")
AW_RO_PASSWORD = os.getenv("AW_READONLY_PASSWORD")

# Application database (our own tables: agent logs, evaluations, embeddings, etc.)
APP_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app_engine = create_engine(APP_DATABASE_URL)
AppSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)

# Source data database (AdventureWorks) — connected with a READ-ONLY role.
# This is a database-level guardrail: even if application-layer SQL validation
# were bypassed, Postgres itself will reject any write from this connection.
AW_DATABASE_URL = f"postgresql://{AW_RO_USER}:{AW_RO_PASSWORD}@{DB_HOST}:{DB_PORT}/{ADVENTUREWORKS_DB}"
aw_engine = create_engine(AW_DATABASE_URL)
AWSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=aw_engine)

# Backwards-compatible aliases
engine = app_engine
SessionLocal = AppSessionLocal
