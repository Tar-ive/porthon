# Milestone 2: Deep Agents — Execution Layer for Questline Simulations

## Section 1: The Questline Agent Loop

**Profile → Simulate → Choose → Execute → Measure → Re-simulate**

Questline's pipeline generates scenarios and actions, but today they're only *shown* — never *executed*. Milestone 2 closes this loop.

When Theo (or any profiled persona) consciously chooses a questline, deep agents in the background execute the actions: creating calendar blocks, setting up Notion workspaces, generating design challenges, scheduling posts — all personalized from profiling context.

### Why Agents, Not Just Recommendations

Theo's execution score is **0.45** — he knows what to do but can't follow through (ADHD admin paralysis, indicator 0.80). The agents *do the admin for him*. They don't just suggest "block time for invoicing" — they create the actual calendar event with ADHD-aware timing.

### The Conscious Choice Moment

```
Existing Pipeline (M1):  Profiler → Extractor → Scenarios → Actions
                                                      │
                                              User sees 3 scenarios
                                              on the Questline UI
                                                      │
                                              ┌───────▼────────┐
                                              │ CONSCIOUS       │
                                              │ CHOICE          │
                                              │ "I choose the   │
                                              │  Freelance      │
                                              │  Velocity       │
                                              │  questline"     │
                                              └───────┬────────┘
                                                      │
New (M2):  QuestOrchestrator decomposes → agent tasks → QuestPlan
           CalendarCoach | FigmaLearning | NotionOrganizer | ContentCreator
```

---

## Section 2: Agent Specifications

### 2.1 QuestOrchestrator (coordinator)

**Purpose:** Receives the chosen scenario + action plan + profile scores. Decomposes actions into agent-specific tasks, runs all agents in parallel via `asyncio.gather()`, assembles the final `QuestPlan`.

**Input:** `QuestContext` (scenario, action_plan, profile_scores, extracted_data, persona_id)
**Output:** `QuestPlan` (calendar, learning, workspace, content, narrative, next checkpoint)

**Logic:**
- Maps each action to the right agent by keyword analysis (schedule/block → CalendarCoach, portfolio/design → FigmaLearning, organize/track → NotionOrganizer, post/share → ContentCreator)
- Checks archetype to decide which agents to activate
- Runs selected agents concurrently
- Generates a cohesive narrative connecting all outputs

### 2.2 CalendarCoach

**Purpose:** Schedules ADHD-aware time blocks from the action plan into Google Calendar.

**Profiling scores used:**
- `adhd_indicator` (0.80) → 3h hyperfocus blocks for creative, 25min pomodoros for admin, 10min transition buffers
- `execution` (0.45) → prioritize actions that directly improve measurable outcomes
- `financial_stress` (0.75) → front-load revenue-generating tasks

**Input:** `QuestContext`
**Output:** `CalendarPlan` (events, weekly_rhythm_summary, adhd_accommodations, quest_connection)

**Composio actions:** `GOOGLECALENDAR_CREATE_EVENT`, `GOOGLECALENDAR_FIND_FREE_SLOTS`

### 2.3 FigmaLearning

**Purpose:** Generates design challenges tied to scenario skill requirements. Converts learning into portfolio-worthy execution artifacts.

**Profiling scores used:**
- `growth` (0.65) → challenge difficulty calibration
- `execution` (0.45) → portfolio-worthy challenges that produce tangible outputs

**Input:** `QuestContext`
**Output:** `LearningPlan` (challenges, milestones, weekly_practice_hours, portfolio_targets, quest_connection)

### 2.4 NotionOrganizer

**Purpose:** Creates a Notion workspace structure aligned to the chosen questline.

**Profiling scores used:**
- `financial_stress` (0.75) → debt payoff tracker as first page
- `execution` (0.45) → simplified views (not complex dashboards)
- `adhd_indicator` (0.80) → single-page views over multi-layer navigation

**Input:** `QuestContext`
**Output:** `NotionWorkspace` (pages, setup_summary, quest_connection)

