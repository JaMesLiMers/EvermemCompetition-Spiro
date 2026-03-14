# Documentation Redesign — Design Spec

**Date:** 2026-03-14
**Status:** Approved
**Audience:** Competition judges (primary), developers (secondary)
**Language:** English only
**Narrative:** Companion + technical hybrid

---

## Overview

Rewrite all project documentation for the EverMemOS competition submission. Spiro is the world's first context-native empathic AI wearable — a band that quietly listens to everyday life and transforms it into language, memory, and meaning.

The documentation should tell a compelling story for judges while remaining technically transparent and easy to follow.

## Deliverables

### 1. Root README.md

Top-down storytelling structure. Judges get the full picture in one scroll.

**Section layout:**

| # | Section | Content | Visual |
|---|---------|---------|--------|
| 1 | Cover | Project title, one-liner tagline, badges | `figure/cover_pic.jpg` |
| 2 | The Core Tension | Why Spiro exists — life is becoming clearer, yet harder to feel | `figure/core_tension.png` |
| 3 | Introducing Spiro | What it is — a reflective wearable AI, from life to language | `figure/introducing.png` |
| 4 | Features | 4 key capabilities: Capture Moments, On-Demand Perspective, Relationship Insights, Pattern Tracking | `figure/stream.jpg` |
| 5 | User Scenarios | Real-world examples: before a big moment, capturing a glimmer, relationship insight, a longer view | `figure/User Scenario.png` |
| 6 | Hardware | The wearable band — PCB, form factors, on-wrist demos | `figure/hardware_demo.jpg` |
| 7 | Algorithm Flowchart | End-to-end data flow from audio capture to user-facing content | **drawio diagram** (`docs/diagrams/algorithm-flowchart.drawio`) |
| 8 | System Architecture | Module layout, Docker services, data flow between components | **drawio diagram** (`docs/diagrams/system-architecture.drawio`) |
| 9 | Quick Start | Init, deploy, pipeline, run — in ~5 commands via Makefile | Text + code blocks |
| 10 | Project Structure | Table of folders with one-line descriptions + links to sub-READMEs | Text table |
| 11 | Advanced Usage | Full Makefile reference, .env config, custom task parameters | Text + code blocks |
| 12 | Built With | Tech stack, EverMemOS competition acknowledgment, team | Text |

**Narrative arc:** Why (tension) → What (intro + features + scenarios) → How (hardware + algorithm + architecture) → Try it (quick start + advanced)

**Note:** The Makefile `run-task` help string currently omits `event_cards` — update it to list all 5 task types.

### 2. Drawio Diagrams

Create `docs/diagrams/` directory. Export diagrams to SVG (`docs/diagrams/*.svg`) for embedding in READMEs. SVG is preferred for scalability and GitHub rendering.

#### 2a. Algorithm Flowchart (`docs/diagrams/algorithm-flowchart.drawio`)

Left-to-right flow showing the full pipeline:

```
Hardware Band (Mic) → Audio Stream → Gemini Audio Processing → Event Parsing
→ Speaker Mapping (GPT-4o-mini) → GCF Conversion → EverMemOS Ingestion
→ Memory Groups → Episodic Memory Extraction → Agent Prefetch
→ Task Analysis (Claude Sonnet) → JSON Output → App UI Display
```

Key visual elements:
- Hardware section (orange/warm tones) — band, microphone, audio stream
- Processing section (blue tones) — Gemini, event parser, speaker mapping
- Memory section (green tones) — EverMemOS, groups, episodic memories
- Agent section (purple tones) — Claude, 5 task types
- Output section (pink/warm) — React UI, cards, timeline, relationship graph

#### 2b. System Architecture (`docs/diagrams/system-architecture.drawio`)

Layered architecture diagram showing:

```
┌─ Hardware Layer ─────────────────────┐
│  Spiro Band → Audio Stream           │
└──────────────────────────────────────┘
         ↓
┌─ Pipeline Layer ─────────────────────┐
│  generate_speaker_mapping.py         │
│  convert_to_gcf.py                   │
│  ingest_gcf.py                       │
└──────────────────────────────────────┘
         ↓
┌─ EverMemOS (Docker) ────────────────┐
│  Redis | MongoDB | Elasticsearch     │
│  Milvus | arq Worker | REST API      │
└──────────────────────────────────────┘
         ↓
┌─ MCP Server ─────────────────────────┐
│  5 tools: search, get, store, meta,  │
│  delete                              │
└──────────────────────────────────────┘
         ↓
┌─ Agent Layer ────────────────────────┐
│  opencode CLI + Claude Sonnet        │
│  5 tasks: relationships, profiling,  │
│  timeline, suggestions, event_cards  │
└──────────────────────────────────────┘
         ↓
┌─ App Layer ──────────────────────────┐
│  React UI: TimeRiver,                │
│  RelationshipGraph, EventCards       │
└──────────────────────────────────────┘
```

