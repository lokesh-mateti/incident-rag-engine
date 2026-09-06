# Demo Guide — Incident Resolution RAG Engine

A complete walkthrough to set up, run, and understand this project from scratch. No prior setup required.

---

## 1. The Problem

SRE and platform teams handle hundreds of incidents over time. When a new incident occurs at 3 AM, the on-call engineer asks: *"Have we seen this before? What did we do last time?"*

Today, that knowledge lives in scattered Jira tickets, Confluence pages, Slack threads, and postmortem docs. Finding the right one under pressure is slow and error-prone.

**This project solves that.** It ingests past incident reports into a vector database and answers operational queries with grounded, cited answers — instantly.

---

## 2. Architecture Overview

```
Incident Files (.md)
       │
       ▼
  ┌─────────┐     ┌──────────┐     ┌───────────┐
  │ Loader   │────▶│ Chunker  │────▶│ ChromaDB  │
  │ Extract  │     │ Split on │     │ Embed +   │
  │ metadata │     │ ## headers│    │ Store     │
  └─────────┘     └──────────┘     └─────┬─────┘
                                         │
  User Query ──▶ Embed Query ──▶ Similarity Search
                                         │
                                    Top-k chunks
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │ LLM (Claude/ │
                                  │ OpenRouter)  │
                                  └──────┬──────┘
                                         │
                                   Cited Answer
```

### Key Components

| Component | Tech | Purpose |
|-----------|------|---------|
| **Loader** | Python, LangChain | Reads .md files, extracts frontmatter metadata (severity, service, cluster) |
| **Chunker** | LangChain RecursiveCharacterTextSplitter | Splits documents into ~1000 char chunks on markdown headers, preserving metadata |
| **Embedding Model** | all-MiniLM-L6-v2 (HuggingFace) | Converts text into 384-dimension vectors that capture semantic meaning, runs locally on CPU |
| **Vector Store** | ChromaDB | Stores vectors + text + metadata on disk, performs cosine similarity search |
| **RAG Chain** | LangChain | Retrieves relevant chunks, formats them as context, sends to LLM |
| **LLM** | OpenRouter (free) or Anthropic Claude | Generates grounded, cited answers from retrieved context |
| **API** | FastAPI + Uvicorn | REST endpoints: POST /ingest, POST /query, GET /health |
| **CLI** | Typer + Rich | Terminal interface: ingest, ask, chat (interactive REPL) |

### What is RAG?

**Retrieval-Augmented Generation** — instead of asking an LLM to answer from memory (which hallucinates), we first *retrieve* relevant documents from a database, then pass them as context to the LLM. The LLM generates an answer grounded in real data, with citations.

### What is a Vector?

A vector is a list of numbers (e.g., 384 floating-point numbers) that represents the *meaning* of a text. Texts with similar meanings produce similar vectors. This lets us find relevant documents by comparing vectors mathematically (cosine similarity) rather than keyword matching.

Example:
- "pod CrashLoopBackOff" → [0.067, 0.012, 0.066, ...] (384 numbers)
- "container restart loop" → [0.065, 0.015, 0.061, ...] (similar numbers — similar meaning!)
- "terraform state lock" → [-0.034, 0.091, -0.012, ...] (different numbers — different meaning)

### What is an Embedding Model?

An embedding model (like all-MiniLM-L6-v2) is a neural network that converts text into vectors. It's different from an LLM:

| | LLM (Gemma, Claude) | Embedding Model (MiniLM) |
|---|---|---|
| **Input** | Text | Text |
| **Output** | More text (answers) | A list of numbers (vector) |
| **Job** | Generate human-like responses | Capture the *meaning* of text as numbers |
| **Size** | Huge (billions of params) | Small (22M params) |
| **Runs** | Remote API (OpenRouter) | Locally on your laptop CPU |

---

## 3. Prerequisites

### 3a. Operating System

This guide uses Linux (Ubuntu/WSL). macOS works the same way. Windows users should use WSL (Windows Subsystem for Linux).

**Install WSL on Windows (if needed):**
```bash
# Run in PowerShell as Administrator
wsl --install
# Restart your computer, then open "Ubuntu" from Start menu
```

### 3b. Python 3.11+

Check if Python is installed:
```bash
python3 --version
```

If not installed or version is below 3.11:
```bash
# Ubuntu/WSL
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

### 3c. Git

Check if Git is installed:
```bash
git --version
```

If not installed:
```bash
# Ubuntu/WSL
sudo apt install git -y

