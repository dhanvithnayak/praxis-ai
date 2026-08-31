# Praxis AI: Autonomous Enterprise Operations & SOP-Grounded Agent Platform

An enterprise-grade, local-first, multi-provider autonomous agent platform built in **Python 3.12+** using **`uv`**. 

**Praxis AI** transforms static institutional knowledge—Standard Operating Procedures (SOPs), supply chain guidelines, infrastructure runbooks, and compliance policies—into an active, autonomous execution partner that non-technical domain operators can direct using natural language.

---

## The Enterprise Challenge & Use Case

In modern enterprises, critical operational knowledge is siloed across hundreds of static documents:
- **Supply Chain & Logistics**: Inventory threshold calculations, safety-stock policies, vendor SLAs, and fulfillment protocols.
- **Operations & Compliance**: Security checklists, change management SOPs, infrastructure configurations, and audit policies.
- **Incident Response**: SRE runbooks, escalation matrixes, diagnostic sequences, and recovery guidelines.

**The Problem**: Non-technical domain operators (supply chain managers, operations specialists, compliance auditors) spend countless hours manually cross-referencing documents, running repetitive calculations in spreadsheets, and waiting on engineering teams to write custom scripts.

**The Solution with Praxis AI**:
1. **Ingest Institutional Memory**: Ingest all company SOPs, runbooks, and architecture specs into a local-first **Hybrid RAG vector store (LanceDB + BM25 + FastEmbed ONNX)**.
2. **Autonomous Natural Language Execution**: Non-technical operators ask questions or assign tasks in plain English. Praxis AI autonomously retrieves relevant SOP rules, plans multi-step actions using a **ReAct loop**, performs mathematical calculations, executes sandboxed diagnostic scripts, and validates output.
3. **Zero-Trust Safety & Governance**: Operates under strict **3-tier security guardrails** (`STRICT`, `ACCEPT_READ_ONLY`, `AUTONOMOUS`), ensuring destructive commands require explicit human confirmation.

---

## Real-World Enterprise Workflows

### 1. Supply Chain Metric Calculation & Anomaly Detection
> **Scenario**: A supply chain coordinator needs to recalculate dynamic safety stock and reorder points for 50 regional distribution centers based on updated lead-time variance guidelines in SOP-SC-2026.
> 
> **User Prompt**:
> ```text
> praxis run "Review SOP-SC-2026 in our knowledge base, analyze warehouse_inventory.csv, calculate dynamic safety stock for all Tier-1 hubs, and flag any hubs currently under 15 days of buffer."
> ```
> **Praxis AI Action**: Queries RAG for `SOP-SC-2026` formulas $\rightarrow$ Executes Python calculation sandbox $\rightarrow$ Produces verified summary table with zero manual calculation errors.

### 2. Infrastructure & Compliance Audit
> **Scenario**: An IT compliance analyst needs to verify that staging infrastructure conforms to organizational cybersecurity SOPs before an external audit.
> 
> **User Prompt**:
> ```text
> praxis run "Check our staging infrastructure configs against Section 4 of our Security SOP. Flag any unencrypted storage buckets or overly permissive IAM policies."
> ```
> **Praxis AI Action**: Retrieves security policy criteria via Hybrid RAG $\rightarrow$ Inspects Terraform / YAML configurations via read-only tools $\rightarrow$ Generates an audit discrepancy report.

### 3. SRE Incident Triage & Runbook Execution
> **Scenario**: An on-call support specialist responds to high database latency alerts without deep database engineering experience.
> 
> **Interactive Session**:
> ```text
> praxis start
> > "We are seeing elevated p99 database latency on the checkout service. Follow our DB-Triage-Runbook to check connection pools and slow queries."
> ```
> **Praxis AI Action**: Retrieves runbook diagnostic steps $\rightarrow$ Safely runs read-only queries with user confirmation $\rightarrow$ Identifies blocking transactions and suggests standard recovery action.

---

## Core Capabilities

- **Autonomous ReAct Engine**: Full multi-turn **Reasoning + Acting** execution loop with intelligent context budgeting, sliding-window compaction, and dynamic system prompts.
- **Enterprise Hybrid RAG Subsystem**:
  - Embedded vector database (**LanceDB**) stored locally in `.agent/rag_data/`.
  - Local CPU ONNX embeddings (**FastEmbed** / `BAAI/bge-small-en-v1.5`) with zero API key dependencies and zero data leakage, or cloud embeddings via OpenAI.
  - **Hybrid Search**: Dense vector similarity combined with **BM25** sparse keyword matching via Reciprocal Rank Fusion (RRF).
  - Structure-aware chunking for Markdown headers, Terraform, YAML, Python, and TypeScript.
  - First-class LLM tool: `query_knowledge_base` for autonomous institutional memory retrieval.
