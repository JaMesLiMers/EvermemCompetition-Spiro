# Documentation Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite all project documentation in English with drawio diagrams for the EverMemOS competition submission.

**Architecture:** Top-down storytelling README with 6 existing figures + 2 drawio diagrams. Subfolder READMEs follow a consistent Overview → How it works → Usage → Reference structure. All content in English.

**Tech Stack:** Markdown, draw.io XML (.drawio files), SVG export via draw.io CLI

**Spec:** `docs/superpowers/specs/2026-03-14-documentation-redesign-design.md`

---

## Chunk 1: Drawio Diagrams

### Task 1: Create Algorithm Flowchart

**Files:**
- Create: `docs/diagrams/algorithm-flowchart.drawio`

- [ ] **Step 1: Create docs/diagrams/ directory**

```bash
mkdir -p docs/diagrams
```

- [ ] **Step 2: Write the algorithm flowchart drawio XML**

Write `docs/diagrams/algorithm-flowchart.drawio` — a left-to-right flowchart showing the full pipeline:

```
Hardware Band (Mic) → Audio Stream → Gemini Audio Processing → Event Parsing
→ Speaker Mapping (GPT-4o-mini) → GCF Conversion → EverMemOS Ingestion
→ Memory Groups → Episodic Memory Extraction → Agent Prefetch
→ Task Analysis (Claude Sonnet) → JSON Output → App UI Display
```

Use the drawio skill (`/drawio`) to generate the XML. Color coding:
- Hardware section: orange/warm tones (`fillColor=#fff2cc;strokeColor=#d6b656`)
- Processing section: blue tones (`fillColor=#dae8fc;strokeColor=#6c8ebf`)
- Memory section: green tones (`fillColor=#d5e8d4;strokeColor=#82b366`)
- Agent section: purple tones (`fillColor=#e1d5e7;strokeColor=#9673a6`)
- Output section: pink/warm tones (`fillColor=#f8cecc;strokeColor=#b85450`)

Layout: left-to-right, nodes spaced 200px horizontal / 120px vertical. Use `edgeStyle=orthogonalEdgeStyle;rounded=1` for all edges. Group related nodes into swimlane containers for each section.

- [ ] **Step 3: Verify the drawio file opens correctly**

```bash
# Check XML is well-formed
python3 -c "import xml.etree.ElementTree as ET; ET.parse('docs/diagrams/algorithm-flowchart.drawio'); print('Valid XML')"
```

- [ ] **Step 4: Export to SVG (if draw.io desktop is available)**

```bash
# Try SVG export; skip if drawio CLI not available
if command -v drawio &>/dev/null; then
  drawio -x -f svg -e -b 10 -o docs/diagrams/algorithm-flowchart.drawio.svg docs/diagrams/algorithm-flowchart.drawio
fi
```

- [ ] **Step 5: Commit**

```bash
git add docs/diagrams/algorithm-flowchart.drawio
git commit -m "docs: add algorithm flowchart drawio diagram"
```

---

### Task 2: Create System Architecture Diagram

**Files:**
- Create: `docs/diagrams/system-architecture.drawio`

- [ ] **Step 1: Write the system architecture drawio XML**

Write `docs/diagrams/system-architecture.drawio` — a layered architecture diagram showing 6 layers stacked vertically:

1. **Hardware Layer** (orange) — Spiro Band → Audio Stream
2. **Pipeline Layer** (blue) — generate_speaker_mapping.py, convert_to_gcf.py, ingest_gcf.py
3. **EverMemOS Layer** (green) — Docker services: Redis, MongoDB, Elasticsearch, Milvus, arq Worker, REST API (port 1995)
4. **MCP Server Layer** (teal) — 5 tools: search_memory, get_memories, store_message, get_conversation_meta, delete_memories
5. **Agent Layer** (purple) — opencode CLI + Claude Sonnet 4.6, 5 tasks: relationships, profiling, timeline, suggestions, event_cards
6. **App Layer** (pink) — React UI: TimeRiver, RelationshipGraph, ParticleEdges, EventCards

Use swimlane containers for each layer. Arrows between layers with `edgeStyle=orthogonalEdgeStyle`. Each layer should be a swimlane with `startSize=30`. Internal components as rounded rectangles. Database services as `shape=cylinder3`.

- [ ] **Step 2: Verify the drawio file**

```bash
python3 -c "import xml.etree.ElementTree as ET; ET.parse('docs/diagrams/system-architecture.drawio'); print('Valid XML')"
```