# Configure git (use your details)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 3d. OpenRouter API Key (free, no credit card)

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up with Google or email (no credit card needed)
3. Go to **Keys** → **Create Key**
4. Copy the key (starts with `sk-or-v1-...`)
5. Save it somewhere — you'll need it in Step 5

---

## 4. Clone and Install

### 4a. Clone the Repository

```bash
cd ~
git clone https://github.com/lokesh-mateti/incident-rag-engine.git
cd incident-rag-engine
```

### 4b. Create a Virtual Environment

A virtual environment isolates this project's dependencies from your system Python:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Your terminal prompt should now show `(.venv)` at the beginning. You need to run `source .venv/bin/activate` every time you open a new terminal to work on this project.

### 4c. Install CPU-only PyTorch First

PyTorch is a large dependency. Install the CPU-only version to avoid downloading 1.5GB of GPU libraries you don't need:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu --timeout 120
```

This downloads ~196MB. Wait for it to finish.

### 4d. Install Project Dependencies

```bash
pip install -e ".[dev]" --timeout 120 --retries 5
```

This reads `pyproject.toml` and installs everything: LangChain, ChromaDB, FastAPI, sentence-transformers, etc. Takes a few minutes depending on your internet speed.

**What does `-e ".[dev]"` mean?**
- `-e .` — install this project in "editable" mode (reads pyproject.toml)
- `[dev]` — also install dev extras (pytest, ruff, mypy)

### 4e. Verify Installation

```bash
python3 -c "import langchain; import chromadb; import fastapi; print('All imports OK')"
```

Expected output: `All imports OK`

---

## 5. Configure Environment

### 5a. Create .env File

```bash
cp .env.example .env
```

### 5b. Add Your API Key

Open .env in a text editor:
```bash
nano .env
```

Find the line:
```
OPENROUTER_API_KEY=sk-or-v1-...
```

Replace `sk-or-v1-...` with your actual OpenRouter API key from Step 3d.

Save and exit: `Ctrl+O` → `Enter` → `Ctrl+X`

### 5c. Verify Configuration

```bash
grep OPENROUTER_API_KEY .env
```

You should see your actual key (starting with `sk-or-v1-`).

### 5d. Understanding the .env File

```
LLM_PROVIDER=openrouter              ← Which LLM service to use
OPENROUTER_API_KEY=sk-or-v1-...      ← Your API key
OPENROUTER_BASE_URL=https://...      ← OpenRouter API endpoint
OPENROUTER_MODEL=nvidia/nemotron-3.5-lightning:free  ← Free model, no cost
CHROMA_PERSIST_DIR=./chroma_data     ← Where vectors are stored on disk
EMBEDDING_MODEL=all-MiniLM-L6-v2    ← Local embedding model (runs on CPU)
INCIDENT_DATA_DIR=./data/incidents   ← Where incident markdown files live
CHUNK_SIZE=1000                      ← Max characters per chunk
CHUNK_OVERLAP=200                    ← Overlap between chunks for context
```

---

## 6. Explore the Incident Data

Before ingesting, look at what we're working with:

### 6a. List All Incident Files

```bash
ls data/incidents/
```

Output:
```
inc-001-crashloopbackoff.md   inc-004-hpa-thrashing.md      inc-007-istio-mtls.md
inc-002-oomkilled.md          inc-005-rds-failover.md       inc-008-terraform-state-lock.md
inc-003-node-pressure.md      inc-006-coredns-failure.md
```

### 6b. Read One Incident

```bash
cat data/incidents/inc-001-crashloopbackoff.md
```

Notice the structure:
- **Frontmatter** at the top (id, title, severity, service, cluster, date)
- **Body** follows a consistent template: Detection → Root Cause → Timeline → Resolution → Remediation → Lessons Learned

All 8 incidents are synthetic but realistic K8s/AWS scenarios:

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

---

## 7. Ingest Incident Data

This step loads the markdown files, splits them into chunks, converts each chunk into a 384-dimension vector using the local embedding model, and stores everything in ChromaDB.

```bash
python -m src.cli.main ingest-cmd
```

Expected output:
```
Loaded 8 incident files.
Ingested 20 chunks into ChromaDB.
```

The first run downloads the embedding model (~90MB). Subsequent runs are instant.

### What Just Happened?

```
8 markdown files
       │
       ▼ loader.py (extract frontmatter metadata)