- **Universal Multi-Provider Gateway**: Powered by `litellm`—seamlessly switch between:
  - **Anthropic**: Claude 3.7 Sonnet, Claude 3.5 Sonnet, Claude 3.5 Haiku (with prompt caching).
  - **OpenAI**: GPT-4o, o3-mini, o1.
  - **Google Gemini**: Gemini 2.5 Flash, Gemini 2.0 Pro.
  - **Local Models (Ollama / vLLM)**: DeepSeek R1, DeepSeek V3, Qwen 2.5 Coder, Llama 3.3.
  - **Cloud Providers**: OpenRouter, AWS Bedrock, Azure OpenAI, Groq, Mistral.
- **Sandboxed Tool Suite**:
  - `read_file` (line slicing and offset support)
  - `write_file` (atomic write)
  - `edit_file` (targeted block replacements with unified diff previews)
  - `list_dir` (recursive directory tree with `.gitignore` filtering)
  - `grep_search` (regex pattern search)
  - `file_glob` (file pattern matcher)
  - `bash_executor` (async streaming subprocess with safety timeouts)
  - `git_manager` (status, diffs, branch inspection)
- **Safety Guardrails & Permissions**:
  - `STRICT`: Prompts for user confirmation before executing any tool.
  - `ACCEPT_READ_ONLY` (default): Auto-executes read-only and RAG tools; prompts for file writes and shell commands.
  - `AUTONOMOUS` (`--permission autonomous`): Auto-executes tools with safety blocklists for destructive system commands.
- **Rich Terminal UX**:
  - Interactive REPL with `prompt_toolkit` (multi-line input, slash command auto-completion, persistent history).
  - Real-time token streaming, live tool execution spinners, and syntax-highlighted diffs with `rich`.

---

## Quickstart with `uv`

### 1. Install Dependencies
```bash
uv sync
```

### 2. Configure API Keys
Add your keys to a `.env` file or export them in your shell:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIzaSy..."
```

*(Note: If using local models like Ollama / DeepSeek R1 with FastEmbed ONNX, zero cloud API keys are required.)*

### 3. Ingest Enterprise SOPs & Documentation
Index internal Standard Operating Procedures, runbooks, architecture manifests, or documentation:

```bash
# Ingest supply chain SOPs
uv run praxis rag-ingest ./docs/sops --collection enterprise-sops

# Ingest infrastructure runbooks
uv run praxis rag-ingest ./infra --collection enterprise-infra
```

### 4. Start Interactive REPL
```bash
uv run praxis start

# Or with a specific model:
uv run praxis start --model claude-3-7-sonnet
uv run praxis start --model gpt-4o
uv run praxis start --model gemini-flash
uv run praxis start --model ollama/deepseek-r1:14b
```

### 5. Non-Interactive Single Task Run
```bash
uv run praxis run "Review our supply chain SOP and calculate reorder quantities for Q3"
```

---

## Interactive Slash Commands

Inside an interactive session, use slash commands to control the agent in real time:

| Command | Description |
| :--- | :--- |
| `/model [name]` | Inspect or dynamically switch active LLM (e.g. `/model claude-3-7-sonnet`, `/model gpt-4o`) |
| `/permission [mode]` | Switch safety mode (`strict`, `accept_read_only`, `autonomous`) |
| `/rag [on\|off]` | Enable or disable RAG knowledge base lookups |
| `/compact` | Summarize and compact conversation history to optimize token budget |
| `/clear` | Clear terminal screen and reset conversation history |
| `/history` | View the number of active messages in memory |
| `/help` | Show command reference |
| `/exit` | Exit the CLI session |

---

## Running Tests

Run the full asynchronous test suite with `uv`:
```bash
uv run pytest
```

---

## Architecture Overview

```
praxis-ai/
├── pyproject.toml                    # UV project configuration & scripts (praxis, praxis-ai)
├── src/
│   └── praxis_ai/
│       ├── cli/                      # Presentation layer (Typer + Rich + Prompt-Toolkit)
│       │   ├── cli.py                # Command entrypoint
│       │   ├── repl.py               # Interactive REPL session
│       │   └── ui/                   # Renderer, spinners, confirmation prompts
│       │
│       ├── core/
│       │   ├── agent/                # ReAct loop controller, prompt builder, context manager
│       │   ├── providers/            # Universal LiteLLM gateway and model mappings
│       │   ├── tools/                # Tool registry, file system, bash, git, search, RAG tool
│       │   ├── rag/                  # FastEmbed local embeddings, LanceDB, hybrid search
│       │   └── config/               # Settings, constants, permission guardrails
│       │
│       └── utils/                    # Diff computation, token counter, logger
└── tests/
    ├── unit/                         # Unit tests for tools, providers, RAG
    └── integration/                  # Integration tests for ReAct loop
```
