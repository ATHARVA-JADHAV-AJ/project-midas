# Project Midas
**Author:** Atharva Kishor Jadhav (AJ)  
**Classification:** Air-Gapped Agentic OS — Prototype Build

---

## What This Is

Project Midas is a fully offline, centralized agentic operating system built for legacy government hardware with a strict 6 GB VRAM ceiling. It accepts natural-language tasks, routes them through a priority queue, executes them via a LangGraph state machine backed by local Ollama models, and produces real `.docx` and `.xlsx` output files — with zero external network calls at any stage.

## Stack

| Component | Technology |
|---|---|
| API / WebSocket | FastAPI + Uvicorn |
| Priority Queue | Redis Sorted Set (continuous aging) + Celery |
| Agent Orchestration | LangGraph state machine |
| Local LLMs | Ollama (`qwen2.5:3b-instruct`, `qwen2-vl:2b`) |
| Embeddings / RAG | Nomic-Embed-Text (CPU-only) + Qdrant |
| Code Execution | RestrictedPython (Tier A) + Docker sidecar (Tier B) |
| Frontend | Streamlit + live netstat sovereignty monitor |
| Auth | JWT (HS256, local users.json) |

## Quick Start

```bash
# 1. Bootstrap — generates secrets and creates users.json
python scripts/bootstrap.py

# 2. Pull required Ollama models (before starting Docker)
ollama pull qwen2.5:3b-instruct
ollama pull qwen2-vl:2b
ollama pull nomic-embed-text

# 3. Start the stack
docker compose up --build

# 4. Access
#    API:      http://localhost:8000/docs
#    Frontend: http://localhost:8501
```

## Security Notes

- **Tier derived from JWT role** — clients cannot self-assign priority
- **Tier B (Docker sandbox) is never LLM-routed** — only operator-triggered system jobs
- **Tier A (RestrictedPython) Allowlist Expanded (v3.2)** — `pandas` and `openpyxl` are explicitly permitted for Spreadsheet Analysis. This strictly expands the attack surface, but is mitigated because pandas/openpyxl do not grant filesystem/network access beyond the existing `open()` override (which remains locked to `/outputs/`), and strict CPU/Memory/30s timeout limits still apply.
- **`users.json`** is manually seeded (known prototype limitation — see bootstrap.py)
- **Air-gap proof** — check the netstat panel in the Streamlit UI during inference

## Version Log

See `current_update.txt` for the append-only phase completion log.