8 LangChain Documents
       │
       ▼ chunker.py (split on ## headers, ~1000 chars each)
20 chunks (each carries parent metadata)
       │
       ▼ vectorstore.py → ChromaDB.add_documents()
       │    For each chunk:
       │    1. Text → all-MiniLM-L6-v2 → [384 numbers]
       │    2. Store vector + text + metadata on disk
       │
  ./chroma_data/ (your vector database)
```

### Verify the Vector Database

```bash
ls -la chroma_data/
```

You should see `chroma.sqlite3` (metadata/text) and a UUID directory (vector index).

---

## 8. Query — CLI

### 8a. Single Question

```bash
python -m src.cli.main ask "pod CrashLoopBackOff in production"
```

This will:
1. Embed your question into a 384-dimension vector (same model as ingestion)
2. Find the 5 most similar chunks in ChromaDB via cosine similarity
3. Format those chunks as context in a prompt
4. Send the prompt to the LLM (OpenRouter)
5. Return a grounded, cited answer

### 8b. Try More Queries

```bash
python -m src.cli.main ask "OOMKilled on ML pods — what should I check?"
python -m src.cli.main ask "DNS resolution failing across the cluster"
python -m src.cli.main ask "how do we handle RDS failover?"
python -m src.cli.main ask "HPA scaling issues causing 5xx errors"
python -m src.cli.main ask "Istio mTLS breaking cross-namespace calls"
```

### 8c. Interactive Chat Mode

```bash
python -m src.cli.main chat
```

Type queries interactively. Type `exit` to quit.

---

## 9. Inspect Vectors and Similarity Scores

### 9a. See Real Similarity Scores

```bash
python3 -c "
from src.retrieval.vectorstore import get_vectorstore
store = get_vectorstore()
results = store.similarity_search_with_relevance_scores('pod CrashLoopBackOff in production', k=5)
for doc, score in results:
    print(f'{score:.4f}  {doc.metadata[\"source\"]}')
"
```

Output shows ranked results with scores:
```
0.3478  inc-001-crashloopbackoff.md   ← most relevant
0.2848  inc-002-oomkilled.md          ← related (pod restarts)
0.2740  inc-003-node-pressure.md      ← somewhat related
0.2007  inc-006-coredns-failure.md    ← less related
0.1935  inc-004-hpa-thrashing.md      ← least related
```

### 9b. See an Actual Vector

```bash
python3 -c "
from langchain_huggingface import HuggingFaceEmbeddings
model = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')
v = model.embed_query('pod CrashLoopBackOff in production')
print(f'Input: \"pod CrashLoopBackOff in production\"')
print(f'Vector length: {len(v)} dimensions')
print(f'First 10 numbers: {[round(x, 4) for x in v[:10]]}')
"
```

This shows the actual 384 floating-point numbers that represent the meaning of that text.

### 9c. Compare Two Vectors (Cosine Similarity)

```bash
python3 -c "
from langchain_huggingface import HuggingFaceEmbeddings
import numpy as np

model = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')

v1 = model.embed_query('pod CrashLoopBackOff in production')
v2 = model.embed_query('PagerDuty alert fired. All 6 replicas entered CrashLoopBackOff')
v3 = model.embed_query('Terraform state lock blocked infra changes')

def cosine_sim(a, b):
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

print(f'Query vs CrashLoopBackOff chunk: {cosine_sim(v1, v2):.4f}  ← similar meaning')
print(f'Query vs Terraform chunk:        {cosine_sim(v1, v3):.4f}  ← different meaning')
"
```

This demonstrates why vector search works — similar texts produce higher scores.

### 9d. See How Documents Are Chunked

```bash
python3 -c "
from src.ingestion.loader import load_incidents
from src.ingestion.chunker import chunk_documents

docs = load_incidents()
chunks = chunk_documents(docs)
print(f'{len(docs)} files → {len(chunks)} chunks\n')
for c in chunks:
    print(f'{c.metadata[\"source\"]:40s}  {len(c.page_content):5d} chars')
"
```

---

## 10. API Server

The same RAG pipeline is also exposed as a REST API via FastAPI.

### 10a. Start the Server

Open a terminal:
```bash
cd ~/incident-rag-engine
source .venv/bin/activate
ANONYMIZED_TELEMETRY=False uvicorn src.api.main:app --reload
```

The server starts at `http://localhost:8000`. You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 10b. Test Endpoints (in a second terminal)

Open another terminal:

**Health check:**
```bash
curl http://localhost:8000/health
```

Output: `{"status":"ok"}`

**Ingest data via API:**
```bash
curl -X POST http://localhost:8000/ingest
```

**Query via API:**
```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "pod CrashLoopBackOff in production"}' | python3 -m json.tool
```

This returns JSON with the answer and source documents.

**Interactive API docs (Swagger UI):**

Open in browser: `http://localhost:8000/docs`

This is auto-generated by FastAPI — you can test endpoints interactively from the browser.

### 10c. Stop the Server

Press `Ctrl+C` in the terminal running uvicorn.

### 10d. What is Uvicorn?

Uvicorn is a lightweight ASGI web server for Python. FastAPI defines the routes and logic, but can't serve traffic by itself. Uvicorn listens on port 8000, receives HTTP requests, and hands them to FastAPI for processing.

### 10e. Request Flow

```
curl POST /query
       │
       ▼
   Uvicorn (port 8000) → receives HTTP request
       │
       ▼
   FastAPI (src/api/main.py) → routes to query_incidents()
       │
       ▼
   chain.query() → retrieves chunks from ChromaDB
       │              → formats context
       │              → calls OpenRouter LLM
       │              → returns cited answer
       ▼
   JSON response → back to curl
```

---

## 11. Run Tests

```bash
ANONYMIZED_TELEMETRY=False pytest -v
```

Expected output: `17 passed`

Tests cover:
- **Ingestion:** loader reads files correctly, extracts metadata, chunker splits properly
- **Retrieval:** ChromaDB ingest/search/reset, chain prompt structure, empty-store edge case
- **API:** health endpoint, input validation, end-to-end ingest

No API key needed — tests don't call the LLM.

---

## 12. Docker (Optional)

If you have Docker Desktop installed:

### 12a. Build and Run

```bash
docker compose up --build
```

### 12b. Ingest via Docker

```bash
docker compose --profile setup up
```

### 12c. Query via Docker

```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "pod CrashLoopBackOff in production"}' | python3 -m json.tool
```

### 12d. Stop

```bash
docker compose down
```

---

## 13. Code Walkthrough

### Key files to understand, in order:

**`src/config.py`** — Centralized config using pydantic-settings. All environment variables defined in one place. The `LLMProvider` enum controls whether we use OpenRouter or direct Anthropic API. Pydantic validates types and reads `.env` automatically.

**`src/ingestion/loader.py`** — Reads markdown files from `data/incidents/`. The `_parse_frontmatter()` function extracts metadata (id, severity, service, cluster) from the top of each file. Each file becomes a LangChain `Document` with `.page_content` (body text) and `.metadata` (extracted fields + source filename).

**`src/ingestion/chunker.py`** — Splits documents into retrieval-sized pieces using `RecursiveCharacterTextSplitter`. The separators list `["\n## ", "\n### ", "\n\n", "\n", " "]` means it splits on markdown headers first, then paragraphs, then lines, then words — preserving semantic boundaries. Each chunk inherits the parent document's metadata so we can cite the source file after retrieval.

**`src/retrieval/vectorstore.py`** — Wraps ChromaDB. The key line is the `Chroma()` constructor that passes `embedding_function=HuggingFaceEmbeddings(...)` — this tells ChromaDB to use our local embedding model. When `add_documents()` is called, ChromaDB internally embeds each chunk and stores the vector + text + metadata. When `similarity_search()` is called, ChromaDB embeds the query and finds the nearest vectors.

**`src/retrieval/chain.py`** — The RAG chain that ties everything together. `_build_llm()` creates the right LangChain chat model based on the provider config. `query()` is the complete pipeline in 10 lines: retrieve → format context → build prompt → call LLM → return result. The system prompt enforces citation behavior and flags destructive actions.

**`src/api/main.py`** — FastAPI application with three endpoints: `GET /health`, `POST /ingest`, `POST /query`. Pydantic models (`QueryRequest`, `QueryResponse`) validate input and serialize output. The API layer is thin — it just calls the same functions the CLI uses.

**`src/cli/main.py`** — Typer CLI with three commands: `ingest-cmd` (load and embed incidents), `ask` (single query), `chat` (interactive REPL). Uses Rich for formatted terminal output.

---

## 14. Infrastructure & DevOps Artifacts

### Dockerfile
- Multi-stage build: dependencies cached in separate layer for faster rebuilds
- Pre-downloads the embedding model so first request isn't slow
- Runs uvicorn on port 8000

### docker-compose.yml
- `app` service with health check
- `ingest` one-shot service under `setup` profile
- Shared named volume for ChromaDB persistence across restarts

### Helm Chart (`helm/incident-rag/`)
- Full K8s deployment: Deployment, Service, ConfigMap, PVC, Ingress, HPA
- API keys stored in K8s Secret (not in the chart — security best practice)
- ConfigMap checksum in pod annotations triggers rollout on config change
- HPA with 300s scale-down stabilization window (inspired by INC-004 in our own data!)
- PVC for ChromaDB persistence

### GitHub Actions CI (`.github/workflows/ci.yml`)
- Three-stage pipeline: Lint (ruff) → Test (pytest) → Docker build
- Runs on every push to main and every PR
- Docker build uses GitHub Actions cache for faster builds

---

## 15. Design Decisions

| Decision | Why |
|----------|-----|
| **Local embeddings** (all-MiniLM-L6-v2) | No extra API key, no cost, runs on CPU. Good enough for incident reports. |
| **ChromaDB** (not Pinecone/Weaviate) | Zero infrastructure, persists to disk. Swap to managed DB for production. |
| **OpenRouter** (not direct OpenAI/Anthropic) | Free tier available, provider-agnostic, one API key for 380+ models. |
| **Metadata in frontmatter** (not YAML) | Simple, human-readable, easy to parse without heavy YAML dependency. |
| **LangChain** (not raw API calls) | Composable chains, built-in text splitters, easy provider switching. |
| **Typer CLI** (not argparse) | Auto-generated help, type hints, Rich integration for pretty output. |
| **Pydantic settings** | Single source of truth for config, validates types, reads .env automatically. |
| **Provider-agnostic LLM** | One env var switches between OpenRouter and Anthropic. Shows extensible design. |
| **CPU-only PyTorch** | Embedding model runs fine on CPU. No GPU needed, saves 1.3GB download. |

---

## 16. How to Scale for Production

| Layer | This Project | Production |
|-------|-------------|------------|
| Source data | 8 markdown files | Jira, PagerDuty, Confluence, Slack — thousands of incidents pulled via APIs |
| Ingestion | Manual `ingest-cmd` | Scheduled pipeline (Airflow/Dagster) pulling new incidents daily |
| Chunking | Simple text split | Semantic chunking, section-aware parsers |
| Embedding model | all-MiniLM-L6-v2 (local, free) | OpenAI text-embedding-3-large or fine-tuned domain model |
| Vector DB | ChromaDB (local files) | Pinecone, Weaviate, pgvector — managed, distributed |
| Metadata filtering | None | Filter by severity, date range, service, cluster before similarity search |
| Updates | Drop and re-ingest | Incremental upserts, versioned embeddings |
| Interface | CLI + REST API | Slack bot, web dashboard, PagerDuty integration |

---

## 17. Frequently Asked Questions

**Q: Why not just use keyword search?**
A: Keyword search fails on semantic similarity. "container restart loop" wouldn't match "CrashLoopBackOff" — but vector search catches the semantic overlap because the embedding model understands they mean similar things.

**Q: What about hallucination?**
A: The system prompt explicitly says "use ONLY the retrieved context" and "if the context doesn't have enough information, say so — do not guess." The citations let users verify every claim against the source file.

**Q: Why 384 dimensions? Why not more?**
A: all-MiniLM-L6-v2 is optimized for speed and semantic similarity. Larger models (3072 dimensions) capture more nuance but cost more to store and compare. For incident reports, 384 is sufficient.

**Q: How do you handle new incidents?**
A: Add the new .md file to `data/incidents/` and run `ingest-cmd` again. In production, this would be automated via a webhook from PagerDuty or Jira.

**Q: What about sensitive incident data?**
A: Embeddings are one-way — you can't reconstruct the original text from the vector. In production, encrypt at rest, use IAM-scoped access, and run the embedding model inside a VPC.

**Q: Why does the same embedding model need to be used for ingestion and query?**
A: Because the 384 numbers are model-specific. If you used Model A to create vectors and Model B to embed the query, the numbers wouldn't be comparable — like measuring distance in miles vs kilometers without converting.

**Q: How much does it cost to run?**
A: Embeddings are free (local model). The LLM call costs fractions of a cent per query on paid models, or zero on OpenRouter free models. You can demo the entire project for under $1.

---

## 18. Suggested YouTube Video Flow

1. Hook — "Your incidents are your best runbook"
2. Problem statement — why SRE teams need this
3. Architecture diagram walkthrough
4. Live demo — ingest + CLI queries
5. API server demo + Swagger UI
6. Show vectors and similarity scores
7. Code walkthrough — key files
8. DevOps artifacts — Dockerfile, Helm, CI
9. Scaling for production — what changes
10. Wrap-up + GitHub link

---

## 19. Useful Commands Reference

```bash
# Activate virtual environment (every new terminal)
cd ~/incident-rag-engine
source .venv/bin/activate

# Ingest incident data
python -m src.cli.main ingest-cmd

# Single query
python -m src.cli.main ask "your question here"

# Interactive chat
python -m src.cli.main chat

# API server
ANONYMIZED_TELEMETRY=False uvicorn src.api.main:app --reload

# API health check
curl http://localhost:8000/health

# API query
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "pod CrashLoopBackOff"}' | python3 -m json.tool

# Run tests
ANONYMIZED_TELEMETRY=False pytest -v

# Show similarity scores
python3 -c "
from src.retrieval.vectorstore import get_vectorstore
store = get_vectorstore()
results = store.similarity_search_with_relevance_scores('your query', k=5)
for doc, score in results:
    print(f'{score:.4f}  {doc.metadata[\"source\"]}')
"

# Show a real vector
python3 -c "
from langchain_huggingface import HuggingFaceEmbeddings
model = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')
v = model.embed_query('pod CrashLoopBackOff')
print(f'Vector: {len(v)} dimensions')
print(f'First 10: {[round(x, 4) for x in v[:10]]}')
"

# See how documents are chunked
python3 -c "
from src.ingestion.loader import load_incidents
from src.ingestion.chunker import chunk_documents
docs = load_incidents()
chunks = chunk_documents(docs)
print(f'{len(docs)} files → {len(chunks)} chunks')
for c in chunks:
    print(f'{c.metadata[\"source\"]:40s}  {len(c.page_content):5d} chars')
"

# Compare vector similarity
python3 -c "
from langchain_huggingface import HuggingFaceEmbeddings
import numpy as np
model = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')
v1 = model.embed_query('pod CrashLoopBackOff in production')
v2 = model.embed_query('container restart loop failing health check')
v3 = model.embed_query('terraform state lock during deployment')
def cosine_sim(a, b):
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
print(f'Query vs CrashLoopBackOff: {cosine_sim(v1, v2):.4f}  (similar)')
print(f'Query vs Terraform:        {cosine_sim(v1, v3):.4f}  (different)')
"
```

---

## 20. Troubleshooting

**`ModuleNotFoundError: No module named 'src'`**
You need to be in the project root directory with the venv activated:
```bash
cd ~/incident-rag-engine
source .venv/bin/activate
```

**`RateLimitError: 429`**
Free OpenRouter models share rate limits. Wait 30 seconds and retry. If persistent, switch models:
```bash
# Check available free models
curl -s https://openrouter.ai/api/v1/models | python3 -c "
import sys,json
[print(m['id']) for m in json.load(sys.stdin)['data'] if ':free' in m['id']]
"

# Update .env with a working free model
sed -i 's|current-model-name|new-model-name:free|' .env
```

**`NotFoundError: 404 — model unavailable for free`**
The free model slug changed on OpenRouter. Check available free models (command above) and update `.env`.

**ChromaDB telemetry warnings**
Harmless warnings, not errors. Suppress with:
```bash
echo "ANONYMIZED_TELEMETRY=False" >> .env
```

**`pip install` timeout**
Slow internet. Add timeout flags:
```bash
pip install -e ".[dev]" --timeout 120 --retries 5
```

**PyTorch downloading GPU/CUDA libraries (1.5GB+)**
You accidentally installed full PyTorch. Fix:
```bash
pip uninstall torch -y
pip install torch --index-url https://download.pytorch.org/whl/cpu --timeout 120
```

**`error: src refspec main does not match any` (git push)**
Your local branch is `master`, GitHub expects `main`:
```bash
git branch -M main
git push -u origin main
```
