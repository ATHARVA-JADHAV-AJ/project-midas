# Project Midas 🛡️

**Sovereign, Air-Gapped Agentic AI Operating System**  
*SIH 2026 Grand Finale Architecture*

Project Midas is an enterprise-grade, fully autonomous Agentic AI workbench designed to operate entirely offline in secure, air-gapped environments. Engineered specifically for resource-constrained hardware, the entire multimodal agent loop runs seamlessly on a strict **6GB VRAM** ceiling.

---

## 🚀 Core Architecture & Features

### 1. True Agentic Loop (ReAct)
Midas isn't a static chatbot; it's an autonomous agent. Using a custom LangGraph state machine, the agent employs a **Plan → Act → Observe → Iterate** loop. It breaks ambiguous tasks into multi-step execution plans (e.g., Vision Extract → Code Execute → Document Generation) and autonomously self-corrects if its code fails during execution.

### 2. Dynamic VRAM Swapper
To run 8B+ parameter workflows on a 6GB GPU, Midas acts as its own resource manager. It aggressively orchestrates memory by hot-swapping specialized models into VRAM (e.g., loading `qwen2-vl:2b` for OCR, instantly flushing it upon completion, and pre-warming `qwen2.5:3b-instruct` for reasoning and code generation).

### 3. Secure Code Execution Sandbox
Midas enforces a strict **Math Prohibition Rule**—the LLM is forbidden from doing arithmetic in its context window to prevent hallucinations. Instead, it writes Python code (pandas, openpyxl). This code is evaluated in a dual-layer security environment:
*   **Tier A (RestrictedPython):** Abstract Syntax Tree (AST) validation blocks malicious imports, bans infinite loops (30s timeout), and prevents prompt-injection payloads.
*   **Tier B (Docker Dispatcher):** Fully isolated execution container.

### 4. Network Sovereignty & Air-Gap Proof
Built for zero-trust environments. A live telemetry dashboard monitors `ss -tunp` metrics at the kernel level, proving to operators (and SIH judges) that exactly zero external API calls are made during the entire RAG and inference pipeline. All assets (including CDNs like Mermaid.js) are hosted locally.

### 5. Local RAG & Embedding (CPU-Pinned)
Document ingestion (PDF, DOCX) utilizes Docling for layout-aware chunking. To preserve precious GPU memory for the reasoning models, embedding generation (`nomic-embed-text`) is strictly pinned to the CPU before being stored in a local Qdrant vector database.

---

## 🛠️ Tech Stack
*   **Frontend:** Vanilla JS, CSS Keyframes, marked.js, Mermaid.js, KaTeX
*   **Backend API:** Python, FastAPI, Redis Streams (Live WebSocket telemetry)
*   **Agentic Graph:** LangGraph (Custom Nodes: Planner, Observer, Code Executor)
*   **LLM Engine:** Ollama (Local inference)
*   **Vector Store:** Qdrant
*   **Task Queue:** Celery + Redis Priority Queue (Time-decay starvation prevention)

---

## ⚙️ Installation & Quick Start

### 1. Prerequisites
*   Docker & Docker Compose
*   [Ollama](https://ollama.com/) installed on the host machine.

### 2. Pull Required Local Models
Open a terminal on your host machine and pull the necessary models into Ollama:
```bash
ollama pull qwen2.5:3b-instruct    # Reasoning & Coding
ollama pull llama3.2:latest        # Answer Polishing
ollama pull qwen2-vl:2b            # Vision & OCR
ollama pull nomic-embed-text:latest # RAG Embeddings (CPU)
```

### 3. Spin up the Environment
Clone the repository and start the Docker stack:
```bash
git clone https://github.com/ATHARVA-JADHAV-AJ/project-midas.git
cd project-midas
docker compose up -d --build
```
*(This launches 7 isolated containers: API, Celery Worker, Redis, Qdrant, Priority Consumer, Sandbox Dispatcher, and Frontend).*

### 4. Access the Workbench
*   Navigate to: `http://localhost:8501`
*   **Default Login:** 
    *   User: `admin`
    *   Pass: `midas2026`

---

## 🧪 Evaluating the Agentic Capabilities

To test the true power of the agentic loop, try uploading a mock invoice or dataset (e.g., `data.xlsx`) with the following prompt:

> *"Analyze this data, calculate the sum of the overdue column, and generate a formal .docx summary report."*

**Watch the Telemetry:**
1. The `agent_planner` node will structure a 2-to-3 step autonomous plan.
2. The agent will write Python code, send it to the sandbox, and read the output.
3. If it hallucinates a column name, the `agent_observer` will catch the `KeyError`, loop back, rewrite the code, and try again.
4. The VRAM manager will dynamically swap models as needed.
5. The Network Sovereignty monitor will stay at **0 External Connections**.

---
*Built for SIH 2026. Code by Atharva Kishor Jadhav (AJ).*