**Composio actions:** `NOTION_CREATE_PAGE`, `NOTION_CREATE_DATABASE`

### 2.5 ContentCreator

**Purpose:** Schedules social posts that bridge the public/private persona gap and track questline progress.

**Profiling scores used:**
- `deltas["public_private"]` (0.40) → "learning in public" posts that authentically bridge the gap
- `growth` (0.65) → content aligned to learning milestones

**Input:** `QuestContext`
**Output:** `ContentCalendar` (posts, posting_cadence, brand_voice_notes, quest_connection)

**Composio actions:** `FACEBOOK_CREATE_POST`, `FACEBOOK_SCHEDULE_POST`

### 2.6 OutcomeCollector

**Purpose:** Collects real outcome data via Composio APIs to measure quest completion. Deterministic — no LLM needed.

**Input:** `QuestPlan` + `PersonaConfig`
**Output:** `QuestOutcome` (action_outcomes, completion_rate, profile_score_delta)

**Composio actions:** `GOOGLECALENDAR_EVENTS_LIST`, `NOTION_SEARCH`, `FACEBOOK_GET_POST`

---

## Section 3: Personalization via Profiling Context

Each agent receives `ProfileScores` from PROFILING_MATH so it adapts behavior:

| Score | Value (Theo) | Agent Impact |
|-------|-------------|--------------|
| ADHD indicator | 0.80 | CalendarCoach: 3h hyperfocus blocks + 25min pomodoros for admin |
| Financial stress | 0.75 | NotionOrganizer: debt payoff tracker as first page |
| Public/private delta | 0.40 | ContentCreator: "learning in public" posts bridge gap |
| Growth | 0.65 | FigmaLearning: portfolio-worthy challenges |
| Execution | 0.45 | All agents: prioritize tangible outputs over planning |

---

## Section 4: Theo's Specific Questline Workflow

### Top 5 Quests for Theo

1. **Freelance Velocity** — raise invoice win rate from 13% to 40%
2. **Spatial Computing Convergence** — pivot 3D/AR skills into career advantage
3. **Austin Community Anchor** — build local professional network
4. **Debt Velocity** — eliminate $15k debt in 18 months
5. **Location Clarity** — resolve Austin vs. move decision with data

### Example: "Freelance Velocity" Agent Outputs

**CalendarCoach:** Morning 9am-12pm hyperfocus blocks (Mon/Wed/Fri) for client work. 25min pomodoro at 2pm for invoice admin. Buffer blocks before/after client calls.

**FigmaLearning:** "Design a brand identity for a fictional Austin taco truck" — simulates the $2.2k projects Theo needs to win. Portfolio-worthy output.

**NotionOrganizer:** Client pipeline database (Lead → Proposal → Active → Invoiced → Paid), rate calculator page, project tracker.

**ContentCreator:** Weekly "design process" post showing work-in-progress. Aligned to FigmaLearning milestone completion.

---

## Section 5: Continuous Learning Loop

```
Quest Executed → Outcome Signals → Profile Updated → Next Quest Refined
                      │
           Calendar: did Theo attend?
           Notion: did he update tracker?
           Social: did he post?
           Transactions: revenue change?
                      │
               OutcomeCollector
                      │
               QuestMemory (persistent)
               - past quest completion rates
               - what worked / what didn't
               - profile score trajectory
```

### Re-simulation Trigger

When `completion_rate < 0.5`, suggest re-running scenario generation with updated QuestMemory so the next quest adapts (e.g., "evening blocks don't work → switch to morning only").

---

## Section 6: Persona-Agnostic Architecture

1. **ProfileScores are the interface** — agents never hardcode persona names or goals
2. **QuestContext is parameterized** — `persona_id` determines data directory
3. **Archetype-driven agent selection:**
   - "Emerging Talent" → all 5 agents
   - "Reliable Operator" → skip CalendarCoach, focus on growth agents
   - "At Risk" → heavy CalendarCoach + NotionOrganizer
   - "Compounding Builder" → light touch, mainly ContentCreator

