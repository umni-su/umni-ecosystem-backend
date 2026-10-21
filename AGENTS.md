# AGENTS.md

Backend for the UMNI smart-home ecosystem. FastAPI + SQLModel + PostgreSQL, flat
module layout at the repo root (not a Python package). Russian is used in code
comments and docs.

## Running it

The real environment is `.venv` (**Python 3.11**). Bare `python` on PATH may be a
different interpreter with a completely different dependency set — this machine
has a system Python 3.13 with older `sqlalchemy`/`sqlmodel`, and `fastapi`/`uvicorn`
on PATH resolve there. Always call the venv explicitly:

```powershell
.\.venv\Scripts\python.exe -m compileall -q <dirs>
.\.venv\Scripts\python.exe main.py          # uvicorn on 0.0.0.0:8000
```

There is no lint, typecheck, formatter, or test runner configured for the repo as
a whole — no `pyproject.toml`, no ruff/mypy/flake8, no pytest in `requirements.txt`.
The only fast check is `compileall`. CI (`.github/workflows/docker-publish.yml`)
only builds and publishes Docker images on `v*` tags.

On this machine PowerShell blocks `npm.ps1`; use `npm.cmd` instead. Frontend is a
**separate repo**, `../umni-ecosystem-frontend` (Vue 3 + Vuetify + Vuex + Vite), not
a submodule. `npm.cmd run build` there is the compile check; there is no lint script.

## Importing `main` is not harmless

`main.py` runs work at import time, before the app object exists:

- `main.py:22` `Crypto.create_key()` writes `.ecosystem.key` (gitignored).
- `main.py:30-31` `configure_mappers()` and `MigrationManager.run_migrations()`.

So `import main` in a throwaway script opens a DB connection and may run migrations.
Import the specific module you need instead.

**Migrations run only when `APP_MODE=production`** (`database/migrations.py:35-40`);
anything else is skipped *silently*. The local `env_config/.env` ships with
`APP_MODE=production`, which is why startup appears to migrate. If you flip the mode
to `development`, tables stop being created and nothing tells you.

## Environment config

Settings come from `env_config/.env`, **not** `.env` (`config/settings.py:73-76`,
`case_sensitive=True`). `.env` is gitignored; `env_config/.env.template` is the
committed one. `API_ROOT=/api` becomes FastAPI's `root_path`, so routers declare
paths *without* the `/api` prefix even though the frontend calls `/api/...`.

## Database and migrations

- The SQLAlchemy URL is assembled in `config/settings.py:57-70` with an explicit
  `scheme="postgresql+psycopg2"`. SQLAlchemy 2.1 resolves a bare `postgresql://`
  to `PGDialect_psycopg` (psycopg3), which is not installed — the app then dies
  with `No module named 'psycopg'`. Do not drop the `+psycopg2` suffix.
- `database/migrations/env.py` takes the URL from `settings.database_url` directly
  (lines 122 and 162). `sqlalchemy.url` in `alembic.ini` is commented out. So the
  CLI works as-is and reads the same env file:

  ```powershell
  .\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe"
  .\.venv\Scripts\python.exe -m alembic upgrade head
  .\.venv\Scripts\python.exe -m alembic current
  ```

- Versions live in `database/migrations/versions/` and are named
  `YYYY_MM_DDHHMM-<rev>_<slug>.py`.
- **A new entity must be added to `database/entities_imports.py`** or
  `--autogenerate` will not see it. `env.py` imports that module precisely to
  register every model in `SQLModel.metadata`.

### SQLModel datetime fields

Since sqlmodel 0.0.48, annotating a field as `datetime` makes it a `UTCDateTime`
(`DateTime(timezone=True)`) and binding a naive value raises
`Datetime values must have timezone information`. Every timestamp column in this
database is `timestamp without time zone` **except** `logs.timestamp`
(`timestamptz`). So declare `sa_type=DateTime` on datetime table fields to get
naive columns. `entities/mixins/created_updated.py` `TimeStampMixin` covers
`created`/`updated` for every table — fix it there and all entities inherit.
`sqlmodel.NaiveDatetime` does **not** exist; it is a pydantic type, not re-exported.

## Routing

Routers are defined in `routes/` and registered in `main.py:80-100`. Starlette
matches in **registration order**, so a literal route must be declared above a
path-parameter route: `GET /cameras/{camera_id}` used to swallow
`GET /cameras/streams` and return 422. Check ordering before assuming a route is
broken.

## Auth

`classes/auth/auth.py`. Access token lifetime is `ACCESS_TOKEN_EXPIRE_MINUTES = 30`.

- `check_permission(...)` reads `Authorization: Bearer` via `OAuth2PasswordBearer`.
- `validate_token(...)` reads `?token=` from the query string; `check_permission_by_token`
  wraps it. The query form is what `<img>`-style requests would need, but
  `check_permission_by_token` is currently **unused** — the frontend fetches covers
  with a `fetch` + `Authorization` header and converts to a base64 data URL.
- Sliding refresh: `get_current_user` emits an `X-Refresh-Token` header when ≤ 1/5
  of the lifetime is left (the last 6 of 30 minutes). Nothing refreshes a token
  unless a request happens inside that window, which is why the frontend polls
  `GET /api/auth/check` every 5 minutes.

## WebRTC

Signalling is `services/cameras/webrtc/`; the socket is `WS /api/ws/webrtc?token=`.

- The socket is authenticated **once at the handshake** (`Auth.validate_ws_token`)
  and never re-checked, so it survives token expiry. Do not re-create the client on
  token rotation — `WebRtcClient.get()` deliberately reuses the singleton, otherwise
  the old socket is abandoned together with every live `RTCPeerConnection`.
- `routes/webrtc.py` closes all sessions for a camera on a new offer.
- `GET /cameras/streams` is the stream-state diagnostic endpoint; `PUT`/`DELETE`
  `/cameras/{id}/stream` start and stop a stream.

## Plugins

`plugins/core/` and `plugins/custom/`. Each subdirectory is a plugin exposing
`<name>_plugin.py` plus `<name>_config.json`; a starting point is in
`plugins/template/`. Discovery is by directory scan in
`services/plugins/plugins_service.py`.

- `plugins/custom/simple_timer/.venv` is a **vendored virtualenv** — exclude it from
  searches or you will get noise.
- `plugins/custom/tuya/tests/` holds the only tests in the repository, and pytest is
  not a declared dependency, so they are not part of any regular workflow.

## Translations

`l10n/` holds `ru` and `en` `LC_MESSAGES` with two domains, `messages` and `ui`.
Only `.po`/`.pot` are tracked; the compiled `.mo` are **gitignored**
(`.gitignore:14`), so a fresh clone has no working translations until you compile.
Recompile after editing any `.po`:

```bash
bash bin/scripts/compile-translations.sh          # both domains
pybabel compile -d l10n -D messages               # or one domain
pybabel extract -o l10n/templates/messages.pot .  # after adding _() strings
pybabel update -i l10n/templates/messages.pot -d l10n
```

`l10n/README.md` has the full Babel workflow.

## Deploy

The Docker image is `python:3.11-slim`, runs `uvicorn main:app` on 8000 and probes
`GET /health`, which also reports the stream registry state — keep that route
working or the container gets killed as unhealthy. Published from CI on `v*` tags
only. The Windows single-file build via Nuitka is documented in `README.md`.
