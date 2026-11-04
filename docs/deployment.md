# Containerized local deployment

This setup provides a reproducible local stack for the FastAPI backend, MySQL,
and the Vite-built React frontend. It is not a production deployment recipe.

## Prerequisites

- Docker Engine with Compose v2
- A copy of `.env.example` saved as `.env`
- Non-placeholder values for `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, and a
  JWT secret of at least 32 characters

Compose passes `DATABASE_URL` independently; it does not URL-encode or derive
it from `MYSQL_PASSWORD`. Set both values consistently. The simplest safe
choice is a URL-safe MySQL password generated with Python:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use that same URL-safe value in `MYSQL_PASSWORD` and in `DATABASE_URL`:

```text
MYSQL_PASSWORD=generated-url-safe-value
DATABASE_URL=mysql+pymysql://tarim_app:generated-url-safe-value@db:3306/tarim_karar_analiz
```

If a password contains reserved URL characters such as `@`, `:`, or `#`, its
password component must be percent-encoded only in `DATABASE_URL` (`@` becomes
`%40`, for example), while `MYSQL_PASSWORD` retains the raw password.

The application uses the non-root MySQL user `tarim_app` by default. Do not use
the MySQL root account in `DATABASE_URL`.

## Start the stack

```bash
docker compose up --build
```

Open `http://localhost:8080`. The frontend passes `/api/...` requests through
Nginx to the backend, with the `/api` prefix removed before forwarding.

The backend does not call `create_all` at import time. Container startup runs
`alembic upgrade head` before starting Uvicorn, so the final schema comes from
the tracked migrations in `migrations/`.

The compose file deliberately does not mount SQL files into MySQL's automatic
init directory because the seed file has not been validated as an idempotent,
production-safe migration.

## Optional seed operation

After the backend healthcheck is green (which implies the database is healthy
and migrations have completed), run the explicit one-shot seed profile:

```bash
docker compose --profile seed run --rm seed
```

Review `database_seed.sql` before using this against any persistent database.
The command applies only `database_seed.sql`; it does not apply
`database_schema.sql`, because schema ownership belongs to Alembic. The seed
operation may not be safe to repeat.

## Verification

```bash
docker compose ps
curl http://localhost:8080/
```

For CI, the repository's GitHub Actions workflow runs Python 3.11 tests and a
frontend build. Frontend lint is reported but currently non-blocking because
the existing codebase has a known lint baseline that should be cleaned up in a
separate change. Tests are not copied into the backend image, so pytest is not
an image-runtime verification command; run it in the repository environment or
in CI instead.

`docker compose config` validates interpolation and structure only. Real
container startup and healthchecks require a running Docker daemon; they are
not verified by this configuration check.