- [ ] **Step 3: Export to SVG (if draw.io desktop is available)**

```bash
if command -v drawio &>/dev/null; then
  drawio -x -f svg -e -b 10 -o docs/diagrams/system-architecture.drawio.svg docs/diagrams/system-architecture.drawio
fi
```

- [ ] **Step 4: Commit**

```bash
git add docs/diagrams/system-architecture.drawio
git commit -m "docs: add system architecture drawio diagram"
```

---

## Chunk 2: Root README

### Task 3: Write Root README.md

**Files:**
- Modify: `README.md` (full rewrite)

- [ ] **Step 1: Write the root README**

Replace the entire `README.md` with the new English version. Structure (all sections in one file):

**Section 1 — Cover:**
```markdown
<p align="center">
  <img src="figure/cover_pic.jpg" alt="Spiro" width="100%">
</p>

# Spiro — World-First Context-Native Empathic AI Wearable

> From Life to Language. Carry your days with you.

[![EverMemOS](https://img.shields.io/badge/Powered%20by-EverMemOS-blue)](https://github.com/anthropics/evermemos)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Required-blue)](https://docker.com)
```

**Section 2 — The Core Tension:**
- Image: `figure/core_tension.png`
- Text: "Life is becoming clearer. Yet harder to feel. We can record almost everything — steps, sleep, conversations, data. But meaning is fading. Spiro exists to bring meaning back."

**Section 3 — Introducing Spiro:**
- Image: `figure/introducing.png`
- Text: "Spiro is a reflective wearable AI that transforms everyday life into language, memory, and meaning. It quietly listens to everyday life and returns lived experience as words."

**Section 4 — Features:**
- Image: `figure/stream.jpg`
- List the 4 features from the figure:
  1. Capture Meaningful Moments — auto-identifies important conversations, emotional shifts, milestones
  2. On-Demand Perspective — rotate the band to surface relevant past moments
  3. Relationship Pattern Insights — analyzes interaction patterns over time
  4. Personal Pattern Tracking — identifies recurring themes in work, relationships, emotional cycles

**Section 5 — User Scenarios:**
- Image: `figure/User Scenario.png`
- Brief intro: "Spiro adapts to your life across different moments:"
- Reference 4 scenarios from the figure (Before a Big Moment, Capturing a Glimmer, Relationship Insight, A Longer View)

**Section 6 — Hardware:**
- Image: `figure/hardware_demo.jpg`
- Text about the wearable band: custom PCB, available in silver and gold, designed as everyday jewelry with embedded AI

**Section 7 — Algorithm Flowchart:**
- Header: "How It Works — From Audio to Insight"
- Text: brief description of the end-to-end pipeline
- Image: `![Algorithm Flowchart](docs/diagrams/algorithm-flowchart.drawio.svg)` (or link to .drawio file if SVG export unavailable)
- Fallback: include a text-based flow diagram similar to the existing README

**Section 8 — System Architecture:**
- Header: "System Architecture"
- Image: `![System Architecture](docs/diagrams/system-architecture.drawio.svg)` (or link)
- Fallback text diagram

**Section 9 — Quick Start:**
Translate existing Chinese quick start to English. Keep the same structure:
```markdown
## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python >= 3.10
- [opencode CLI](https://opencode.ai)

### 1. Initialize
make init
# Edit .env with your API keys

### 2. Deploy Services
make deploy
make status

### 3. Prepare Data
make generate-speaker-mappings INPUT=data/basic_events_79ef7f17.json
make convert-gcf INPUT=data/basic_events_79ef7f17.json

### 4. Ingest Data
make ingest-gcf

### 5. Run Analysis
make run-task TASK=relationships USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090

### 6. Stop Services
make stop
```

**Section 10 — Project Structure:**
Table format with links to subfolder READMEs:

| Directory | Description |
|-----------|-------------|
| [`agent/`](agent/README.md) | AI Agent analysis module — 5 task types powered by Claude Sonnet |
| [`pipeline/`](pipeline/README.md) | Data preprocessing — speaker mapping, GCF conversion, ingestion |
| [`mcp_server/`](mcp_server/README.md) | MCP Server bridging EverMemOS and AI agents |
| [`shared/`](shared/README.md) | Shared utilities — EverMemOS async API client |
| [`data/`](data/README.md) | Datasets — 832 conversation events |
| [`app_demo/`](app_demo/README.md) | React visualization UI |
| `EverMemOS/` | Memory engine (git submodule) — [docs](EverMemOS/docs/) |
| `opencode/` | opencode CLI (git submodule) |

