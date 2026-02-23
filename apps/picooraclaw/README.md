<div align="center">
  <img src="assets/new_logo.png" alt="PicoClaw" width="512">

  <h1>PicoOraClaw: Ultra-Efficient AI Assistant in Go + ollama + Oracle AI Database based on PicoClaw</h1>

  <h3>$10 Hardware · 10MB RAM · 1s Boot · Oracle AI Vector Search · ollama-based </h3>

  <p>
    <img src="https://img.shields.io/badge/Go-1.24+-00ADD8?style=flat&logo=go&logoColor=white" alt="Go">
    <img src="https://img.shields.io/badge/Arch-x86__64%2C%20ARM64%2C%20RISC--V-blue" alt="Hardware">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <br>
    <a href="https://picoclaw.io"><img src="https://img.shields.io/badge/Website-picoclaw.io-blue?style=flat&logo=google-chrome&logoColor=white" alt="Website"></a>
    <a href="https://x.com/SipeedIO"><img src="https://img.shields.io/badge/X_(Twitter)-SipeedIO-black?style=flat&logo=x&logoColor=white" alt="Twitter"></a>
  </p>

  <p>
    <a href="https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https://github.com/jasperan/picooraclaw/raw/main/deploy/oci/orm/picooraclaw-orm.zip">
      <img src="https://oci-resourcemanager-plugin.plugins.oci.oraclecloud.com/latest/deploy-to-oracle-cloud.svg" alt="Deploy to Oracle Cloud"/>
    </a>
  </p>

 [中文](README.zh.md) | [日本語](README.ja.md) | **English**
</div>

---

