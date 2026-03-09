# Questline — Demo Video Script

**Target length:** ~4:00
**Format:** Loom screen recording with camera on
**Persona:** Theo Nakamura — 23, freelance designer/barista in Austin, ADHD, undercharging, burning out

---

## [0:00–0:30] Team Intro

**[Camera on]**

"Hey, I'm Michael — I worked on the frontend, UX, and infrastructure."

"I'm Kusum — I handled the backend and data design."

"And I'm Saksham — I built the agent pipeline and external integrations."

"Together we built **Questline** — let's show you what it does."

---

## [0:30–1:00] Elevator Pitch

**[Camera on]**

"Theo is 23, freelancing in Austin — ADHD, undercharging, credit card debt creeping up. And no single app in his life can see the full picture.

Questline connects his calendar, finances, mood logs, and social data to find the patterns that are actually shaping his future — and then gives him a concrete path to change them.

It's not a dashboard or a chatbot. It's an agent that knows your whole life and helps you do something about it."

---

## [1:00–1:30] Ingest Screen — Knowledge Graph

**[Screen share]**

"We start on the Ingest screen. This is the knowledge graph of Theo's data — transactions, calendar, lifelog, social posts — structured and stored in LightRAG, backed by Neo4j and Qdrant. Watch the nodes and edges build out as it loads — each node is an entity extracted from Theo's data, each edge is a relationship the system found between them.

---

## [1:30–2:15] Patterns Screen

**[Navigate to Patterns]**

"Now the agent surfaces cross-domain behavioral patterns. This is one of the key value propositions of Questline.

Taking a look at **Burnout Cascade**. When Theo's meeting density exceeds 30 hours in a week, his exercise drops to near zero *and* his food delivery spend triples. No budget or calendar app sees that. You only see it when you fuse the data together.

Each pattern cites the specific records it came from — expand it and you can see the exact calendar event and transaction that triggered it. The pipeline runs these through an LLM on every cycle, and caches the result so it only reruns when the underlying data actually changes."

---

## [2:15–2:45] Questlines Screen

**[Navigate to Questlines]**

"Based on those patterns, the agent generates three life trajectories — one year, five years, ten years out. Most likely, possible, aspirational.

These aren't generic advice. Each scenario references the patterns that make it likely or unlikely for *Theo specifically*. We pick the five-year scenario — freelancing full-time, motion design retainer clients — and hand it to the Action Planner."

---

## [2:45–3:15] Actions Screen

**[Navigate to Actions]**

"The Action Planner reads the selected scenario alongside Theo's live calendar and recent transactions and generates time-bound micro-actions. Each one links back to a specific data record.

This action — 'Send a rate proposal to NovaBit before the March 7th discovery call' — is grounded in `cal_0081`, the actual calendar event in Theo's data. It's not advice. It's a next step with a deadline, a reason, and a receipt."

---

## [3:15–4:00] Chat + Notion Integration

**[Navigate to Chat]**

"Finally — chat. Theo can have a real conversation with the agent about any of this. But more importantly, the agent can *act*.

Watch this."

**[Type or speak into mic:]**
*"Hey, I just got off the NovaBit discovery call. They're interested. Can you update my Notion client pipeline with NovaBit as a new lead at the proposal stage, $150/hr motion design retainer?"*

"The agent picks that up, calls the Notion integration through Composio, and writes a new entry directly into Theo's client pipeline — name, rate, stage, source. No copy-paste, no switching tabs.

This is what Track 2 looks like when it actually works. It's not a companion that *talks* to you. It's one that *moves* with you."

---

## [4:00–4:40] How We Built It

**[Camera on, briefly show architecture or terminal]**

"Under the hood, Questline is a four-step pipeline. First, a deterministic Python extractor pulls Theo's JSONL data — transactions, calendar, lifelog — into compact typed structs. No LLM involved, deterministic, fast.

Second, we send those structs to an LLM in JSON output mode — it returns a structured `PatternReport` with cross-domain correlations. Third, a Scenario Generator takes that report and produces three `ScenarioSet` objects across time horizons. Fourth, the Action Planner reads the selected scenario and live data to output `ActionPlan` with actions grounded in specific data refs — like `cal_0081`.

The whole thing is hash-cached. We sha256 the assembled prompt inputs. If Theo's data hasn't changed, we skip the LLM entirely and return the cached result instantly.

The knowledge graph runs on LightRAG backed by Neo4j and Qdrant. When you ask the chat agent a question, we classify the intent — factual, pattern, advice, emotional — and query LightRAG in the corresponding mode. Global search for patterns, hybrid for advice, skip the graph entirely for emotional messages. That context gets injected into the system prompt alongside the active scenario and action plan.

The Notion integration goes through Composio. One API call — `NOTION_CREATE_DATABASE_PAGE` — and it writes directly to Theo's pipeline. The frontend is React 19 with Vite, the KG visualization is Sigma.js, streaming is SSE using the Vercel AI SDK format. Backend is FastAPI with a Stripe-style `/v1/` API.

Every step has a 30-second timeout with graceful fallback to demo mode. Nothing breaks on stage."

---

## [4:40–5:00] Close — So What?

**[Camera back on]**

"Questline is the first tool that sees Theo's life the way Theo actually lives it — across apps, across domains, across time.

The Burnout Cascade pattern, the NovaBit opportunity, the five-year scenario — none of that exists in any single app. We had to build the pipeline that connects them, the agent that reasons across them, and the integrations that act on them.

That's Questline. Thanks for watching."

---

## Timing Guide

| Section | Duration | Cumulative |
|---------|----------|------------|
| Team Intro | 0:30 | 0:30 |
| Elevator Pitch | 0:30 | 1:00 |
| Ingest / Knowledge Graph | 0:30 | 1:30 |
| Patterns | 0:45 | 2:15 |
| Questlines | 0:30 | 2:45 |
| Actions | 0:30 | 3:15 |
| Chat + Notion | 0:45 | 4:00 |
| How We Built It | 0:40 | 4:40 |
| Close | 0:20 | 5:00 |

---

## Pre-Record Checklist

- [ ] App running at localhost:8000, Theo's data pre-loaded
- [ ] Knowledge graph visible and animated on ingest screen
- [ ] Patterns loaded (Burnout Cascade visible, data_refs expandable)
- [ ] NovaBit calendar event (`cal_0081`) in data
- [ ] Notion pipeline page open in another tab (show before/after)
- [ ] Mic working for voice input demo
- [ ] Do one full run-through for timing
- [ ] Mute mic during any LLM loading pauses, then cut back in
