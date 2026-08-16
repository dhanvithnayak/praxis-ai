# Claude Code Clone (Multi-Provider + Enterprise RAG)

An enterprise-grade, highly modular, provider-agnostic autonomous coding assistant CLI built in **Python 3.12+** using **`uv`**.

---

## Key Capabilities

- **Autonomous ReAct Engine**: Full multi-turn **Reasoning + Acting** execution loop with intelligent context budgeting, sliding-window compaction, and dynamic system prompts.
- **Universal Multi-Provider Gateway**: Powered by `litellm`—seamlessly switch between:
  - **Anthropic**: Claude 3.7 Sonnet, Claude 3.5 Sonnet, Claude 3.5 Haiku (with prompt caching).
  - **OpenAI**: GPT-4o, o3-mini, o1.
  - **Google Gemini**: Gemini 2.5 Flash, Gemini 2.0 Pro.
  - **Local Models (Ollama / vLLM)**: DeepSeek R1, DeepSeek V3, Qwen 2.5 Coder, Llama 3.3.
  - **Cloud Providers**: OpenRouter, AWS Bedrock, Azure OpenAI, Groq, Mistral.
- **Enterprise RAG Knowledge Subsystem**:
  - Embedded vector database (**LanceDB**) stored locally in `.agent/rag_data/`.
  - Local CPU ONNX embeddings (**FastEmbed** / `BAAI/bge-small-en-v1.5`) with zero API key dependencies, or cloud embeddings via OpenAI.
  - **Hybrid Search**: Dense vector similarity combined with **BM25** sparse keyword matching via Reciprocal Rank Fusion (RRF).
  - Structure-aware chunking for Markdown headers, Terraform, YAML, Python, and TypeScript.
  - First-class LLM tool: `query_knowledge_base` for autonomous institutional memory retrieval.
- **Tool Sandbox**:
  - `read_file` (line slicing and offset support)
  - `write_file` (atomic write)
  - `edit_file` (targeted block replacements with unified diff previews)
  - `list_dir` (recursive directory tree with `.gitignore` filtering)
  - `grep_search` (regex pattern search)
  - `file_glob` (file pattern matcher)
  - `bash_executor` (async streaming subprocess with safety timeouts)
  - `git_manager` (status, diffs, branch inspection)
- **Safety Guardrails**:
  - `STRICT`: Asks user confirmation for every tool execution.
  - `ACCEPT_READ_ONLY` (default): Auto-executes read-only and RAG tools, prompts for file writes and shell commands.
  - `AUTONOMOUS` (`--permission autonomous`): Auto-executes tools with safety blocklists for destructive root commands.
- **Rich Terminal UX**:
  - Interactive REPL with `prompt_toolkit` (multi-line input, slash command auto-completion, persistent history).
  - Real-time token streaming, live tool execution spinners, and syntax-highlighted diffs with `rich`.

---

## Quickstart with `uv`

### 1. Install dependencies
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

### 3. Start Interactive REPL
```bash
uv run agent-cli start
# Or with a specific model:
uv run agent-cli start --model claude-3-7-sonnet
uv run agent-cli start --model gpt-4o
uv run agent-cli start --model gemini-flash
uv run agent-cli start --model ollama/deepseek-r1:14b
```

### 4. Non-Interactive Single Task Run
```bash
uv run agent-cli run "Find all TODO comments in src/ and format them in a table"
```

---

## Enterprise RAG Usage

### Ingesting Documents / Codebases
Index internal architecture decision records (ADRs), infrastructure playbooks, Kubernetes manifests, or API documentation:

```bash
uv run agent-cli rag-ingest ./docs --collection enterprise-infra
uv run agent-cli rag-ingest ./terraform --collection infra-modules
```

### Querying Knowledge Base Directly
```bash
uv run agent-cli rag-query "How are staging database credentials configured?" --collection enterprise-infra
```

During conversational turns, the assistant automatically uses the `query_knowledge_base` tool to retrieve these documents whenever relevant.

---

## Interactive Slash Commands

Inside the interactive REPL session, use slash commands to control the agent:

| Command | Description |
| :--- | :--- |
| `/model [name]` | Inspect or dynamically switch active LLM (e.g. `/model claude-3-7-sonnet`, `/model gpt-4o`) |
| `/permission [mode]` | Switch safety mode (`strict`, `accept_read_only`, `autonomous`) |
| `/rag [on\|off]` | Enable or disable RAG knowledge base lookups |
| `/compact` | Summarize and compact conversation history to free context window |
| `/clear` | Clear terminal screen and reset conversation history |
| `/history` | View the number of messages in active memory |
| `/help` | Show command reference |
| `/exit` | Exit the CLI session |

---

## Running Tests

Run the comprehensive test suite with `uv`:
```bash
uv run pytest
```

---

## Architecture Overview

```
claude-code-clone/
├── pyproject.toml                    # UV project configuration
├── src/
│   └── claude_code_clone/
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
