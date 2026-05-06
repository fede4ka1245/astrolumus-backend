# AGENTS.md — Alpha Astrology Platform

Guidelines for AI agents working on this codebase.

---

## Project Overview

**Alpha** is a full-stack astrology platform. Core features: natal chart / horoscope generation, astrological calendar, user profiles & subscriptions, bootcamp courses, community forum, real-time chat, push notifications, multi-payment gateways.

**Repo**: Django REST API backend + React/Capacitor frontend (`alfa-frontend/`) + Next.js screenshot service (`app-preview-main/`).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 4.1, DRF 3.13, Python 3.11 |
| Database | PostgreSQL 14 |
| Cache / Broker | Redis |
| File storage | MinIO (S3-compatible) |
| WebSockets | Django Channels 4 + channels-redis |
| Task queue | Celery 5 + Celery Beat |
| Auth | JWT (simplejwt) + Session (admin) |
| Payments | BePaid, YooKassa, Stripe |
| Push | Firebase FCM |
| i18n platform | Tolgee (self-hosted REST API) |
| Frontend | React + TypeScript, Vite, Redux Toolkit, Capacitor, Electron |
| Preview service | Next.js 13, Prisma, Playwright |
| Error tracking | Sentry |
| Logging | Loguru |

---

## Repository Layout

```
alpha/              Django project config (settings, urls, asgi, celery)
users/              Auth, profiles, subscriptions
horoscope/          Horoscope generation & caching
payments/           BePaid / YooKassa / Stripe processing
bootcamp/           Course management
astrology_forum/    Community forum
astrology_calendar/ Calendar & planetary positions
deep_sky/           Deep-sky astrology features
chat/               Real-time messaging (Channels)
notifications_ext/  Push / email / in-app notifications
advertising/        Ad campaigns
info/               Static content, app info (Documents, AppPartInfo)
tariffs/            Subscription tiers & pricing
astroprocessor/     Astrological calculation engine
utils/              Shared utilities (tolgee_client, multilinguality, minio, tasks)
alfa-frontend/      React + Capacitor app (web / iOS / Android / Electron)
app-preview-main/   Next.js link-preview service
tests/              pytest test suite
```

Each Django app follows the standard layout: `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `filters.py`, `permissions.py`, `migrations/`.

---

## Common Commands

### Django
```bash
python manage.py migrate
python manage.py makemigrations
python manage.py collectstatic
python manage.py compilemessages   # compile .po files
python manage.py shell
```

### Testing
```bash
pytest                  # all tests (uses alpha.settings per pytest.ini)
pytest tests/ -v
```

### Celery
```bash
celery -A alpha worker -l info
celery -A alpha beat -l info
```

### Frontend (`alfa-frontend/`)
```bash
npm install
npm run dev             # Vite dev server
npm run build
npm run lint
npx cap sync            # sync Capacitor project
```

### Docker
```bash
make up                 # start dev stack
make down
make web-wsgi-rebuild   # rebuild Django container
make celery-rebuild     # rebuild Celery worker
```

---

## API Conventions

- **Versioning**: URL-based — `/api/v<int:version>/`. All current endpoints are v1.
- **Auth**: JWT (`Authorization: Bearer <token>`) for API; session auth for Django admin.
- **Pagination**: `LimitOffsetPagination`, default 10 items.
- **Filtering**: `DjangoFilterBackend` with per-app `FilterSet` classes.
- **Docs**: Swagger at `/swagger/`, ReDoc at `/redoc/`.
- ViewSets use DRF mixins explicitly; avoid adding router-level actions unless required.

### Typical ViewSet pattern
```python
class MyViewSet(mixins.ListModelMixin,
                mixins.RetrieveModelMixin,
                mixins.CreateModelMixin,
                GenericViewSet):
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = MyFilter
    pagination_class = LimitOffsetPagination
```

---

## Localization Architecture

The platform supports multiple languages (currently **ru** and **en**). Translations flow through three layers: **Admin Panel → Tolgee (i18n platform) → S3 (MinIO)**, and are served to the API from S3.

### Content types and their namespaces

| Content type | Tolgee namespace | Key format |
|---|---|---|
| Frontend UI strings | `frontend` | nested i18next keys |
| App-preview UI | `app-preview` | nested i18next keys |
| Tariffs | `tariffs` | `tariff.<pk>.<field>` |
| Documents | `documents` | `doc.<pk>.<field>` |
| App info (AppPartInfo) | `app_info` | `appinfo.<pk>.<field>` |
| Astroprocessor types/data | `astroprocessor_types`, `astroprocessor_data` | `type.<pk>.<field>` etc. |
| Deep sky objects | `constellations`, `stars`, `stellar_types`, `sky_info` | `const.<pk>.<field>` etc. |
| Backend static strings | `backend` | `app.model.field.verbose_name` |

Each namespace has its own **dedicated Tolgee project** (IDs in `settings.TOLGEE_PROJECTS`). Frontend/app-preview live in the main project (`settings.TOLGEE_PROJECT_ID`).

### Flow: Admin Panel → Tolgee → S3

```
Admin saves a model with localized fields (JSONField)
        │
        ▼
