# Deploy to Production

Deploy the current branch to the production server via Coolify.

## How to use

```
/deploy [branch]
```

- `branch` — branch to deploy (default: `staging2`, which is what Coolify monitors)

---

## Instructions for the agent

You are deploying the Alpha Astrology Platform to production. Read `AGENTS.md` for full deployment details.

### Prerequisites

- All changes must be committed and pushed
- Production deploys from branch **`staging2`** via Coolify

### Steps

1. **Ensure both branches are in sync:**
```bash
git checkout staging2
git merge staging --no-edit
git push origin staging2
git checkout staging
git push origin staging
```

2. **Read SSH credentials from `.env`:**
```bash
PROD_SSH_PASS  # from .env
```

3. **Trigger Coolify deploy via API (on test server 64.226.83.59):**
```bash
sshpass -p "$PROD_SSH_PASS" ssh -o StrictHostKeyChecking=no root@64.226.83.59 "
curl -s -X POST 'http://localhost:8000/api/v1/deploy?uuid=rc40okc4wco0w4wco8kgs4o4&force=true' \
  -H 'Authorization: Bearer 9|deploy-now-token-2026'
"
```

The response contains a `deployment_uuid`. Save it.

4. **Poll deployment status** (takes 5–10 min):
```bash
sshpass -p "$PROD_SSH_PASS" ssh -o StrictHostKeyChecking=no root@64.226.83.59 "
curl -s 'http://localhost:8000/api/v1/deployments/<DEPLOYMENT_UUID>' \
  -H 'Authorization: Bearer 9|deploy-now-token-2026'
" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("Status:", d["status"])'
```

Poll every 60 seconds until status is `finished` or `failed`.

5. **Verify after deploy:**
```bash
sshpass -p "$PROD_SSH_PASS" ssh -o StrictHostKeyChecking=no root@142.93.143.116 '
APP=$(docker ps --format "{{.Names}}" | grep "^alpha-application")
echo "Container: $APP"
docker exec $APP python -c "
import django, os
os.environ.setdefault(\"DJANGO_SETTINGS_MODULE\", \"alpha.settings\")
django.setup()
print(\"Django OK\")
"
'
```

### Important

- **Never use `docker cp` + `kill -HUP`** — changes don't persist after container restart
- Coolify rebuilds Docker images from git, so code must be pushed first
- After deploy, run the analytics sync if analytics data is needed immediately:
```bash
docker exec $APP python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alpha.settings')
django.setup()
from analytics.tasks import sync_to_analytics_db
print(sync_to_analytics_db())
"
```
