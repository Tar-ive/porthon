# Hackathon Submission Requirements

## Required Submission Checklist

- [ ] **Team Name**
- [ ] **Project Description (2-3 sentences)**
- [ ] **Track selected**
- [ ] **3–5 min demo video** (Unlisted YouTube/Vimeo or Loom)
  - [Demo Video Instructions](https://www.notion.so/Demo-Video-Instructions-30e0743dff2c8174af0ee640b92a63d4?pvs=21)
- [ ] **GitHub repo link** (public or invite judges). Must include a **README** with:
  - [ ] Quick start (commands to run)
  - [ ] Tech stack & architecture diagram (simple is fine)
  - [ ] How to reproduce the demo (env vars, API keys, sample .env)
  - [ ] Datasets used and their source
  - [ ] Known limitations & next steps
- [ ] **Deployed URL (if any)** or short screen capture of the working app
- [ ] **Team roster** (names, roles, contacts)

---

## Judging Criteria

**Philosophy:** A winning project isn't just a slide deck or a simple API wrapper — it's a functioning system that ingests personal data, processes it meaningfully, and produces something genuinely valuable for the person whose data it is.

**Total: 100 Points**

---

### 1. Completeness — 50 pts

*Did they actually build a working system?*

- Does the system successfully complete the full data workflow without crashing? Can a judge follow the core loop from data input to meaningful output, live, without it breaking?
- Is there significant depth under the hood? Did they build a real pipeline — e.g., a consent layer, a RAG system, a personalized inference loop, custom logic — rather than a static dashboard or a thin API wrapper?

> A project that partially works but shows real engineering depth will score better than a polished demo with nothing behind it.

---

### 2. Meets Track Criteria — 25 pts

*Did they actually solve the problem they chose?*

- Does the project address the stated goal of their chosen track?
  - Track 1 should move or structure data
  - Track 2 should deliver personal value through an AI agent
  - Track 3 should surface insight from a user's own data
- Can they articulate the "data story"? Who owns the data? Where does it come from? How is consent handled? Why does this build something better for the individual?

---

### 3. Innovation — 15 pts

*Did they push the boundaries?*

- Did they combine data sources or approaches in a novel way? (e.g., fusing AI conversation history with calendar data to detect burnout patterns — not just displaying data in a new format)
- Is the insight non-obvious and valuable? "This person spends a lot on food" is obvious. "This person's discretionary spending spikes in the week after high-stress calendar periods" is valuable.

---

### 4. User Experience — 10 pts

*Is it actually usable?*

- Could a real person — not a developer — use this tool to make a decision or understand something about themselves?
- Is the output clear and actionable? Judges will ask: would Jordan, Maya, Darius, Sunita, or Theo actually want this?
