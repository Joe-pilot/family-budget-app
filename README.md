# Family Budget — self-hosted, Postgres + Ollama + K8s

Log expenses from Telegram or a web dashboard, in plain sentences —
*"spent 45 on groceries today"* — parsed locally by Ollama, stored in
Postgres, no cloud dependency once it's running.

```
Telegram / Web browser → telegram-bot / web (thin clients)
                             ↓
                        Budget API (FastAPI) — all business logic here
                             ↓                  ↓
                          Postgres            Ollama (local LLM parsing)
```

Everything routes through the one API. Telegram and the web UI are both
thin clients calling the same `/api/agent/log` endpoint — nothing talks to
Postgres or Ollama directly except the API.

---

## Two ways to run this

1. **`docker-compose`** — fastest way to try it on one machine, or to test
   changes before pushing to the cluster. Start here.
2. **`k8s/`** — the real deployment, for your OPNsense-fronted local cluster.

---

## 1. Try it locally with docker-compose

```bash
cp .env.example .env
# edit .env: paste your TELEGRAM_BOT_TOKEN from @BotFather

docker compose up -d --build
docker compose exec ollama ollama pull llama3.2:3b   # first run only, ~2GB

open http://localhost:8080        # web dashboard
```

Message your bot on Telegram, send `/whoami`, then:
```bash
# edit .env: ALLOWED_TELEGRAM_USER_IDS=<the id it gave you>
docker compose up -d   # picks up the new env var
```

Try `spent 45 on groceries today` in Telegram, or use the quick-add bar at
the top of the web dashboard — both hit the same endpoint, you'll see the
same row show up in both places.

---

## 2. Deploy to your K8s cluster

### What you need first

- A K8s cluster reachable from wherever you run `kubectl` (k3s, kubeadm,
  whatever you're running behind OPNsense)
- Docker images built and available to that cluster (see below — this is
  the one step that varies by cluster type)
- A Telegram bot token from `@BotFather`

### Build and load the images

Build all three:
```bash
docker build -t family-budget/api:latest ./api
docker build -t family-budget/web:latest ./web
docker build -t family-budget/telegram-bot:latest ./telegram-bot
```

Get them onto your cluster's nodes — how depends on what you're running:

| Cluster type | Command |
|---|---|
| k3s (single node, most common for this kind of setup) | `docker save family-budget/api:latest \| k3s ctr images import -` (repeat for web, telegram-bot) |
| kind | `kind load docker-image family-budget/api:latest` (repeat for web, telegram-bot) |
| minikube | `minikube image load family-budget/api:latest` (repeat for web, telegram-bot) |
| You run a local registry | `docker push` to it, then set each Deployment's `image:` to `your-registry/...` and `imagePullPolicy: Always` |

### Configure

```bash
cd k8s
cp 02-secrets.yaml 02-secrets.local.yaml   # keep the real one out of git
```
Edit `02-secrets.local.yaml`:
- `POSTGRES_PASSWORD` — pick a real password, update `DATABASE_URL` to match
- `TELEGRAM_BOT_TOKEN` — from BotFather
- leave `ALLOWED_TELEGRAM_USER_IDS` and `API_KEY` empty for now

Edit `01-configmap.yaml`:
- `WEB_API_BASE_URL` — the address your family's *browsers* will use to
  reach the API. With the NodePort setup below, that's
  `http://<any-node-ip>:30081`. Update it once you know your node's IP on
  the K8s VLAN (or your OPNsense DNS override — see the earlier networking
  discussion).

### Apply everything

```bash
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secrets.local.yaml
kubectl apply -f 10-postgres.yaml
kubectl apply -f 20-api.yaml
kubectl apply -f 30-web.yaml
kubectl apply -f 40-telegram-bot.yaml
kubectl apply -f 50-ollama.yaml

kubectl -n family-budget get pods -w   # watch until everything is Running
```

The last file also runs a one-time Job that pulls the Ollama model onto its
PVC — check progress with:
```bash
kubectl -n family-budget logs job/ollama-pull-model -f
```
This needs internet egress once (see the earlier OPNsense firewall rule);
after that, Ollama runs fully offline.

### First-run whitelist

```bash
# message your bot on Telegram: /whoami
# edit k8s/02-secrets.local.yaml: ALLOWED_TELEGRAM_USER_IDS=<id>,<id2>,...
kubectl apply -f 02-secrets.local.yaml
kubectl -n family-budget rollout restart deployment/telegram-bot
```

### Reach the web dashboard

With the NodePort manifests as given: `http://<any-node-ip>:30080`.
For a cleaner address, see the OPNsense DNS override / MetalLB notes from
the earlier networking discussion — swap `30-web.yaml`'s Service `type`
from `NodePort` to `LoadBalancer` once MetalLB is installed, and update
`WEB_API_BASE_URL` to match.

---

## Repo layout

```
api/              FastAPI backend — owns Postgres, the category catalog,
                  budget targets, and Ollama-based parsing. Everything
                  else is a thin client of this.
web/              Static SPA (vanilla JS + vendored Chart.js — zero
                  external CDN dependencies, works with no internet egress)
telegram-bot/     Long-polling bot, calls the API's /api/agent/log
k8s/              One manifest per concern, numbered in apply order
docker-compose.yml   Local dev/test — same topology as k8s/
```

## Extending the category list

The catalog lives in one place: `api/app/catalog.py`. Add a line, restart
the API — it seeds new categories into Postgres automatically (existing
rows are untouched, so your budget targets and transaction history are
safe). The web UI and Telegram bot both pull categories from the API, so
they never need separate updates.

## Day-to-day operations

- **Logs**: `kubectl -n family-budget logs -f deployment/budget-api` (swap
  the deployment name for web/telegram-bot/postgres/ollama)
- **New family member**: they DM the bot `/whoami`, you add their ID to
  `ALLOWED_TELEGRAM_USER_IDS` in the secret, `kubectl apply` +
  `rollout restart deployment/telegram-bot`
- **Change the model**: edit `OLLAMA_MODEL` in `01-configmap.yaml`,
  `kubectl apply`, then re-run `kubectl apply -f 50-ollama.yaml` to trigger
  a fresh pull job, then `kubectl rollout restart deployment/budget-api`
  (and telegram-bot) to pick up the new env var
- **Back up your data**: it's all in the `postgres-data` PVC — a normal
  `pg_dump` against the `postgres` pod is all you need; nothing else in the
  system holds state