DB is updated (JSONField stores {"ru": "...", "en": "..."})
        │
        ▼
LocalizedModelAdmin.save_model() calls tolgee_client.upsert_key()
        │   namespace = self.tolgee_namespace (e.g. "tariffs")
        │   key = "{model_name}.{pk}.{field_name}"
        │   payload = {"ru": "...", "en": "..."}
        ▼
Tolgee REST API (TOLGEE_API_URL) stores the translation
        │
        ├─► sync_tolgee_to_s3.delay()  ← triggered immediately after save
        │
        └─► Celery Beat also runs sync_tolgee_to_s3 every 5 minutes (fallback)
                │
                ▼
        utils/tasks.py :: sync_tolgee_to_s3()
                │  calls tolgee_client.export_namespace() / export_namespace_nested()
                │  downloads ZIP from Tolgee export API
                │  uploads JSON files to MinIO bucket "alpha":
                │    alpha/translations/{namespace}/{lang}.json
                ▼
        S3 (MinIO) — source of truth for serving translations
```

### Flow: API serving translations to clients

```
API request (with ?lang=ru or Accept-Language header)
        │
        ▼
MultilingualityViewMixin._get_language_code()
  Priority: 1) ?language_code / ?lang param
            2) Accept-Language header
            3) user.language preference
            4) settings.DEFAULT_LANGUAGE_CODE
        │
        ▼
LocalizedFieldsSerializerMixin.get_localized_value()
        │
        ├─ if tolgee_namespace is set:
        │    utils/translation_loader.get_localized_value_from_s3()
        │      reads alpha/translations/{namespace}/{lang}.json from MinIO
        │      falls back to DEFAULT_LANGUAGE_CODE if translation missing
        │
        └─ fallback: reads directly from DB JSONField
```

### Key files

| File | Role |
|---|---|
| `utils/tolgee_client.py` | REST API wrapper for Tolgee (read/write/export/delete) |
| `utils/tasks.py` | `sync_tolgee_to_s3` Celery task |
| `utils/multilinguality.py` | `LocalizedModelAdmin`, `LocalizedFieldsSerializerMixin`, `MultilingualityViewMixin` |
| `utils/management/commands/import_dynamic_content_to_tolgee.py` | One-time bulk import of DB content → Tolgee |
| `utils/management/commands/import_backend_static_to_tolgee.py` | Import verbose_names / choices → Tolgee `backend` namespace |
| `utils/management/commands/import_frontend_to_tolgee.py` | Import frontend i18next files → Tolgee |

### Rules for adding localized content to a new model

1. Store translations as `models.JSONField(default=dict)` — format `{"ru": "...", "en": "..."}`.
2. In `admin.py`, subclass `LocalizedModelAdmin`, set `localized_fields` and `tolgee_namespace`.
3. In `serializers.py`, mix in `LocalizedFieldsSerializerMixin`, set `localized_fields` and `tolgee_namespace`.
4. In `views.py`, mix in `MultilingualityViewMixin` on the ViewSet.
5. Register the namespace in `utils/tasks.py :: PROJECTS` dict (use `"flat"` mode).
6. Add the namespace → project ID mapping to `settings.TOLGEE_PROJECTS`.
7. Run `python manage.py import_dynamic_content_to_tolgee` to seed existing data.

### Admin delete behaviour

`LocalizedModelAdmin.delete_model()` automatically removes all Tolgee keys for the deleted object via `delete_keys_by_prefix(namespace, "{model_name}.{pk}.")`.

### Translation cache

`utils/translation_loader` maintains an in-memory cache of S3 JSON files. After an admin save triggers `sync_tolgee_to_s3`, `invalidate_cache()` is called so the next request re-fetches from S3.

---

## Authentication & Permissions

- JWT tokens: 5-minute access tokens, 365-day refresh tokens.
- Custom `LastSeenMiddleware` updates `user.last_seen` on each authenticated request.
- WebSocket connections use a custom JWT middleware (`utils/channels_jwt_auth_middleware.py`) — standard DRF auth does not apply to Channels consumers.
- Typical permission classes per app: `IsAuthorOrIsAdminOrCreateReadOnly`, `IsAuthenticated`, `IsAdminUser`.

---

## File Storage

All uploads go to MinIO (S3-compatible), never to local disk.

- Public buckets listed in `settings.MINIO_PUBLIC_BUCKETS`.
- Signed URLs expire in 24 hours.
- Translation JSON files live in the `alpha` bucket under `alpha/translations/`.

---

## Async Tasks (Celery)

- Decorate tasks with `@shared_task`.
- Beat schedule is in `alpha/settings.py :: CELERY_BEAT_SCHEDULE`.
- Payment webhooks (BePaid, YooKassa, Stripe) are processed asynchronously.
- `sync_tolgee_to_s3` runs every 5 minutes via Beat, and is also triggered on-demand after admin saves.

---

## Real-time Chat

- Django Channels 4 with Redis channel layer.
- ASGI entry point: `alpha/asgi.py`.
- WebSocket URL routing is separate from REST routing.
- JWT auth middleware wraps the ASGI application; authenticate before accepting the connection.

---

## Environment Variables (key ones)

```
SECRET_KEY, DEBUG, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
REDIS_URL
MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_USE_HTTPS
MINIO_PUBLIC_BUCKETS
TOLGEE_API_URL, TOLGEE_API_KEY, TOLGEE_PROJECT_ID, TOLGEE_PROJECTS (JSON)
TOLGEE_TRANSLATIONS_S3_PREFIX
BEPAID_SHOP_ID, BEPAID_SECRET_KEY
YOOKASSA_ACCOUNT_ID, YOOKASSA_SECRET_KEY
EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
FCM_PROJECT_ID, FCM_PRIVATE_KEY, FCM_CLIENT_EMAIL
SENTRY_DSN, SENTRY_ENV
DOMAIN, BACKEND_URL, DEFAULT_LANGUAGE_CODE
```

---

## Testing

- Framework: **pytest-django** (`pytest.ini` points to `alpha.settings`).
- Fixtures: `tests/conftest.py` loads `tests/fixtures/users.json` at session scope.
- Standard fixtures: `admin_user`, `staff_user`, `authenticated_client`.
- Use `pytest-drf` helpers for API endpoint tests.
- Do not mock the database unless testing code that is explicitly database-agnostic.

---

## Deployment

Production is managed by **Coolify** (self-hosted PaaS) running on the test server (`64.226.83.59`).

### Key facts

| Setting | Value |
|---------|-------|
| Coolify dashboard | `http://64.226.83.59:8000` |
| Coolify deploys from branch | **`staging2`** |
| Production server | `142.93.143.116` |
| Application UUID | `rc40okc4wco0w4wco8kgs4o4` |
| Build type | Docker Compose (`docker-compose.yaml` at repo root) |

