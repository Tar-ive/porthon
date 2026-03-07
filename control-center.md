# 🎮 Questline Control Center

**Runtime:** `http://localhost:8000` | **Mode:** Demo (livemode: false) | **Persona:** Theo Nakamura (p05)

---

## 📊 Active Scenario

| Field | Value |
|-------|-------|
| **Title** | Conversion-First Freelance Stabilization |
| **Horizon** | 1yr |
| **Likelihood** | most_likely |
| **Summary** | Theo shifts focus from endless learning to revenue conversion by productizing core design offers, tightening follow-up cadence, and protecting deep-work blocks. |
| **Tags** | conversion, revenue, focus, freelance |
| **Patterns** | public_private_delta, learning_vs_conversion_mismatch, financial_stress_triangulation |

---

## 👷 Workers (6 Total)

| Worker | Label | Status | Queue Depth | Last Error |
|--------|-------|--------|-------------|------------|
| `kg_worker` | KG Search | 🟢 ready | 0 | — |
| `calendar_worker` | Calendar Scheduler | 🟢 ready | 0 | — |
| `notion_leads_worker` | Notion Leads Tracker | 🟢 ready | 0 | — |
| `notion_opportunity_worker` | Notion Opportunity Tracker | 🟢 ready | 0 | — |
| `facebook_worker` | Facebook Publisher | 🟢 ready | 0 | — |
| `figma_worker` | Figma Plan Generator | 🟢 ready | 0 | — |

---

## 📋 Latest Cycle Tasks (6 Executed)

| Task ID | Worker | Action | Priority | Status |
|---------|--------|--------|----------|--------|
| `task_15d6ed6f-...` | kg_worker | search | 10 | ✅ completed |
| `task_215d3140-...` | calendar_worker | sync_schedule | 20 | ✅ completed |
| `task_825deefb-...` | notion_leads_worker | create_pipeline | 30 | ✅ completed |
| `task_c7217a4c-...` | notion_opportunity_worker | create_workspace | 30 | ✅ completed |
| `task_bb9c2cce-...` | facebook_worker | draft_posts | 40 | ✅ completed |
| `task_a9b55b87-...` | figma_worker | generate_challenge | 40 | ✅ completed |

---

## 📋 Previous Cycle Tasks (6 Executed)

| Task ID | Worker | Action | Priority | Status |
|---------|--------|--------|----------|--------|
| `task_87cddcfd-...` | kg_worker | search | 10 | ✅ completed |
| `task_d8b77ee2-...` | calendar_worker | sync_schedule | 20 | ✅ completed |
| `task_1d74f2b5-...` | notion_leads_worker | create_pipeline | 30 | ✅ completed |
| `task_2dd8f689-...` | notion_opportunity_worker | create_workspace | 30 | ✅ completed |
| `task_a124d75d-...` | facebook_worker | draft_posts | 40 | ✅ completed |
| `task_27f17df5-...` | figma_worker | generate_challenge | 40 | ✅ completed |

---

## 📅 Generated Artifacts (Demo Mode)

### Calendar Events
- **Deep Work: Portfolio Sprint (UT Library)** — 180 min focus block
- **Deep Work: Client Deliverable Block (UT Library)** — 180 min focus block
- **Admin Sprint: Invoice Follow-up** — 45 min admin
- **Debt-Paydown Review** — 30 min review

### Notion Leads (Client Pipeline)
- Referral Lead (Referral source, Lead status)
- Portfolio Lead (Portfolio source, Proposal status)
- Direct Lead (Direct source, Lead status)

### Figma Challenge Briefs
1. Conversion-first landing refresh for a local service brand
2. Brand motion system for an Austin creator collective
3. Portfolio case-study narrative sprint with measurable KPI

### Weekly Milestones
- Week 1: Brief + concept frames
- Week 2: Mid-fidelity exploration
- Week 3: Final polish + share-out

---

## 💬 Facebook Comments (Pending Replies)

| Comment ID | Post | Message | Status |
|-----------|------|---------|--------|
| `c_inject_001` | p_seed_001 | Injected comment | ✅ ready_to_send |
| `c_seed_001` | p_seed_001 | Seed comment one | ✅ ready_to_send |
| `c_seed_002` | p_seed_001 | Seed comment two | ✅ ready_to_send |
| `ui_seed_001` | ui_post_001 | Love your recent update. | ✅ ready_to_send |
| `ui_seed_002` | ui_post_001 | Can you share milestones? | ✅ ready_to_send |

---

## 🔄 Cycle History (Last 5)

| Cycle ID | Trigger | Executed | Failed | Duration |
|----------|---------|----------|--------|----------|
| `cycle_d3954855-...` | demo.workflow.proactive.commit | 6 | 0 | 1ms |
| `cycle_69cce8bf-...` | scenario_activated | 6 | 0 | 1ms |
| `cycle_72ce8776-...` | tick | — | — | 2ms |
| `cycle_f5a507fb-...` | tick | — | — | 2ms |
| `cycle_a2d7c9c6-...` | tick | — | — | 2ms |

---

## 🎯 Value Signals Detected

| Signal | Description |
|--------|-------------|
| **public_private_delta** | Public confidence is ahead of private certainty. |
| **learning_vs_conversion_mismatch** | Learning intensity outpaces direct revenue conversion loops. |
| **financial_stress_triangulation** | Debt stress is an execution drag, not just a budgeting issue. |
| **adhd_execution_constraints** | Execution improves when tasks are chunked and environment-scaffolded. |

---

## 🔌 Integrations Available

| Integration | Status | Description |
|-------------|--------|-------------|
| **Neo4j** | 🔴 Not connected | Knowledge Graph storage |
| **Qdrant** | 🔴 Not connected | Vector storage for RAG |
| **Composio** | Available | Tool execution framework |
| **OpenAI** | ✅ Connected | LLM via OpenRouter (Grok-4.1-fast) |
| **Facebook** | 🔵 Demo mode | Social media monitoring |
| **Notion** | 🔵 Demo mode | Lead/opportunity tracking |
| **Calendar** | 🔵 Demo mode | Schedule sync |

---

## 📈 API Quick Reference

```bash
# Health check
curl http://localhost:8000/v1/health -H "Authorization: Bearer sk_demo_default"

# Full runtime state
curl http://localhost:8000/v1/runtime -H "Authorization: Bearer sk_demo_default"

# List scenarios
curl http://localhost:8000/v1/scenarios -H "Authorization: Bearer sk_demo_default"

# Activate new quest
curl -X POST http://localhost:8000/v1/quests \
  -H "Authorization: Bearer sk_demo_default" \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "scen_002"}'

# List approvals
curl http://localhost:8000/v1/approvals -H "Authorization: Bearer sk_demo_default"

# Event stream (SSE)
curl -N http://localhost:8000/v1/events/stream \
  -H "Authorization: Bearer sk_demo_default"
```

---

*Last updated: 2026-03-05 02:35 UTC*
