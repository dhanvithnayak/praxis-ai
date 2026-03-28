<div align="center">
  <h2>Praxis AI</h2>

  <p align="center">
    <i>Autonomous, SOP-grounded automation and code generation for non-technical teams.</i>
    <br />
    <br />
    <a href="https://github.com/dhanvithnayak/praxis-ai/issues">Report Bug / Request Feature</a>
  </p>
</div>

<details>
<summary>Table of Contents</summary>

- [Overview](#overview)
  - [The Automation Bottleneck](#the-automation-bottleneck)
  - [Agentic Automation for Operations](#agentic-automation-for-operations)
  - [Grounding Code in Company Knowledge](#grounding-code-in-company-knowledge)
  - [Safety Modes](#safety-modes)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation & Setup](#installation--setup)
- [Usage](#usage)
  - [1. Ingest Company Policies and Runbooks](#1-ingest-company-policies-and-runbooks)
  - [2. Interactive Assistant](#2-interactive-assistant)
  - [3. One-Shot Task Execution](#3-one-shot-task-execution)
  - [4. Interactive Slash Commands](#4-interactive-slash-commands)
  - [5. Model Selection](#5-model-selection)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [License](#license)

</details>

## Overview

Praxis AI is an autonomous code generation and task execution tool built in Python 3.12+ using `uv`. 

It is designed for non-technical team members (such as operations coordinators, compliance officers, and logistics analysts) to build, test, and run automations for their repetitive daily work without having to rely on engineering teams.

```
+-----------------------------------------------------------------------------------+
|                               Non-Technical Operator                             |
|         "Generate a weekly inventory balance report adhering to our SOP"          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                  Praxis AI                                        |
|  +---------------------------+  +----------------------+  +---------------------+ |
|  |     Hybrid RAG Engine     |  |   ReAct Loop Engine  |  |  Sandboxed Sandbox  | |
|  | (Policies, Runbooks, APIs)|->| (Multi-step Planning)|->| (Code Gen & Tests)  | |
|  +---------------------------+  +----------------------+  +---------------------+ |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               Verified Automation Result / Structured Action Output               |
+-----------------------------------------------------------------------------------+
```

### The Automation Bottleneck

In most organizations, non-technical staff know their operational processes intimately, but cannot write the scripts needed to automate them. 

Automating even routine tasks (cross-referencing inventory spreadsheets, reconciling billing discrepancies, or auditing system configs) typically requires:
1. Writing detailed requirement documents.
2. Holding scoping meetings with Business Analysts (BAs) to draft Jira tickets.
3. Waiting weeks in IT or engineering backlogs for someone to write a short utility script.

### Agentic Automation for Operations

Praxis AI removes this bottleneck by letting operators describe tasks in plain English. 

Using an autonomous ReAct (Reasoning + Acting) execution loop, Praxis AI:
- Translates operational intent into a concrete execution plan.
- Writes the necessary Python scripts and data processing logic.
- Executes code in a local sandboxed environment.
- Detects runtime errors and self-corrects until the task completes successfully.

### Grounding Code in Company Knowledge

General-purpose coding assistants often fail in enterprise environments because they operate in a vacuum without context on internal file structures, database conventions, or compliance rules.

Praxis AI includes an integrated local Hybrid RAG subsystem (LanceDB + BM25 + FastEmbed ONNX):
- **Internal Knowledge Retrieval**: Indexes Standard Operating Procedures (SOPs), runbooks, API schemas, and security checklists.
- **Contextual Code Generation**: The agent inspects internal documentation before writing code (`query_knowledge_base`) to adhere to company standards.
- **Local-First Privacy**: Vector storage and ONNX embeddings run entirely on your machine, preventing proprietary company rules and data from leaking to third parties.

### Safety Modes

To keep automated execution safe, Praxis AI supports three permission tiers:

* `STRICT`: Requires manual user approval before running any tool or shell command.
* `ACCEPT_READ_ONLY` *(default)*: Runs RAG lookups, file reads, and inspections automatically. Prompts for confirmation before modifying files or executing shell commands.
* `AUTONOMOUS`: Runs approved tools automatically while enforcing a hardcoded blocklist against destructive commands (`rm -rf`, disk formatters, network reconfiguration).

## Getting Started

### Prerequisites

* Python 3.12+
* [uv](https://docs.astral.sh/uv/)

```bash
# Install uv (macOS / Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation & Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/dhanvithnayak/praxis-ai.git
   cd praxis-ai
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Configure your chosen LLM provider in `.env`:
   ```env
   # Cloud providers (optional)
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-...
   GEMINI_API_KEY=AIzaSy...

   # Local Ollama setup
   OLLAMA_BASE_URL=http://localhost:11434
   AGENT_MODEL=ollama/qwen2.5-coder:7b
   ```
   When using local models via Ollama with FastEmbed ONNX embeddings, Praxis AI runs fully offline with no API keys needed.

## Usage

### 1. Ingest Company Policies and Runbooks

Index internal SOPs, runbooks, or guides into the local knowledge base:

```bash
# Ingest supply chain SOPs
uv run praxis rag-ingest ./docs/sops --collection enterprise-sops

# Ingest infrastructure runbooks
uv run praxis rag-ingest ./infra/runbooks --collection infrastructure-docs
```

### 2. Interactive Assistant

Start an interactive terminal session:

```bash
uv run praxis start

# Or specify a model directly:
uv run praxis start --model claude-3-7-sonnet
uv run praxis start --model gpt-4o
uv run praxis start --model ollama/qwen2.5-coder:7b
```

Inside the session, describe your task:
```text
praxis> Check SOP-SC-2026 in our knowledge base, parse daily_stock.csv, and build a script to flag hubs below minimum buffer.
```

### 3. One-Shot Task Execution

Run a single automation directly from the terminal:

```bash
uv run praxis run "Audit our Terraform configs in ./infra against our security SOP and output a list of discrepancies"
```

### 4. Interactive Slash Commands

Control execution inside an active session with slash commands:

| Command | Action |
| :--- | :--- |
| `/model [name]` | View or switch active LLM (e.g. `/model gpt-4o`, `/model ollama/deepseek-r1:14b`) |
| `/permission [mode]` | Switch safety tier (`strict`, `accept_read_only`, `autonomous`) |
| `/rag [on\|off]` | Enable or disable knowledge base retrieval |
| `/compact` | Compact conversation history to optimize token usage |
| `/history` | View message count and token allocation |
| `/clear` | Clear terminal and reset session memory |
| `/help` | Show command reference |
| `/exit` | Exit the assistant |

### 5. Model Selection

The gateway supports switching between cloud and local providers:

* **Anthropic**: `claude-3-7-sonnet`, `claude-3-5-sonnet`, `claude-3-5-haiku`
* **OpenAI**: `gpt-4o`, `o3-mini`, `o1`
* **Google Gemini**: `gemini/gemini-2.5-flash`, `gemini/gemini-2.0-pro`
* **Local (Ollama / vLLM)**: `ollama/qwen2.5-coder:7b`, `ollama/deepseek-r1:14b`, `ollama/llama3.3`

## Project Structure

The project uses the standard src-layout:

```
praxis-ai/
├── LICENSE                           # MIT License
├── pyproject.toml                    # UV workspace configuration
├── .env.example                      # Environment template
├── praxis-ai.code-workspace          # Workspace file
│
├── src/
│   └── praxis_ai/
│       ├── cli/                      # Presentation layer (Typer CLI and interactive REPL)
│       │   ├── cli.py                # Command definitions
│       │   ├── repl.py               # Prompt-toolkit REPL session
│       │   └── ui/                   # Terminal renderers and spinners
│       │
│       ├── core/                     # Core execution engine
│       │   ├── agent/                # ReAct loop, context manager, prompt builder
│       │   ├── providers/            # LiteLLM multi-provider gateway
│       │   ├── rag/                  # FastEmbed, LanceDB, BM25 hybrid search
│       │   ├── tools/                # Filesystem, bash, git, and search tools
│       │   └── config/               # Settings, constants, permission guardrails
│       │
│       └── utils/                    # Diff rendering, token counters, helpers
│
└── tests/
    ├── unit/                         # Unit tests (tools, providers, RAG)
    └── integration/                  # Integration tests (ReAct loop)
```

## Running Tests

Run the test suite with `uv`:

```bash
uv run pytest
```

## License

Distributed under the [MIT License](LICENSE).