### How to deploy

Code is baked into Docker images. **`docker cp` + `kill -HUP` does NOT persist** — changes are lost on container restart. The only reliable deploy method:

1. Push code to **`staging2`** branch
2. Trigger Coolify deploy via API:

```bash
sshpass -p "$PROD_SSH_PASS" ssh -o StrictHostKeyChecking=no root@64.226.83.59 "
curl -s -X POST 'http://localhost:8000/api/v1/deploy?uuid=rc40okc4wco0w4wco8kgs4o4&force=true' \
  -H 'Authorization: Bearer 9|deploy-now-token-2026'
"
```

3. Monitor deployment status:

```bash
sshpass -p "$PROD_SSH_PASS" ssh -o StrictHostKeyChecking=no root@64.226.83.59 "
curl -s 'http://localhost:8000/api/v1/deployments/<deployment_uuid>' \
  -H 'Authorization: Bearer 9|deploy-now-token-2026' | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"status\"])'
"
```

4. Deploy typically takes **5–10 minutes** (Docker build + migrations + collectstatic)

### Always push to both branches

Keep `staging` and `staging2` in sync:
```bash
git checkout staging2 && git merge staging --no-edit && git push origin staging2
git checkout staging && git push origin staging
```

### Databases

| Name | Host (inside docker network) | Port (external) | Purpose |
|------|-----|------|---------|
| `postgres` (alpha) | `postgres:5432` | `5432` | Main application DB |
| `analytics-db` | `analytics-db:5432` | `5434` | Cold analytics DB (synced hourly) |
| `preview-db` | `preview-db:5432` | `5433` | Next.js preview app |

---

## Coding Conventions

- **Python**: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE_CASE for constants.
- **URLs**: kebab-case with trailing slash (`/api/v1/my-resource/`).
- **Models**: add `created_at` / `updated_at` via `TimeStampedModel` (model-utils) where relevant.
- **Serializers**: separate read/write serializers when field sets differ significantly.
- **Admin**: use `LocalizedModelAdmin` for any model with multilingual content.
- **CORS**: currently `CORS_ALLOW_ALL_ORIGINS = True` — do not widen this further; it is already tracked as a TODO.
- Two databases: main Django DB and a separate `preview-db` for the link-preview service. Keep migrations for each separate.