**Section 11 — Advanced Usage:**
Translate existing sections: all Make commands table, environment variables table, opencode.json config, task parameters table. Include `event_cards` in all task listings.

**Section 12 — Built With:**
- EverMemOS — long-term memory engine
- Claude Sonnet 4.6 — AI analysis via opencode
- Gemini — audio processing
- GPT-4o-mini — speaker role inference
- React + vis.js — visualization
- Docker — infrastructure
- Acknowledgment: "Built for the EverMemOS Competition"

- [ ] **Step 2: Verify markdown renders correctly**

```bash
# Check no broken image links
for f in figure/cover_pic.jpg figure/core_tension.png figure/introducing.png figure/stream.jpg "figure/User Scenario.png" figure/hardware_demo.jpg; do
  [ -f "$f" ] && echo "OK: $f" || echo "MISSING: $f"
done
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite root README in English for competition"
```

---

## Chunk 3: Subfolder READMEs

### Task 4: Write pipeline/README.md

**Files:**
- Create: `pipeline/README.md`

**Reference files to read before writing:**
- `pipeline/generate_speaker_mapping.py`
- `pipeline/convert_to_gcf.py`
- `pipeline/ingest_gcf.py`
- `pipeline/transcript_parser.py`
- `pipeline/extract_transcript.py`

- [ ] **Step 1: Read all pipeline scripts to understand exact functionality**

- [ ] **Step 2: Write pipeline/README.md**

Structure:
```markdown
# Pipeline — Data Preprocessing

## Overview
Transforms raw audio conversation events into structured memories...

## Pipeline Flow
[Text diagram or reference to pipeline-flow.drawio]

Raw Events (832) → Speaker Mapping → GCF Conversion → EverMemOS Ingestion

## Scripts

### generate_speaker_mapping.py
[What it does, input/output, usage]

### convert_to_gcf.py
[What it does, smart splitting, input/output, usage]

### ingest_gcf.py
[What it does, async concurrency, input/output, usage]

### transcript_parser.py
[What it does, regex patterns, usage]

### extract_transcript.py
[What it does, usage]

## Usage
[Make commands for each step with examples]

## Data Formats
[Input format, GCF output format, speaker mapping format]
```

- [ ] **Step 3: Commit**

```bash
git add pipeline/README.md
git commit -m "docs: add pipeline README"
```

---

### Task 5: Write agent/README.md

**Files:**
- Create: `agent/README.md`

**Reference files to read before writing:**
- `agent/cli.py`
- `agent/config.py`
- `agent/tasks/base.py`
- `agent/tasks/relationships.py`
- `agent/tasks/profiling.py`
- `agent/tasks/timeline.py`
- `agent/tasks/suggestions.py`
- `agent/tasks/event_cards.py`

- [ ] **Step 1: Read all agent source files**

- [ ] **Step 2: Write agent/README.md**

Structure:
```markdown
# Agent — AI Memory Analysis

## Overview
Extracts insights from stored memories using Claude Sonnet 4.6...

## How It Works
1. Prefetch episodic memories from EverMemOS for the target user/group
2. Build a task-specific prompt with prefetched context
3. Execute via opencode CLI (MCP-enabled)
4. Parse and validate JSON output

## Task Types

| Task | Description | Key Output Fields |
|------|-------------|-------------------|
| relationships | Interpersonal network analysis | persons, relationships, key_interactions |
| profiling | User persona building | interests, personality_traits, behavioral_habits, values |
| timeline | Event chronology | timeline, causal_analysis |
| suggestions | Intelligent recommendations | suggestions (with context, actionability) |
| event_cards | User-readable summaries | event_cards (title, body, timestamp, participants) |

## Usage
[Make commands with all parameters]

## Output Format
[JSON metadata envelope spec with example]
```

- [ ] **Step 3: Commit**

```bash
git add agent/README.md
git commit -m "docs: add agent README"
```

---

### Task 6: Write mcp_server/README.md

**Files:**
- Create: `mcp_server/README.md`

**Reference files to read:**
- `mcp_server/server.py`
- `mcp_server/requirements.txt` (if exists)
- `opencode.json` (MCP config section)

- [ ] **Step 1: Read mcp_server source**

- [ ] **Step 2: Write mcp_server/README.md**

