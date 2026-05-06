# Debug Server

Diagnose and debug issues on the **testing** or **production** server for the Alpha Astrology Platform.

## How to use

```
/debug-server [env] [issue description]
```

- `env` — `prod` or `test` (default: `test`)
- `issue description` — what seems to be broken (optional; agent will investigate if omitted)

---

## Instructions for the agent

You are debugging a live deployment of the **Alpha Astrology Platform**. Before doing anything, read `AGENTS.md` in the project root — it is the authoritative reference for the project's architecture, tech stack, service layout, localization flow, and conventions. All debugging should be informed by that document.

### 1. Load server credentials from `.env`

Read the project-root `.env` file and extract the relevant variables:

| Variable | Description |
|----------|-------------|
| `PROD_SSH_HOST` | Production server IP |
| `PROD_SSH_USER` | Production SSH user |
| `PROD_SSH_PASS` | Production SSH password |
| `TEST_SSH_HOST` | Testing server IP |
| `TEST_SSH_USER` | Testing SSH user |
| `TEST_SSH_PASS` | Testing SSH password |

**Never print or log credentials.** Use `sshpass` for non-interactive SSH:

```bash
# Test server
sshpass -p "$TEST_SSH_PASS" ssh -o StrictHostKeyChecking=no $TEST_SSH_USER@$TEST_SSH_HOST

# Production server
sshpass -p "$PROD_SSH_PASS" ssh -o StrictHostKeyChecking=no $PROD_SSH_USER@$PROD_SSH_HOST
```

Or set a shell alias for the session:
```bash
alias ssh-test='sshpass -p "$TEST_SSH_PASS" ssh -o StrictHostKeyChecking=no $TEST_SSH_USER@$TEST_SSH_HOST'
alias ssh-prod='sshpass -p "$PROD_SSH_PASS" ssh -o StrictHostKeyChecking=no $PROD_SSH_USER@$PROD_SSH_HOST'
```

### 2. Default to the test server

**Always reproduce and investigate on `test` first** unless the issue is confirmed prod-only or prod-specific data is required. Only connect to prod when explicitly asked or after test investigation is exhausted.

### 3. Understand the deployment layout

The project runs in Docker Compose. On both servers the stack lives at `/root/alpha` (or the path shown by `docker ps`). Key services:

| Container | Role |
|-----------|------|
| `app` / `web` | Django + Gunicorn (WSGI) |
| `celery` | Celery worker |
| `celery-beat` | Scheduled tasks (Tolgee→S3 sync every 5 min) |
| `postgres` | PostgreSQL 14 |
| `redis` | Cache + Celery broker |
| `minio` | S3-compatible file storage |
| `alfa-frontend` | React app |
| `app-preview` | Next.js link-preview service |

### 4. First-pass triage checklist

Run these on the target server to get a quick picture:

```bash
# 1. Container health
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 2. Recent errors in Django app
docker logs --tail=100 $(docker ps -qf name=web) 2>&1 | grep -E "ERROR|CRITICAL|Traceback|Exception"

# 3. Celery worker health
docker logs --tail=50 $(docker ps -qf name=celery) 2>&1

# 4. Check disk / memory
df -h && free -h

# 5. Recent nginx / proxy errors (if applicable)
journalctl -u nginx --since "1 hour ago" --no-pager 2>/dev/null || true
```

### 5. Django-specific debugging

```bash
# Run Django shell inside the app container
docker exec -it $(docker ps -qf name=web) python manage.py shell

# Check pending migrations
docker exec -it $(docker ps -qf name=web) python manage.py showmigrations | grep "\[ \]"

# View live app logs (follow)
docker logs -f $(docker ps -qf name=web)

# Check Celery task queue depth
docker exec -it $(docker ps -qf name=redis) redis-cli llen celery

# Django management commands
docker exec -it $(docker ps -qf name=web) python manage.py <command>
```

### 6. Database debugging

```bash
# Connect to PostgreSQL
docker exec -it $(docker ps -qf name=postgres) psql -U $DB_USER -d $DB_NAME

# Check slow / active queries
docker exec -it $(docker ps -qf name=postgres) psql -U $DB_USER -d $DB_NAME \
  -c "SELECT pid, now()-query_start AS duration, query FROM pg_stat_activity WHERE state='active' ORDER BY duration DESC LIMIT 10;"

# Check DB size
docker exec -it $(docker ps -qf name=postgres) psql -U $DB_USER -d $DB_NAME \
  -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));"
```

The DB credentials are in the container's `.env` / environment — read them with:
```bash
docker exec $(docker ps -qf name=web) env | grep DB_
```

### 7. Localization / Tolgee → S3 debugging

The localization pipeline is: **Admin Panel → Tolgee → S3** (see AGENTS.md §Localization Architecture for the full flow).

```bash
# Manually trigger Tolgee→S3 sync
docker exec -it $(docker ps -qf name=web) python manage.py shell -c \
  "from utils.tasks import sync_tolgee_to_s3; print(sync_tolgee_to_s3())"

# Check Celery Beat ran the scheduled sync
docker logs --tail=200 $(docker ps -qf name=celery-beat) 2>&1 | grep tolgee

# Check if translation files exist in MinIO
docker exec -it $(docker ps -qf name=web) python manage.py shell -c \
  "from utils.tasks import _get_minio_client; c=_get_minio_client(); [print(o.object_name) for o in c.list_objects('alpha', prefix='alpha/translations/', recursive=True)]"

# Invalidate translation cache manually
docker exec -it $(docker ps -qf name=web) python manage.py shell -c \
  "from utils.translation_loader import invalidate_cache; invalidate_cache(); print('cache cleared')"
```

### 8. Payment webhook debugging

Payments are processed async via Celery. Check:
```bash
# Recent payment task failures
docker logs --tail=200 $(docker ps -qf name=celery) 2>&1 | grep -E "(bepaid|yookassa|stripe|ERROR)"

# Check Flower (if running) for failed tasks
# Typically accessible at http://<server>:5555
```

### 9. Applying fixes

- **Never run `docker-compose down` on prod without confirming with the user.**
- For config/code changes, rebuild only the affected container:
  ```bash
  # Rebuild and restart app only
  docker-compose up -d --no-deps --build web

  # Run migrations after deploy
  docker exec -it $(docker ps -qf name=web) python manage.py migrate
  ```
- For hotfixes, prefer `docker exec` to run a management command or shell snippet over a full redeploy.
- After any fix, tail logs for 30 seconds to confirm no new errors:
  ```bash
  docker logs -f --since=0s $(docker ps -qf name=web) &
  sleep 30
  kill %1
  ```

### 10. Reporting findings

After investigation, report:
1. **Root cause** — what went wrong and why.
2. **Evidence** — specific log lines, error messages, query results.
3. **Fix applied** (if any) — exact commands run.
4. **Recommended follow-up** — migrations, config changes, code fixes to make in the repo.

If a code fix is needed, make it in the local repo following AGENTS.md conventions, not directly on the server.