4. **PersonaConfig** for multi-user support:
```python
class PersonaConfig(BaseModel):
    persona_id: str
    data_dir: str
    composio_entity_id: str | None = None
    enabled_agents: list[str]
    quest_memory_path: str
```

---

## Section 7: Composio Integration Map

| Agent | Composio Actions | Auth Required |
|-------|-----------------|---------------|
| CalendarCoach | `GOOGLECALENDAR_CREATE_EVENT`, `GOOGLECALENDAR_FIND_FREE_SLOTS` | Google OAuth |
| NotionOrganizer | `NOTION_CREATE_PAGE`, `NOTION_CREATE_DATABASE` | Notion OAuth |
| ContentCreator | `FACEBOOK_CREATE_POST`, `FACEBOOK_SCHEDULE_POST` | Facebook OAuth |
| OutcomeCollector | `GOOGLECALENDAR_EVENTS_LIST`, `NOTION_SEARCH` | Reuses above |
| FigmaLearning | None (LLM-only, no external API) | — |

**Graceful degradation:** Without `COMPOSIO_API_KEY`, agents generate plans but skip execution. The QuestPlan is still returned with full detail — just not pushed to external services.

**Direct execution pattern (no LLM framework dependency):**
```python
from composio import Composio
composio = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"))
result = composio.tools.execute("GOOGLECALENDAR_CREATE_EVENT", user_id=entity_id, arguments={...})
```

---

## Section 8: Pydantic Schemas

All models defined in `src/backend/agents/models.py`. Key types:

- `ProfileScores` — bridges profiling math → agents
- `QuestContext` — input to every agent
- `CalendarEvent`, `CalendarPlan` — CalendarCoach I/O
- `DesignChallenge`, `LearningMilestone`, `LearningPlan` — FigmaLearning I/O
- `NotionPage`, `NotionWorkspace` — NotionOrganizer I/O
- `ScheduledPost`, `ContentCalendar` — ContentCreator I/O
- `ActionOutcome`, `QuestOutcome`, `QuestMemory` — continuous learning
- `QuestPlan` — orchestrator output
- `PersonaConfig` — multi-persona support

See `src/backend/agents/models.py` for full definitions.

---

## Section 9: Technical Architecture

### File Structure
```
src/backend/agents/
  __init__.py
  models.py              # All Pydantic I/O contracts
  base.py                # BaseAgent ABC: plan → execute → verify
  composio_tools.py      # Composio SDK wrapper (graceful degradation)
  calendar_coach.py      # ADHD-aware scheduling
  figma_learning.py      # Design challenge generation
  notion_organizer.py    # Workspace creation
  content_creator.py     # Social content scheduling
  quest_orchestrator.py  # Coordinator: decomposes → runs → assembles
  outcome_collector.py   # Outcome measurement (deterministic)
```

### Integration with Existing Pipeline

- `extractor.py` provides `extract_persona_data()` — unchanged
- `scenario_gen.py` produces scenarios — unchanged
- `action_planner.py` produces actions — unchanged
- New `/api/quest` endpoint chains: extract → scenarios → actions → agents

### API Endpoints

- `POST /api/quest` — accepts `{"scenario_id": "s_001"}`, returns `QuestPlan`
- `POST /api/quest/outcomes` — triggers OutcomeCollector, returns `QuestOutcome`

### BaseAgent Pattern

```python
class BaseAgent(ABC):
    def __init__(self, context: QuestContext): ...
    async def plan(self) -> dict: ...      # LLM generates structured plan
    async def execute(self) -> T: ...      # Composio executes (or dry-run)
    async def verify(self) -> bool: ...    # Check execution success
    async def run(self) -> T: ...          # plan → execute → verify lifecycle
```

Each agent follows the same AsyncOpenAI + JSON mode pattern established in `scenario_gen.py`.
