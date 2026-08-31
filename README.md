# Enterprise Analytics Copilot with Autonomous Data Scientist Agents

## Running the Database

Always start the database from the **project root** (not from inside `docker/`), so the `.env` file is picked up correctly:

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d
```

To stop it:

```bash
docker compose --env-file .env -f docker/docker-compose.yml down
```