#### 2c. Optional: Pipeline Data Flow (`docs/diagrams/pipeline-flow.drawio`)

For `pipeline/README.md` — detailed view of the data transformation steps with file formats at each stage.

### 3. Subfolder READMEs

All in English. Each follows a consistent structure: Overview → How it works → Usage → Reference. Replace existing subfolder READMEs where they exist.

#### 3a. `pipeline/README.md`

- **Overview:** Data preprocessing pipeline — transforms raw audio events into structured memories
- **Pipeline Flow:** Reference to pipeline-flow.drawio or text diagram
- **Scripts:**
  - `generate_speaker_mapping.py` — LLM batch speaker role inference (GPT-4o-mini)
  - `convert_to_gcf.py` — Raw events → GroupChatFormat conversion with smart splitting
  - `ingest_gcf.py` — Async batch ingestion to EverMemOS (semaphore-controlled concurrency)
  - `transcript_parser.py` — Regex-based fragment/turn extraction
  - `extract_transcript.py` — Audio transcript extraction
- **Usage examples:** Make commands for each step
- **Data format specs:** Input format, GCF output format, speaker mapping format

#### 3b. `agent/README.md`

- **Overview:** AI agent analysis system — extracts insights from memories using Claude Sonnet
- **How it works:** Prefetch episodic memories → Build prompt → Run via opencode CLI → Parse JSON output
- **5 Task Types table:**
  - relationships — interpersonal network analysis
  - profiling — user persona building
  - timeline — event chronology with causal analysis
  - suggestions — intelligent recommendations
  - event_cards — user-readable event summaries
- **Usage:** `make run-task TASK=... USER_ID=...`
- **Output format:** JSON metadata envelope spec

#### 3c. `mcp_server/README.md`

- **Overview:** MCP bridge between EverMemOS and AI agents
- **5 Tools:**
  - `search_memory` — search episodic memories
  - `get_memories` — retrieve memories by ID
  - `store_message` — store new messages
  - `get_conversation_meta` — get conversation metadata
  - `delete_memories` — remove memories
- **Configuration:** opencode.json MCP server setup
- **Dependencies:** `requirements.txt` and installation
- **How it connects:** EverMemOS REST API ↔ MCP Protocol ↔ Agent

#### 3d. `shared/README.md`

- **Overview:** Shared utilities used across modules
- **EverMemOS API Client** (`evermemos_api.py`):
  - Async HTTP client (httpx)
  - Connection pooling
  - Methods: store_message, search_memory, create_conversation_meta, etc.
- **Usage:** Import examples

#### 3e. `data/README.md`

- **Overview:** Dataset for the competition — 832 real conversation events
- **Files:**
  - `basic_events_79ef7f17.json` — Raw dataset (13MB, 832 events with embedded speaker mappings)
  - `gcf_all.json` — Merged GCF output (3089 groups, 141K messages)
  - `demo_audio.mp3` — Audio sample
  - `demo_output.json` — Sample analysis output
- **Data format:** Fragment structure, speaker turns, speaker label normalization
- **Pipeline relationship:** How raw data flows through pipeline to EverMemOS

#### 3f. `app_demo/README.md`

- **Overview:** React visualization UI for analysis results
- **Components:**
  - `TimeRiver` — chronological event timeline
  - `RelationshipGraph` — interactive relationship network (vis.js)
  - `ParticleEdges` — animated relationship connections
  - `EditPersonModal` — person data editing
- **Services:** Gemini API integration for semantic analysis
- **How to run:** Setup and dev server commands
- **Input:** JSON output from agent tasks

## Figures

All existing figures stored in `figure/` directory. Referenced via relative paths in markdown:

```markdown
![Cover](figure/cover_pic.jpg)
![Core Tension](figure/core_tension.png)
![Introducing Spiro](figure/introducing.png)
![Features](figure/stream.jpg)
![User Scenarios](figure/User%20Scenario.png)
![Hardware](figure/hardware_demo.jpg)
```

Drawio diagrams stored in `docs/diagrams/`. Export to SVG for README embedding:

```markdown
![Algorithm Flowchart](docs/diagrams/algorithm-flowchart.svg)
![System Architecture](docs/diagrams/system-architecture.svg)
```

The `.drawio` source files are kept alongside the SVGs for future editing.

## Terminology

- **Wearable / band** — NOT bracelet. Spiro is a wearable band (手环)
- **Companion AI** — the emotional/empathic narrative
- **Context-native** — captures context from real life, not typed input
- **Empathic** — understands and reflects emotional patterns

## Out of Scope

- EverMemOS submodule README (has its own docs)
- opencode submodule README (has its own docs)
- API reference docs (covered by EverMemOS docs)
