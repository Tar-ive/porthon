# Questline — Demo Video Script

**Target length:** 4:00–4:30
**Format:** Loom screen recording with camera on
**Persona:** Theo — freelance designer, $5,840 in credit card debt, undercharging clients, wants to expand his business

---

## SECTION 1 — Team Intro (0:00–0:25)

**[Camera on, no screen share yet]**

> "Hey everyone, we're [Team Name]. I'm [Name], I led the agent architecture and LightRAG pipeline. This is [Name], who built the frontend and Questline UI. And [Name], who handled our tool integrations — Google Calendar, Notion, and Figma workers."

> "We built **Questline** for Track 2 — delivering personal value through an AI agent."

---

## SECTION 2 — Elevator Pitch (0:25–0:55)

**[Still camera, maybe show the Questline logo/landing briefly]**

> "Here's the problem: if you're a freelancer, nobody's watching out for you. No manager notices you're undercharging. No financial advisor sees the credit card debt creeping up. You've got data scattered across your bank, your calendar, your health apps — but no one is connecting the dots."

> "Questline is a personal AI companion that ingests your real behavioral data, builds a knowledge graph of your life patterns, and then does something no other tool does — it surfaces possible goal states based on your interests and life circumstances, lets you choose one as your questline, and takes real action in your real tools *today* to move you toward it. Not generic advice. Real calendar blocks. Real Notion pipelines. Figma design challenges scoped to your skill level. All grounded in your actual data."

---

## SECTION 3 — Live Demo (0:55–3:20)

### 3A — Data Ingest & Pattern Detection (0:55–1:40)

**[Screen share: Questline app, show the knowledge graph or loading state]**

> "Let's walk through this as Theo, a 27-year-old freelance designer in Austin. When Theo connects his data, our LightRAG pipeline kicks in — ingesting his synthetic data: 2,800 financial transactions, a year of health logs, 1,200 calendar events, and his social activity. All of that gets normalized into a knowledge graph that captures entities, relationships, and temporal patterns."

**[Show loading animation completing, then patterns screen]**

> "The agent's first job is pattern extraction. It queries the knowledge graph autonomously — Theo never has to ask the right question."

**[Show the patterns list, highlight a cross-domain insight]**

> "Single-domain patterns are useful — spending's up 14%, exercise dropped 40%. But the cross-domain correlations are what Theo can't see on his own."