Structure:
```markdown
# MCP Server — EverMemOS Bridge

## Overview
MCP (Model Context Protocol) server that bridges EverMemOS and AI agents...

## Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| search_memory | Search episodic memories | query, user_id, search_type |
| get_memories | Retrieve memories by type | user_id, memory_type |
| store_message | Store a new message | content, sender, group_id |
| get_conversation_meta | Get conversation metadata | user_id |
| delete_memories | Remove memories | memory_ids |

## Configuration
[opencode.json MCP section]

## Dependencies
[requirements.txt contents and installation]

## Architecture
EverMemOS REST API ↔ MCP Protocol ↔ Agent (opencode CLI)
```

- [ ] **Step 3: Commit**

```bash
git add mcp_server/README.md
git commit -m "docs: add mcp_server README"
```

---

### Task 7: Write shared/README.md

**Files:**
- Create: `shared/README.md`

**Reference:** `shared/evermemos_api.py`

- [ ] **Step 1: Read shared source**

- [ ] **Step 2: Write shared/README.md**

Structure:
```markdown
# Shared — Common Utilities

## Overview

## EverMemOS API Client (`evermemos_api.py`)
Async HTTP client wrapping the EverMemOS REST API...

### Methods
[Table of methods with parameters and return types]

### Usage
[Import and usage examples]
```

- [ ] **Step 3: Commit**

```bash
git add shared/README.md
git commit -m "docs: add shared README"
```

---

### Task 8: Write data/README.md

**Files:**
- Modify: `data/README.md` (rewrite)

**Reference:** Existing `data/README.md`, actual data files

- [ ] **Step 1: Read existing data/README.md**

- [ ] **Step 2: Rewrite data/README.md in English**

Structure:
```markdown
# Data — Competition Dataset

## Overview
832 real conversation events captured by the Spiro wearable band...

## Files

| File | Description | Size |
|------|-------------|------|
| basic_events_79ef7f17.json | Raw dataset with embedded speaker mappings | 13MB, 832 events |
| gcf_all.json | Merged GroupChatFormat output | ~5MB, 3089 groups, 141K messages |
| last100_events.json | Subset of recent events for testing | — |
| demo_audio.mp3 | Audio sample | — |
| demo_output.json | Sample analysis output | — |

## Data Format
[Fragment structure, speaker turns, speaker label normalization rules]

## Pipeline Flow
Raw events → Speaker Mapping → GCF Conversion → EverMemOS
```

- [ ] **Step 3: Commit**

```bash
git add data/README.md
git commit -m "docs: rewrite data README in English"
```

---

### Task 9: Write app_demo/README.md

**Files:**
- Modify: `app_demo/README.md` (rewrite)

**Reference:** `app_demo/` source files

- [ ] **Step 1: Read app_demo source**

- [ ] **Step 2: Rewrite app_demo/README.md**

Structure:
```markdown
# App Demo — Visualization UI

## Overview
React-based visualization UI for Spiro analysis results...

## Components

| Component | Description |
|-----------|-------------|
| TimeRiver | Chronological event timeline |
| RelationshipGraph | Interactive relationship network (vis.js) |
| ParticleEdges | Animated relationship connections |
| EditPersonModal | Person data editing interface |
## Services
Gemini API integration for semantic analysis...

## How to Run
[Setup and dev server commands]

## Input
JSON output from agent tasks in `output/` directory
```

- [ ] **Step 3: Commit**

```bash
git add app_demo/README.md
git commit -m "docs: rewrite app_demo README in English"
```

---

## Chunk 4: Cleanup

### Task 10: Fix Makefile run-task Help String

**Files:**
- Modify: `Makefile:197`

- [ ] **Step 1: Update the run-task help text to include event_cards**

Change line 197 from:
```makefile
run-task: ## 运行分析任务 (TASK=relationships|profiling|timeline|suggestions USER_ID=xxx)
```
to:
```makefile
run-task: ## Run analysis task (TASK=relationships|profiling|timeline|suggestions|event_cards USER_ID=xxx)
```

Also update line 199 (usage example) to include `event_cards`:
```
echo "Usage: make run-task TASK=relationships|profiling|timeline|suggestions|event_cards USER_ID=user123"; \
```

And update line 200 (task types list) to include `event_cards`:
```
echo "Task types: relationships | profiling | timeline | suggestions | event_cards"; \
```

- [ ] **Step 2: Verify**

```bash
make run-task 2>&1 | head -5
# Should show event_cards in the task list
```

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "fix: add event_cards to run-task help string"
```
