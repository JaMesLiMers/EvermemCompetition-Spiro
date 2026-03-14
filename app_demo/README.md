# Spiro — App Demo

React-based visualization UI for Spiro analysis results. This interactive front-end renders memory diaries, relationship networks, and AI-generated insights produced by the Spiro agent pipeline.

## Components

| Component | File | Description |
|---|---|---|
| **TimeRiver** | `components/TimeRiver.tsx` | Per-person chronological memory timeline. Displays diary entries filtered by person, a profile header with relationship stats, and an AI chat input for querying memories. Renders a 3D starfield particle animation on canvas as the background. |
| **RelationshipGraph** | `components/RelationshipGraph.tsx` | Interactive force-directed relationship network built with D3.js. Centers a "Me" node with curved links to each person, weighted by occurrence count. Supports zoom, drag, hover highlights, and click menus to explore or edit a person. |
| **ParticleEdges** | `components/ParticleEdges.tsx` | Ambient canvas overlay that renders drifting particles along screen edges. Used as a decorative layer in the diary detail view with `mix-blend-mode: screen`. |
| **EditPersonModal** | `components/EditPersonModal.tsx` | Modal form for editing a person's name, relationship label, and avatar URL. Updates are applied in-memory via React state. |

The main `App.tsx` orchestrates four views:
- **Home** — grid of memory cards and a "Spiro Nebula" section showing life-topic analysis with gravity scores.
- **Diary** — full-screen immersive reading view with parallax background and participant avatars.
- **Graph** — the `RelationshipGraph` network map ("Spiro Map").
- **River** — the `TimeRiver` person-focused timeline with AI insights panel.

## Services

### Gemini API Integration (`services/geminiService.ts`)

Uses the `@google/genai` SDK to call Gemini models for semantic analysis of diary content:

| Function | Model | Purpose |
|---|---|---|
| `generateDiaryBackground` | gemini-3-flash-preview + gemini-2.5-flash-image | Analyzes diary mood to generate a cinematic image prompt, then produces a background image. |
| `analyzeLifeTopics` | gemini-3-flash-preview | Categorizes all diaries into 4-6 life themes with gravity scores (0-100) via structured JSON output. |
| `queryPersonHistory` | gemini-3-flash-preview | Answers natural-language questions about a person based on diary context. |
| `generatePersonInsights` | gemini-3-flash-preview | Extracts deep insights (birthdays, promises, personality traits, needs) for a specific person. |

## Input Data

The app loads JSON data from the `data/` directory:

| File | Content |
|---|---|
| `people.json` | Person records (id, name, relationship, occurrence count, linked diary IDs) |
| `diaries.json` | Diary entries (id, title, date, content, image URL, linked person IDs) |
| `life-topics.json` | Life theme analysis results (name, gravity, description, icon, color) |
| `insights.json` | Per-person AI insights keyed by person ID |

These files correspond to the JSON output produced by agent tasks in the `output/` directory.

## How to Run

**Prerequisites:** Node.js

1. Install dependencies:
   ```bash
   npm install
   ```

2. Set `GEMINI_API_KEY` in `.env.local` to your Gemini API key (required for AI features).

3. Start the dev server:
   ```bash
   npm run dev
   ```

The app runs on `http://localhost:3000`.

## Tech Stack

- React 19, TypeScript
- Vite 6
- D3.js (relationship graph)
- Canvas API (particle effects)
- Google Gemini SDK (`@google/genai`)