**[Point to Pattern #6: burnout cascade]**

> "This one: after weeks with 30+ hours of meetings, Theo's exercise drops and his delivery food spending triples. That's a burnout cascade — financial, physical, and time domains all linked. No single app surfaces that."

### 3B — Questline Selection (1:40–2:10)

**[Navigate to Questlines screen]**

> "Based on Theo's patterns, interests, and life circumstances, the agent generates possible questlines — concrete goal states Theo might want to work toward."

**[Show the questline cards]**

> "These aren't predictions. They're options. The Comfortable Drift — keep the current trajectory. The Rebalance — pay down debt and restructure time to grow the business sustainably. The Transformation — an aggressive push toward financial freedom and peak performance."

> "Each questline references the specific patterns that make it relevant to Theo. It's not a personality quiz — it's grounded in what the knowledge graph actually knows about his life."

**[Click "The Rebalance" → "Lock In My Quest"]**

> "Theo picks The Rebalance. He wants to pay down his $5,800 in credit card debt and grow his freelance business without burning out. Now the action planner kicks in."

### 3C — Weekly Actions & Tool Integration (2:10–3:00)

**[Show the Dashboard → Weekly Actions view]**

> "The LLM generates 10 concrete micro-actions for this week, mapped to specific days and times. Not 'exercise more' — 'Walk at 6pm Monday, your calendar is free.' Not 'save money' — 'Transfer $50 to savings at 7:30am, that's $2,600 a year.'"

> "Each action has a rationale that ties back to a detected pattern and explains how it compounds toward the Rebalance questline."

**[Show Google Calendar with blocks being created]**

> "These actions aren't just suggestions sitting in a list. Questline writes directly to Theo's Google Calendar — real time blocks with context so he knows exactly what to do and why."

**[Switch to show Notion workspace — task board / freelance pipeline]**

> "And here's the Notion integration. The agent builds and maintains a freelance pipeline for Theo — tracking active client projects, proposals in flight, and revenue targets tied to his debt payoff goal. When Theo closes a project or lands a new lead, the agent updates the pipeline and recalculates whether he's on track. This isn't a template Theo has to maintain — the agent writes to it proactively."

**[Switch to show Figma integration — a design challenge or portfolio prompt]**

> "On the Figma side, the agent generates scoped design challenges matched to Theo's current skill level — one portfolio piece, four hours, aligned with what School of Motion courses he's been taking. It can create project briefs, set up frames, and give Theo a runway to build the portfolio that justifies raising his rates from $600 to $2,200 per project. The agent even drafts a social post for when the piece is done."

**[Show proactive behavior — new data triggers task updates]**

> "And this is the proactive layer. When new personal data enters the system — a new transaction, a calendar change, a completed task — the agent detects it, re-queries the knowledge graph, and updates Theo's actions across all three tools automatically. No manual syncing. No 'open the app and check.' The companion is always working."

### 3D — Chat Agent (3:00–3:20)

**[Switch to Chat/Adjust tab]**

> "But life doesn't go according to plan. Theo can chat with the agent to adjust."

**[Type or click: "The 30-minute walks feel like too much"]**

> "The agent doesn't just say 'try harder.' It responds with data: 'Start with 10 minutes. Your data shows even short walks improve your sleep score.' It adapts the plan to what Theo will actually do — that's the Atomic Habits philosophy. Tiny, achievable, compounding."

**[Show the agent suggesting a modified action]**

> "It can also rescale savings targets, swap actions to different days, or replace an action entirely — always grounded in what the knowledge graph knows about Theo and his chosen questline."

---

## SECTION 4 — How We Built It (3:20–3:55)

**[Optionally show architecture diagram or terminal briefly]**

> "Under the hood: our agent is a multi-step pipeline running on [DGX Spark / your hardware]. Step one, LightRAG ingests and indexes personal data into a knowledge graph with entity extraction and temporal relationships. Step two, the pattern extractor queries the graph autonomously to find single-domain trends and cross-domain correlations. Step three, the questline generator surfaces possible goal states grounded in those patterns and the user's circumstances. Step four, the action planner generates daily micro-actions and the tool workers execute them — writing calendar blocks, updating Notion databases, and scoping Figma design challenges, all through Composio."

> "The frontend is React. The agent backend is Python with a Claude API chain using tool use — the LLM can query LightRAG, read and write to Google Calendar, Notion, and Figma without human prompting. When new data enters the system, the proactive loop detects changes, re-queries the graph, and updates Theo's plan across all connected tools."

> "The hardest engineering challenge was making the tool integrations genuinely useful, not just connected. The Notion worker doesn't just create a page — it maintains a living freelance pipeline that updates when Theo's data changes. The Figma worker doesn't just open a file — it generates scoped creative briefs matched to his skill progression. That's the depth that separates a real agent from an API wrapper."

---

## SECTION 5 — So What? (3:55–4:20)

**[Camera on, direct to judges]**

> "So why does this matter?"

> "Theo's data already existed. His bank had his transactions. His phone had his steps. His calendar had his meetings. But nothing connected them. Nobody told him that his Thursday delivery spending was a stress response to his Wednesday meeting load — and that breaking that one cycle is the lever that makes his debt payoff plan actually work."

> "Questline doesn't give Theo a to-do list. It gives him a questline — a goal state he chose for himself — and then a companion that takes real action in his real tools to get him there. Calendar blocks that protect his recovery time. A Notion pipeline that tracks his freelance revenue against his debt. Figma challenges that build the portfolio he needs to charge what he's worth."

> "This is personal data working *for* the person. That's the promise of Track 2, and that's what we built. Thanks."

---

## Demo Checklist (pre-record)

- [ ] App loaded with Theo's synthetic data pre-ingested as fallback
- [ ] LightRAG knowledge graph populated and queryable
- [ ] Google Calendar connected and showing empty slots for action blocks
- [ ] Notion workspace visible with freelance pipeline board
- [ ] Figma integration ready to show a generated design challenge
- [ ] Chat agent responding in real-time (or near real-time with acceptable latency)
- [ ] Screen recorder set up with camera on
- [ ] Practice run completed under 4:30
- [ ] All team members know their intro lines

## Timing Guide

| Section | Duration | Cumulative |
|---------|----------|------------|
| Team Intro | 0:25 | 0:25 |
| Elevator Pitch | 0:30 | 0:55 |
| Demo: Data Ingest & Patterns | 0:45 | 1:40 |
| Demo: Questline Selection | 0:30 | 2:10 |
| Demo: Actions, Calendar, Notion, Figma | 0:50 | 3:00 |
| Demo: Chat Agent | 0:20 | 3:20 |
| How We Built It | 0:35 | 3:55 |
| So What / Close | 0:25 | 4:20 |