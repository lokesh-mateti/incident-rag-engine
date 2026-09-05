# Incident Resolution RAG Engine

RAG-powered incident resolution engine for Cloud/Kubernetes operations. Ingests past incident reports, runbooks, and postmortems into a vector database, then answers operational queries with grounded, cited answers.

**Ask:** *"Pod CrashLoopBackOff in production — what did we do last time?"*
**Get:** A cited answer referencing past incidents, with prioritized remediation steps.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Incident RAG Engine                      │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │  Markdown     │    │  Loader +    │    │   ChromaDB        │  │
│  │  Incidents    │───▶│  Chunker     │───▶│   (Vector Store)  │  │
│  │  data/        │    │              │    │                   │  │
│  └──────────────┘    └──────────────┘    └────────┬──────────┘  │
│                                                   │              │
│  ┌──────────────┐    ┌──────────────┐    ┌────────▼──────────┐  │
│  │  User Query   │    │  RAG Chain   │    │  HuggingFace      │  │
│  │  (CLI / API)  │───▶│  (LangChain) │◀──▶│  Embeddings       │  │
│  └──────────────┘    └───────┬──────┘    │  (all-MiniLM-L6)  │  │
│                              │           └───────────────────┘  │
│                     ┌────────▼────────┐                         │
│                     │  LLM Provider   │                         │
│                     │  ┌────────────┐ │                         │
│                     │  │ OpenRouter │ │  ◀── default (free)     │
│                     │  │ Anthropic  │ │  ◀── direct Claude API  │
│                     │  └────────────┘ │                         │
│                     └─────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow:**
1. Markdown incident files are loaded, frontmatter metadata extracted (severity, service, cluster)
2. Documents are split into chunks (markdown-aware, with overlap) and embedded locally
3. Chunks are stored in ChromaDB with metadata preserved
4. On query: top-k similar chunks are retrieved, formatted as context, and sent to the LLM
5. The LLM generates a grounded answer citing source incident files

---

## Quick Start

### Prerequisites
- Python 3.11+
- An API key from [OpenRouter](https://openrouter.ai) (free, no credit card) **or** [Anthropic](https://console.anthropic.com)

### Setup

```bash
git clone https://github.com/lokesh-mateti/incident-rag-engine.git
cd incident-rag-engine

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env — add your OPENROUTER_API_KEY (or ANTHROPIC_API_KEY)
```

### Ingest incident data

```bash
rag-cli ingest-cmd
# Loaded 8 incident files.
# Ingested 42 chunks into ChromaDB.
```

### Query

```bash
# Single question
rag-cli ask "pod CrashLoopBackOff in production"

# Interactive REPL
rag-cli chat
```

### API server

```bash
uvicorn src.api.main:app --reload

# Ingest
curl -X POST http://localhost:8000/ingest

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "OOMKilled on ML pods — what should I check?"}'
```

### Docker

```bash
docker compose up --build            # Start API server
docker compose --profile setup up    # Run ingestion
```

---

## LLM Provider Configuration

Set `LLM_PROVIDER` in `.env`:

| Provider | Env Var | Default Model | Cost |
|----------|---------|---------------|------|
| `openrouter` | `OPENROUTER_API_KEY` | `nvidia/nemotron-3.5-lightning:free` | Free |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` | ~$0.002/query |

OpenRouter free models (no credit card needed): `nvidia/nemotron-3.5-lightning:free`, `meta-llama/llama-4-scout:free`, `deepseek/deepseek-chat-v3-0324:free`

---

## Project Structure

```
incident-rag-engine/
├── src/
│   ├── config.py                  # Pydantic settings (env vars)
│   ├── ingestion/
│   │   ├── loader.py              # Markdown loader + frontmatter extraction
│   │   └── chunker.py             # Recursive text splitting
│   ├── retrieval/
│   │   ├── vectorstore.py         # ChromaDB wrapper
│   │   └── chain.py               # RAG chain (retrieve + generate)
│   ├── api/
│   │   └── main.py                # FastAPI endpoints
│   └── cli/
│       └── main.py                # Typer CLI (ingest, ask, chat)
├── data/incidents/                 # Synthetic incident reports (8 K8s/AWS incidents)
├── tests/                          # Pytest suite
├── Dockerfile                      # Multi-stage production image
├── docker-compose.yml              # API + ingestion services
├── .github/workflows/ci.yml       # Lint → Test → Docker build
├── helm/incident-rag/             # Helm chart (K8s deployment)
└── pyproject.toml                  # Dependencies and tooling config
```

---

## Sample Incidents

The `data/incidents/` directory contains 8 synthetic but realistic incidents:

| ID | Title | Severity | Category |
|----|-------|----------|----------|
| INC-001 | CrashLoopBackOff — payment-service | SEV-1 | Config / DB |
| INC-002 | OOMKilled — recommendation-engine | SEV-2 | Resource limits |
| INC-003 | Node NotReady — disk pressure | SEV-2 | Node / storage |
| INC-004 | HPA thrashing — checkout-api | SEV-1 | Autoscaling |
| INC-005 | RDS Multi-AZ failover | SEV-1 | Database / AWS |
| INC-006 | CoreDNS failure — cluster-wide outage | SEV-1 | DNS / scheduling |
| INC-007 | Istio mTLS broke cross-namespace traffic | SEV-2 | Service mesh |
| INC-008 | Terraform state lock during incident | SEV-2 | IaC / process |

Each follows a consistent template: Detection → Root Cause → Timeline → Resolution → Remediation → Lessons Learned.

---

## Testing

```bash
pytest -v
```

Tests cover ingestion (loader, chunker, metadata extraction), vector store operations (ingest, search, reset), and API endpoints (health, validation, e2e ingest). No API key needed — LLM calls are not invoked in tests.

---

## Roadmap

- [x] Helm chart for K8s deployment
- [ ] Terraform module (ECS Fargate)
- [ ] Slack bot integration
- [ ] Streaming responses (SSE)
- [ ] Metadata filtering (by severity, service, date range)
- [ ] Evaluation harness (RAGAS)

---

## License

MIT
