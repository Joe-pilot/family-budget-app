# Family Budget

A self-hosted family budgeting application with a web dashboard, Telegram input, and local natural-language transaction parsing.

Family Budget keeps financial data in your own PostgreSQL database. A FastAPI service contains the business logic, while the browser and Telegram bot act as clients. Ollama converts messages such as `spent 45 on groceries today` into structured transactions without requiring a hosted AI service.

> [!IMPORTANT]
> This project is designed for a trusted private network. It is not hardened for direct exposure to the public internet. See [Security](#security) before deploying it.

## Features

- Monthly budgets for income, expenses, and savings
- Transaction entry from a responsive web dashboard
- Natural-language entry through the dashboard or Telegram
- Monthly trends and category summaries
- Local inference with Ollama
- Docker Compose for a single host and Kubernetes manifests for a cluster
- No external JavaScript CDN dependency

## Architecture

```text
Web browser ───────┐
                   ├──▶ FastAPI ──▶ PostgreSQL
Telegram bot ──────┘       │
                           └──────▶ Ollama
```

Only the API communicates with PostgreSQL and Ollama. Both clients use the same API, so transactions and budget data stay consistent.

## Requirements

For the quickest local setup:

- Docker Engine with Docker Compose v2
- Approximately 4 GB of free memory and 3 GB of disk space for the default model and containers
- A Telegram bot token only if you want to use the Telegram client

For Kubernetes, you also need `kubectl`, a cluster, persistent-volume support, and a way to make locally built images available to cluster nodes.

## Quick start with Docker Compose

1. Create your local configuration:

   ```bash
   cp .env.example .env
   ```

2. Add a Telegram token to `.env`. If you do not want the Telegram client, start only the other services in step 3.

3. Build and start the application:

   ```bash
   docker compose up -d --build
   docker compose exec ollama ollama pull llama3.2:3b
   ```

   Without Telegram:

   ```bash
   docker compose up -d --build postgres ollama api web
   docker compose exec ollama ollama pull llama3.2:3b
   ```

4. Open <http://localhost:8080>. The interactive API documentation is at <http://localhost:8000/docs>.

To restrict Telegram access, send `/whoami` to your bot, copy the returned numeric ID into `ALLOWED_TELEGRAM_USER_IDS` in `.env`, and restart the bot:

```bash
docker compose up -d telegram-bot
```

Stop the stack with `docker compose down`. Add `--volumes` only when you also intend to permanently remove the local database and downloaded Ollama models.

## Configuration

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | API | SQLAlchemy PostgreSQL connection URL |
| `OLLAMA_HOST` | API | Ollama service URL |
| `OLLAMA_MODEL` | API | Model used to parse transaction text |
| `DEFAULT_CURRENCY` | API/web/bot | Currency label displayed to users |
| `TIMEZONE` | API | Application timezone |
| `API_KEY` | API/web/bot | Optional key required by write endpoints |
| `TELEGRAM_BOT_TOKEN` | Bot | Token issued by Telegram's BotFather |
| `ALLOWED_TELEGRAM_USER_IDS` | Bot | Optional comma-separated numeric allowlist |
| `API_BASE_URL` | Web/bot | Address used to reach the API |

The Compose file includes development defaults for the database. Change all credentials and set `API_KEY` before using the application outside an isolated local environment. Never commit `.env` or a populated Kubernetes Secret.

## Kubernetes deployment

Build the three project images:

```bash
docker build -t family-budget/api:latest ./api
docker build -t family-budget/web:latest ./web
docker build -t family-budget/telegram-bot:latest ./telegram-bot
```

Load or push the images using the method appropriate for your cluster, then update the image names in the deployment manifests if necessary.

Create a local Secret manifest and configure it:

```bash
cp k8s/02-secrets.example.yaml k8s/02-secrets.yaml
```

Replace every placeholder in `k8s/02-secrets.yaml`. Also set `WEB_API_BASE_URL` in `k8s/01-configmap.yaml` to an API URL reachable from your browsers. The cluster-internal API hostname will not work in a browser.

Apply the manifests in order:

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-secrets.yaml
kubectl apply -f k8s/10-postgres.yaml
kubectl apply -f k8s/20-api.yaml
kubectl apply -f k8s/30-web.yaml
kubectl apply -f k8s/40-telegram-bot.yaml
kubectl apply -f k8s/50-ollama.yaml
```

Watch the workloads and the one-time model download:

```bash
kubectl -n family-budget get pods -w
kubectl -n family-budget logs job/ollama-pull-model -f
```

The included services use NodePorts `30080` for the web interface and `30081` for the API. Restrict them to a trusted network or replace them with your own ingress and authentication setup.

## API overview

FastAPI publishes the complete interactive OpenAPI reference at `/docs`. Important routes include:

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/health` | Service health check |
| `GET` | `/api/categories` | List budget categories |
| `GET`, `POST` | `/api/transactions` | List or create transactions |
| `DELETE` | `/api/transactions/{id}` | Delete a transaction |
| `GET` | `/api/budget` | List budget targets |
| `PUT` | `/api/budget/{id}` | Update a budget target |
| `GET` | `/api/summary/monthly` | Return a year's monthly trend |
| `GET` | `/api/summary/month/{year}/{month}` | Return one month's details |
| `GET` | `/api/summary/categories` | Return year-to-date category totals |
| `POST` | `/api/agent/log` | Parse and store natural-language entries |

When `API_KEY` is configured, send it in the `X-API-Key` header on write requests. Read endpoints remain unauthenticated and should not be exposed to an untrusted network.

## Project layout

```text
api/             FastAPI backend, models, category catalog, and Ollama client
web/             Static browser application served by Nginx
telegram-bot/    Telegram long-polling client
k8s/             Kubernetes resources in deployment order
docker-compose.yml
```

The category catalog is defined in `api/app/catalog.py`. New entries are seeded when the API starts; existing transactions and budget values are retained.

## Operations

View logs:

```bash
docker compose logs -f api
# or
kubectl -n family-budget logs -f deployment/budget-api
```

Create a PostgreSQL backup from Compose:

```bash
docker compose exec -T postgres pg_dump -U budget budget > family-budget.sql
```

Keep backups encrypted and outside the repository because they contain private financial data. Test restoration regularly before relying on a backup process.

## Security

- Keep the application on a private network; do not publish its ports directly.
- Set a strong database password and a high-entropy `API_KEY`.
- Restrict Telegram with `ALLOWED_TELEGRAM_USER_IDS`.
- Store production secrets in a secret manager, SOPS, or Sealed Secrets rather than a plaintext manifest.
- Treat database dumps, logs, transaction exports, and screenshots as private.
- Review CORS, TLS, authentication, and network policies before supporting access from outside your trusted network.

If a secret is committed, removing it in a later commit is not sufficient. Revoke or rotate it immediately and clean it from Git history before publishing. See [SECURITY.md](SECURITY.md) for private vulnerability reporting guidance.

## Contributing

Issues and pull requests are welcome. Please avoid including real financial records, user IDs, tokens, internal hostnames, or screenshots with personal information in examples, tests, issues, and commit history.

Before opening a pull request, verify that the Python sources compile and the container configuration resolves:

```bash
python3 -m compileall -q api telegram-bot
docker compose config --quiet
```

## License

No open-source license has been selected yet. Until a license file is added, copyright law reserves reuse and redistribution rights to the copyright holder.