PicoOraClaw is a fork of [PicoClaw](https://github.com/sipeed/picoclaw) that adds **Oracle AI Database** as a backend for persistent storage and semantic vector search, as well as ollama for LLM communication. The agent remembers facts and recalls them by meaning using in-database ONNX embeddings — no external embedding API required.

<table align="center">
  <tr align="center">
    <td align="center" valign="top">
      <p align="center">
        <img src="assets/picoclaw_mem.gif" width="360" height="240">
        <br><sub>Under 10MB RAM — runs on $10 hardware</sub>
      </p>
    </td>
    <td align="center" valign="top">
      <p align="center">
        <img src="assets/compare.jpg" width="400" height="240">
      </p>
    </td>
  </tr>
</table>

## 🦾 Demonstration

### 🛠️ Standard AI Workflows

<table align="center">
  <tr align="center">
    <th><p align="center">🧩 Full-Stack Engineering</p></th>
    <th><p align="center">🧠 Oracle AI Memory</p></th>
    <th><p align="center">🔎 Web Search & Learning</p></th>
  </tr>
  <tr>
    <td align="center"><p align="center"><img src="assets/picoclaw_code.gif" width="240" height="180"></p></td>
    <td align="center"><p align="center"><img src="assets/picoclaw_memory.gif" width="240" height="180"></p></td>
    <td align="center"><p align="center"><img src="assets/picoclaw_search.gif" width="240" height="180"></p></td>
  </tr>
  <tr>
    <td align="center">Develop · Deploy · Scale</td>
    <td align="center">Remember · Recall · Persist</td>
    <td align="center">Discover · Insights · Trends</td>
  </tr>
</table>

### ⏰ Scheduled Tasks & Reminders

<p align="center">
  <img src="assets/picoclaw_scedule.gif" width="600">
</p>

Set reminders, run recurring tasks, automate workflows — scheduled jobs are stored persistently in Oracle AI Database with full ACID guarantees.

---

## Quickstart (5 minutes)

Everything you need: **Go 1.24+**, **Ollama** and **Docker** (for Oracle AI Database).

### Step 1: Build

```bash
git clone https://github.com/jasperan/picooraclaw.git
cd picooraclaw
make build
```

### Step 2: Initialize

```bash
./build/picooraclaw onboard
```

### Step 3: Start Ollama and pull a model

```bash
# Install Ollama if needed: https://ollama.com/download
ollama pull qwen3:latest
```

### Step 4: Configure for Ollama

Edit `~/.picooraclaw/config.json`:

```json
{
  "agents": {
    "defaults": {
      "provider": "ollama",
      "model": "qwen3:latest",
      "max_tokens": 8192,
      "temperature": 0.7
    }
  },
  "providers": {
    "ollama": {
      "api_key": "",
      "api_base": "http://localhost:11434/v1"
    }
  }
}
```

### Step 5: Chat

```bash
# One-shot
./build/picooraclaw agent -m "Hello!"

# Interactive mode
./build/picooraclaw agent
```

That's it — you have a working AI assistant with local inference. No API keys, no cloud dependency.

---

## Deploy to Oracle Cloud (One-Click)

Deploy a fully configured PicoOraClaw instance on OCI with Oracle AI Database, Ollama, and the gateway — all automated.

[![Deploy to Oracle Cloud](https://oci-resourcemanager-plugin.plugins.oci.oraclecloud.com/latest/deploy-to-oracle-cloud.svg)](https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https://github.com/jasperan/picooraclaw/raw/main/deploy/oci/orm/picooraclaw-orm.zip)

**What gets deployed:**
- OCI Compute instance (shape of your choice, ARM A1.Flex is Always Free)
- Ollama with `gemma3:270m` pre-loaded for CPU inference
- Oracle AI Database (container by default, or managed Autonomous DB)
- PicoOraClaw gateway running as a systemd service

**After deployment (~5-8 min for setup to complete):**

```bash
# Check setup progress
ssh opc@<public_ip> -t 'tail -f /var/log/picooraclaw-setup.log'

# Start chatting
ssh opc@<public_ip> -t picooraclaw agent

# Check gateway health
curl http://<public_ip>:18790/health
```

---

## Add Oracle AI Vector Search

Oracle gives you persistent storage, semantic memory (remember/recall by meaning), and crash-safe ACID transactions. Without it, storage is file-based.

Run the setup script — it handles everything automatically:

```bash
./scripts/setup-oracle.sh [optional-password]
```

This single script:
1. Pulls and starts the Oracle AI Database Free container
2. Waits for the database to be ready
3. Creates the `picooraclaw` database user with the required grants
4. Patches your `~/.picooraclaw/config.json` with the Oracle connection settings
5. Runs `picooraclaw setup-oracle` to initialize the schema and load the ONNX embedding model

Expected output when complete:
```
── Step 4/4: Schema + ONNX model ─────────────────────────────────────────
  Running picooraclaw setup-oracle...
✓ Connected to Oracle AI Database
✓ Schema initialized (8 tables with PICO_ prefix)
✓ ONNX model 'ALL_MINILM_L12_V2' already loaded
✓ VECTOR_EMBEDDING() test passed
✓ Prompts seeded from workspace

════════════════════════════════════════════════════════
  Oracle AI Database setup complete!
  Test with:
    ./build/picooraclaw agent -m "Remember that I love Go"
    ./build/picooraclaw agent -m "What language do I like?"
    ./build/picooraclaw oracle-inspect
════════════════════════════════════════════════════════
```

### Step 5: Test semantic memory

```bash
# Store a fact
./build/picooraclaw agent -m "Remember that my favorite language is Go"

# Recall by meaning (not keywords)
./build/picooraclaw agent -m "What programming language do I prefer?"
```

The second command finds the stored memory via cosine similarity on 384-dimensional vectors — no keyword matching.

### Step 6: Inspect what's stored

The `oracle-inspect` command lets you view everything stored in Oracle without writing SQL.

```bash
picooraclaw oracle-inspect [table] [options]
```

**Tables:** `memories`, `sessions`, `transcripts`, `state`, `notes`, `prompts`, `config`, `meta`
**Options:** `-n <limit>` max rows (default 20), `-s <text>` semantic search (memories only)

#### Overview dashboard (no arguments)

```bash
./build/picooraclaw oracle-inspect
```

```
=============================================================
  PicoOraClaw Oracle AI Database Inspector
=============================================================

  Table                  Rows
  ─────────────────────  ────
  Memories                  20  ████████████████████
  Sessions                   4  ████
  Transcripts                6  ██████
  State                      8  ████████
  Daily Notes                3  ███
  Prompts                    4  ████
  Config                     2  ██
  Meta                       1  █
  ─────────────────────  ────
  Total                     48

  Recent Memories (last 5):
  ─────────────────────────────────────────────────────────
  2026-02-19 04:13  0.6 [preference]  Design docs and plan files go in docs/plans/ ...
  2026-02-19 04:13  0.6 [interest]  User is interested in IoT and embedded systems ...
  2026-02-19 04:13  0.7 [fact]  The Oracle ONNX embedding model used is ALL_MINILM_L12_V2 ...
  2026-02-19 04:13  0.7 [preference]  For complex multi-step tasks, use multi-agent parallel ...
  2026-02-19 04:13  0.8 [preference]  User prefers concise communication ...

  Recent Transcripts (last 5):
  ─────────────────────────────────────────────────────────
  2026-02-19 04:13  assistant   [discord:dev-channel]  I've stored that in memory ...
  2026-02-19 04:13  user        [discord:dev-channel]  Remember that the next release ...
  2026-02-19 04:13  assistant   [telegram:user123]  Oracle Database connection is active ...
  2026-02-19 04:13  user        [telegram:user123]  What's the status of the Oracle connection?
  2026-02-19 04:13  assistant   [cli:repl-session]  I can help with that ...

  Recent Sessions (last 5):
  ─────────────────────────────────────────────────────────
  2026-02-19 04:13  discord:dev-channel             (no summary)
  2026-02-19 04:13  telegram:user123                (no summary)
  2026-02-19 04:13  cli:repl-session                (no summary)
  2026-02-18 06:07  cli:default                     **Cohesive Summary:** The user and
  assistant engaged in a playful exchange starting with "Pong!" ...

  Recent State Entries (last 5):
  ─────────────────────────────────────────────────────────
  2026-02-19 04:13  total_conversations       = 42
  2026-02-19 04:13  agent_mode                = interactive
  2026-02-19 04:13  user_timezone             = America/Los_Angeles
  2026-02-19 04:13  user_name                 = jasperan
  2026-02-19 04:13  last_chat_id              = repl-session

  Recent Daily Notes (last 5):
  ─────────────────────────────────────────────────────────
  2026-02-19  (updated 2026-02-19 04:13)  # 2026-02-19 ...
  2026-02-18  (updated 2026-02-19 04:13)  # 2026-02-18 ...
  2026-02-17  (updated 2026-02-19 04:13)  # 2026-02-17 ...

  System Prompts (last 5):
  ─────────────────────────────────────────────────────────
  2026-02-18 08:38  AGENT                      357 chars
  2026-02-18 08:38  USER                       365 chars
  2026-02-18 08:38  SOUL                       296 chars
  2026-02-18 08:38  IDENTITY                  1271 chars

  Config Entries (last 5):
  ─────────────────────────────────────────────────────────
  2026-02-19 04:13  last_seed                 = 2026-02-19T04:13:34Z
  2026-02-19 04:13  full_config               = { "llm": {...}, "oracle": {...}, ... }

  Schema Metadata:
  ─────────────────────────────────────────────────────────
  2026-02-18 08:38  schema_version                 = 1.0.0

  Tip: Run 'picooraclaw oracle-inspect <table>' for details
       Run 'picooraclaw oracle-inspect memories -s "query"' for semantic search
```

#### List all memories

```bash
./build/picooraclaw oracle-inspect memories
```

```
  All Memories
  ─────────────────────────────────────────────────────────

  ID: faffd019  Vector: yes
  Created: 2026-02-19 04:13  Importance: 0.9  Category: preference  Accessed: 0x
  Content: User prefers Oracle Database as the primary database. They work at Oracle
  and prefer Oracle AI Vector Search for embeddings.

  ID: ecb8cf68  Vector: yes
  Created: 2026-02-19 04:13  Importance: 0.9  Category: preference  Accessed: 0x
  Content: IMPORTANT: Never include AI attribution (Co-Authored-By, Generated by
  Claude, etc.) in git commit messages.

  ID: 0e39036f  Vector: yes
  Created: 2026-02-19 04:13  Importance: 0.8  Category: preference  Accessed: 0x
  Content: Go is the user's primary programming language. They use Go 1.24 and target
  embedded Linux devices (RISC-V, ARM64, x86_64).

  ID: 7aca4a7b  Vector: yes
  Created: 2026-02-19 04:13  Importance: 0.8  Category: preference  Accessed: 0x
  Content: User prefers Ollama as the open-source LLM framework for local inference.

  ID: 27c2473c  Vector: yes
  Created: 2026-02-19 04:13  Importance: 0.7  Category: interest  Accessed: 0x
  Content: User is interested in RAG (Retrieval-Augmented Generation) using LlamaIndex
  and LangChain frameworks.

  ...
```

#### Semantic search over memories

```bash
./build/picooraclaw oracle-inspect memories -s "what does the user like to program in"
```

```
  Semantic Search: "what does the user like to program in"
  ─────────────────────────────────────────────────────────

  [ 61.3% match]  ID: 383ff5d3
  Created: 2026-02-16 06:13  Importance: 0.7  Category: preference  Accessed: 0x
  Content: I prefer Python and Go for programming

  [ 60.7% match]  ID: 0e74a94c
  Created: 2026-02-18 02:20  Importance: 0.7  Category: preference  Accessed: 0x
  Content: my favorite programming language is Go

  [ 40.1% match]  ID: 0e39036f
  Created: 2026-02-19 04:13  Importance: 0.8  Category: preference  Accessed: 0x
  Content: Go is the user's primary programming language. They use Go 1.24 and target
  embedded Linux devices (RISC-V, ARM64, x86_64).

  [ 30.9% match]  ID: 22b84dba
  Created: 2026-02-16 06:12  Importance: 0.7  Category: employment  Accessed: 1x
  Content: I work at Oracle as a developer

  ...
```

#### Inspect sessions

```bash
./build/picooraclaw oracle-inspect sessions
```

```
  Chat Sessions
  ─────────────────────────────────────────────────────────

  Session: discord:dev-channel
  Created: 2026-02-19 04:13  Updated: 2026-02-19 04:13  Messages size: 673 bytes

  Session: telegram:user123
  Created: 2026-02-19 04:13  Updated: 2026-02-19 04:13  Messages size: 304 bytes

  Session: cli:repl-session
  Created: 2026-02-19 04:13  Updated: 2026-02-19 04:13  Messages size: 982 bytes

  Session: cli:default
  Created: 2026-02-16 06:12  Updated: 2026-02-18 06:07  Messages size: 2848 bytes
  Summary: **Cohesive Summary:** The user and assistant engaged in a playful
  exchange starting with "Pong!" The assistant recalled the user's role as an
  Oracle developer and their preference for Go ...
```

#### Inspect agent state

```bash
./build/picooraclaw oracle-inspect state
```

```
  Agent State (Key-Value)
  ─────────────────────────────────────────────────────────
  agent_mode                     = interactive                    (2026-02-19 04:13)
  last_channel                   = cli                            (2026-02-19 04:13)
  last_chat_id                   = repl-session                   (2026-02-19 04:13)
  last_model                     = gpt-4o-mini                    (2026-02-19 04:13)
  tools_used_count               = 187                            (2026-02-19 04:13)
  total_conversations            = 42                             (2026-02-19 04:13)
  user_name                      = jasperan                       (2026-02-19 04:13)
  user_timezone                  = America/Los_Angeles            (2026-02-19 04:13)
```

#### Inspect daily notes

```bash
./build/picooraclaw oracle-inspect notes
```

```
  Daily Notes
  ─────────────────────────────────────────────────────────

  Date: 2026-02-19  ID: 2ccb7e70  Vector: yes  Updated: 2026-02-19 04:13
  Content: # 2026-02-19
  ## Development Progress
  - Implemented seed-demo command for Oracle data population
  - Tested vector embeddings with ALL_MINILM_L12_V2 model
  - Fixed session serialization edge case with empty tool calls

  Date: 2026-02-18  ID: 29a60563  Vector: yes  Updated: 2026-02-19 04:13
  Content: # 2026-02-18
  ## Testing & Debugging
  - Ran full test suite: all 47 tests passing
  - Profiled memory usage on RISC-V board: 8.2MB peak
  - Verified Oracle connection pooling under concurrent load

  Date: 2026-02-17  ID: f4cfb628  Vector: no  Updated: 2026-02-19 04:13
  Content: # 2026-02-17
  ## Architecture Planning
  - Designed transcript storage schema for PICO_TRANSCRIPTS table
  - Sketched WhatsApp channel adapter following existing Telegram pattern
  - Reviewed LangChain-OracleDB integration for RAG pipeline
```

#### Inspect transcripts

```bash
./build/picooraclaw oracle-inspect transcripts
```

```
  Conversation Transcripts
  ─────────────────────────────────────────────────────────
  2026-02-19 04:13  #2  assistant  [discord:dev-channel]   I've stored that in memory ...
  2026-02-19 04:13  #1  user       [discord:dev-channel]   Remember that the next release ...
  2026-02-19 04:13  #2  assistant  [telegram:user123]      Oracle Database connection is active ...
  2026-02-19 04:13  #1  user       [telegram:user123]      What's the status of the Oracle connection?
  2026-02-19 04:13  #2  assistant  [cli:repl-session]      I can help with that ...
  2026-02-19 04:13  #1  user       [cli:repl-session]      Can you help me add a new tool ...
```

#### Inspect stored config

```bash
./build/picooraclaw oracle-inspect config
```

```
  Stored Config
  ─────────────────────────────────────────────────────────
  full_config                    = {
  "llm": {"provider": "openai-compatible", "model": "gpt-4o-mini", ...},
  "oracle": {"enabled": true, "onnx_model": "ALL_MINILM_L12_V2"},
  "channels": {"telegram": {"enabled": true}, "discord": {"enabled": true}},
  "agent": {"max_tool_iterations": 10, "context_window": 8192}
}  (2026-02-19 04:13)
  last_seed                      = 2026-02-19T04:13:34Z       (2026-02-19 04:13)
```

#### View a system prompt in full

```bash
./build/picooraclaw oracle-inspect prompts IDENTITY
./build/picooraclaw oracle-inspect prompts SOUL
```

#### Schema metadata, ONNX models, and vector indexes

```bash
./build/picooraclaw oracle-inspect meta
```

```
  Schema Metadata
  ─────────────────────────────────────────────────────────
  schema_version                 = 1.0.0

  ONNX Models
  ─────────────────────────────────────────────────────────
  ALL_MINILM_L12_V2          EMBEDDING        ONNX

  Vector Indexes
  ─────────────────────────────────────────────────────────
  IDX_PICO_DAILY_NOTES_VEC        on PICO_DAILY_NOTES
  IDX_PICO_MEMORIES_VEC           on PICO_MEMORIES
```

---

## CLI Reference

| Command | Description |
|---|---|
| `picooraclaw onboard` | Initialize config and workspace |
| `picooraclaw agent -m "..."` | One-shot chat |
| `picooraclaw agent` | Interactive chat mode |
| `picooraclaw gateway` | Start long-running service with channels |
| `picooraclaw status` | Show status |
| `picooraclaw setup-oracle` | Initialize Oracle schema + ONNX model |
| `picooraclaw oracle-inspect` | Inspect data stored in Oracle |
| `picooraclaw oracle-inspect memories -s "query"` | Semantic search over memories |
| `picooraclaw seed-demo` | Populate Oracle with realistic demo data |
| `picooraclaw cron list` | List scheduled jobs |
| `picooraclaw skills list` | List installed skills |

---

## How Oracle Storage Works

<p align="center">
  <img src="assets/arch.jpg" alt="PicoOraClaw Architecture" width="680">
</p>

```
                           ┌──────────────────────────────────────────┐
                           │         Oracle AI Database               │
                           │                                          │
  picooraclaw binary       │  ┌──────────────┐  ┌──────────────────┐ │
  ┌───────────────────┐    │  │ PICO_MEMORIES │  │ PICO_DAILY_NOTES │ │
  │  AgentLoop        │    │  │  + VECTOR idx │  │  + VECTOR idx    │ │
  │  ├─ SessionStore ──────│──│──────────────┐│  └──────────────────┘ │
  │  ├─ StateStore   ──────│──│ PICO_SESSIONS││                       │
  │  ├─ MemoryStore  ──────│──│ PICO_STATE   ││  ┌──────────────────┐ │
  │  ├─ PromptStore  ──────│──│ PICO_PROMPTS ││  │ ALL_MINILM_L12_V2│ │
  │  ├─ ConfigStore  ──────│──│ PICO_CONFIG  ││  │   (ONNX model)   │ │
  │  └─ Tools:       │    │  │ PICO_META    ││  │  384-dim vectors  │ │
  │     ├─ remember  ──────│──│ PICO_TRANS.  ││  └──────────────────┘ │
  │     └─ recall    ──────│──└──────────────┘│                       │
  └───────────────────┘    │   go-ora v2.9.0  │                       │
         (pure Go)         │   (pure Go driver)│                       │
                           └──────────────────────────────────────────┘
```

| Table | Purpose |
|---|---|
| `PICO_MEMORIES` | Long-term memory with 384-dim vector embeddings for semantic search |
| `PICO_SESSIONS` | Chat history per channel |
| `PICO_TRANSCRIPTS` | Full conversation audit log |
| `PICO_STATE` | Agent key-value state |
| `PICO_DAILY_NOTES` | Daily journal entries with vector embeddings |
| `PICO_PROMPTS` | System prompts (IDENTITY.md, SOUL.md, etc.) |
| `PICO_CONFIG` | Runtime configuration |
| `PICO_META` | Schema versioning metadata |

The `remember` tool stores text + vector embedding via `VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :text AS DATA)`. The `recall` tool searches by cosine similarity via `VECTOR_DISTANCE()`. Results with < 30% similarity are filtered out.

---

## Using a Cloud LLM Instead of Ollama

If you prefer a cloud provider, set `provider` and add your API key:

<details>
<summary><b>OpenRouter (access to all models)</b></summary>

```json
{
  "agents": {
    "defaults": {
      "provider": "openrouter",
      "model": "anthropic/claude-opus-4-5"
    }
  },
  "providers": {
    "openrouter": {
      "api_key": "sk-or-v1-xxx",
      "api_base": "https://openrouter.ai/api/v1"
    }
  }
}
```

Get a key at [openrouter.ai/keys](https://openrouter.ai/keys) (200K free tokens/month).

</details>

<details>
<summary><b>Zhipu (best for Chinese users)</b></summary>

```json
{
  "agents": {
    "defaults": {
      "provider": "zhipu",
      "model": "glm-4.7"
    }
  },
  "providers": {
    "zhipu": {
      "api_key": "your-key",
      "api_base": "https://open.bigmodel.cn/api/paas/v4"
    }
  }
}
```

Get a key at [bigmodel.cn](https://open.bigmodel.cn/usercenter/proj-mgmt/apikeys).

</details>

<details>
<summary><b>All supported providers</b></summary>

| Provider | Purpose | Get API Key |
|---|---|---|
| `ollama` | Local inference (recommended) | [ollama.com](https://ollama.com) |
| `openrouter` | Access to all models | [openrouter.ai](https://openrouter.ai/keys) |
| `zhipu` | Zhipu/GLM models | [bigmodel.cn](https://open.bigmodel.cn/usercenter/proj-mgmt/apikeys) |
| `anthropic` | Claude models | [console.anthropic.com](https://console.anthropic.com) |
| `openai` | GPT models | [platform.openai.com](https://platform.openai.com) |
| `gemini` | Gemini models | [aistudio.google.com](https://aistudio.google.com) |
| `deepseek` | DeepSeek models | [platform.deepseek.com](https://platform.deepseek.com) |
| `groq` | Fast inference + voice transcription | [console.groq.com](https://console.groq.com) |

</details>

---

## Chat Channels

Connect PicoOraClaw to Telegram, Discord, Slack, DingTalk, LINE, QQ, or Feishu via the `gateway` command.

<details>
<summary><b>Telegram</b> (Recommended)</summary>

1. Message `@BotFather` on Telegram, send `/newbot`, copy the token
2. Add to `~/.picooraclaw/config.json`:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

3. Run `picooraclaw gateway`

</details>

<details>
<summary><b>Discord</b></summary>

1. Create a bot at [discord.com/developers](https://discord.com/developers/applications), enable MESSAGE CONTENT INTENT
2. Add to config:

```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

3. Invite bot with `Send Messages` + `Read Message History` permissions
4. Run `picooraclaw gateway`

</details>

<details>
<summary><b>QQ, DingTalk, LINE, Feishu, Slack</b></summary>

See `config/config.example.json` for the full channel configuration reference. Each channel follows the same pattern:

```json
{
  "channels": {
    "<channel_name>": {
      "enabled": true,
      "<credentials>": "...",
      "allow_from": []
    }
  }
}
```

Run `picooraclaw gateway` after configuring.

</details>

---

## Oracle on Autonomous Database (Cloud)

<details>
<summary><b>ADB wallet-less TLS</b></summary>

```json
{
  "oracle": {
    "enabled": true,
    "mode": "adb",
    "dsn": "(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.us-ashburn-1.oraclecloud.com))(connect_data=(service_name=xxx_myatp_low.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))",
    "user": "picooraclaw",
    "password": "YourPass123"
  }
}
```

</details>

<details>
<summary><b>ADB with mTLS wallet</b></summary>

```json
{
  "oracle": {
    "enabled": true,
    "mode": "adb",
    "host": "adb.us-ashburn-1.oraclecloud.com",
    "port": 1522,
    "service": "xxx_myatp_low.adb.oraclecloud.com",
    "walletPath": "/path/to/wallet",
    "user": "picooraclaw",
    "password": "YourPass123"
  }
}
```

Download wallet from OCI Console > Autonomous Database > DB Connection > Download Wallet.

</details>

<details>
<summary><b>Oracle config reference</b></summary>

| Field | Env Variable | Default | Description |
|---|---|---|---|
| `enabled` | `PICO_ORACLE_ENABLED` | `false` | Enable Oracle backend |
| `mode` | `PICO_ORACLE_MODE` | `freepdb` | `freepdb` or `adb` |
| `host` | `PICO_ORACLE_HOST` | `localhost` | Oracle host |
| `port` | `PICO_ORACLE_PORT` | `1521` | Listener port |
| `service` | `PICO_ORACLE_SERVICE` | `FREEPDB1` | Service name |
| `user` | `PICO_ORACLE_USER` | `picooraclaw` | DB username |
| `password` | `PICO_ORACLE_PASSWORD` | — | DB password |
| `dsn` | `PICO_ORACLE_DSN` | — | Full DSN (ADB wallet-less) |
| `walletPath` | `PICO_ORACLE_WALLET_PATH` | — | Wallet directory (ADB mTLS) |
| `onnxModel` | `PICO_ORACLE_ONNX_MODEL` | `ALL_MINILM_L12_V2` | ONNX model for embeddings |
| `agentId` | `PICO_ORACLE_AGENT_ID` | `default` | Multi-agent isolation key |

</details>

---

## Troubleshooting

<details>
<summary><b>Oracle: Connection refused / ORA-12541</b></summary>

```bash
docker ps | grep oracle          # Is it running?
docker logs oracle-free          # Wait for "DATABASE IS READY"
ss -tlnp | grep 1521            # Is port 1521 listening?
```

</details>

<details>
<summary><b>Oracle: ORA-01017 invalid username/password</b></summary>

```bash
docker exec -it oracle-free sqlplus sys/YourPass123@localhost:1521/FREEPDB1 as sysdba
SQL> ALTER USER picooraclaw IDENTIFIED BY NewPassword123;
```

</details>

<details>
<summary><b>Oracle: VECTOR_EMBEDDING() returns ORA-04063</b></summary>

ONNX model not loaded. Run `picooraclaw setup-oracle` or manually:

```sql
BEGIN
  DBMS_VECTOR.LOAD_ONNX_MODEL('PICO_ONNX_DIR', 'all_MiniLM_L12_v2.onnx', 'ALL_MINILM_L12_V2');
END;
/
```

Requires `GRANT CREATE MINING MODEL TO picooraclaw;` as SYSDBA.

</details>

<details>
<summary><b>Agent falls back to file-based mode</b></summary>

Oracle is enabled but connection failed at startup. Check:
- Is the Oracle container healthy? (`docker ps`)
- Password match between config and `ORACLE_PWD`?
- Service name should be `FREEPDB1` (not `FREE` or `XE`)

</details>

---

## Build Targets

```bash
make build          # Build for current platform
make build-all      # Cross-compile: linux/{amd64,arm64,riscv64}, darwin/arm64, windows/amd64
make install        # Build + install to ~/.local/bin
make test           # go test ./...
make fmt            # go fmt ./...
make vet            # go vet ./...
```

## Docker Compose

```bash
# Full stack with Oracle
PICO_ORACLE_PASSWORD=YourPass123 docker compose --profile oracle --profile gateway up -d

# Without Oracle
docker compose --profile gateway up -d

# One-shot agent
docker compose run --rm picoclaw-agent -m "What is 2+2?"
```

## Features

- Single static binary (~10MB RAM), runs on RISC-V/ARM64/x86_64
- Ollama, OpenRouter, Anthropic, OpenAI, Gemini, Zhipu, DeepSeek, Groq providers
- Oracle AI Database with AI Vector Search (384-dim ONNX embeddings)
- Chat channels: Telegram, Discord, Slack, QQ, DingTalk, LINE, Feishu, WhatsApp
- Scheduled tasks via cron expressions
- Heartbeat periodic tasks
- Skills system (workspace, global, GitHub-hosted)
- Security sandbox with workspace restriction
- Graceful fallback to file-based storage when Oracle is unavailable