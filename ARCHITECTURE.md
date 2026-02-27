# System Architecture: Hyperfocus Monetization & Career Trajectory Advisor

> An ADHD-optimized career intelligence platform that captures hyperfocus episodes from conversation data, maps skill acquisition to market demand, and provides dopamine-friendly micro-milestone career pathing — powered by NLWeb (conversational protocol), LongMemEval memory framework (temporal knowledge graph), and Alchemy (on-chain skill credentials + token rewards).

---

## The Problem → The System

```
ADHD Brain                              What Our System Does
─────────────                           ────────────────────
Hyperfocus on Python for 3 weeks  →  Captures depth + duration from chat data
  then pivots to Blender 3D       →  Maps as skill cluster, not "quitting"
  then back to Python + ML        →  Detects convergence: "3D + ML = spatial computing"
                                  →  Matches to market: "Unity ML, AR/VR roles paying $140k"
                                  →  Generates micro-milestone learning path
                                  →  Mints skill credentials on-chain (Alchemy)
                                  →  Gamified dopamine loop: complete step → token reward
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                             │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Questline UI │  │ MCP Agents   │  │ Hiring       │  │ Enterprise   │   │
│  │ (User App)   │  │ (Claude,     │  │ Marketplace  │  │ Talent API   │   │
│  │              │  │  Copilot...) │  │ (Web App)    │  │ (B2B)        │   │
│  │ • Skill map  │  │              │  │              │  │              │   │
│  │ • Milestones │  │ Query user's │  │ Match ADHD   │  │ Search for   │   │
│  │ • Career path│  │ profile as   │  │ pros to      │  │ cognitive    │   │
│  │ • Rewards    │  │ an MCP tool  │  │ aligned roles│  │ profiles     │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         └──────────────────┴─────────────────┴─────────────────┘           │
│                                    │                                        │
│                     REST /ask + /mcp (Schema.org JSON)                      │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
╔═════════════════════════════════════════════════════════════════════════════╗
║                     NLWeb CONVERSATIONAL LAYER                              ║
║                                                                             ║
║  ┌─────────────────────────────────────────────────────────────────────┐   ║
║  │              PARALLEL PRE-RETRIEVAL ANALYSIS                        │   ║
║  │                                                                     │   ║
║  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │   ║
║  │  │ Decontextualize │ │ Hyperfocus      │ │ Memory          │      │   ║
║  │  │                 │ │ Detection       │ │ Extraction      │      │   ║
║  │  │ "How's that     │ │                 │ │                 │      │   ║
║  │  │  going?" →      │ │ Is user in a    │ │ Extract skills, │      │   ║
║  │  │ "How is Theo's  │ │ hyperfocus      │ │ interests,      │      │   ║
║  │  │  Blender        │ │ episode? What   │ │ engagement      │      │   ║
║  │  │  learning       │ │ domain? What    │ │ signals from    │      │   ║
║  │  │  going?"        │ │ depth level?    │ │ every turn      │      │   ║
║  │  └─────────────────┘ └────────┬────────┘ └────────┬────────┘      │   ║
║  │                               │                    │               │   ║
║  │                    ┌──────────▼────────────────────▼──────────┐    │   ║
║  │                    │  COGNITIVE FINGERPRINT UPDATER            │    │   ║
║  │                    │                                          │    │   ║
║  │                    │  • What problem types sustain attention?  │    │   ║
║  │                    │  • What triggers disengagement?           │    │   ║
║  │                    │  • What's the typical hyperfocus cycle?   │    │   ║
║  │                    │  • Which domains show accelerated depth?  │    │   ║
║  │                    └──────────┬───────────────────────────────┘    │   ║
║  └───────────────────────────────┼─────────────────────────────────────┘   ║
║                                  │                                         ║
║  ┌───────────────────────────────▼─────────────────────────────────────┐   ║
║  │              TOOL ROUTING (LLM selects from tools.xml)              │   ║
║  │                                                                     │   ║
║  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │   ║
║  │  │ Skill Portfolio │ │ Career Match    │ │ Hyperfocus      │      │   ║
║  │  │ Tool            │ │ Tool            │ │ Tracker Tool    │      │   ║
║  │  │                 │ │                 │ │                 │      │   ║
║  │  │ "What skills    │ │ "What jobs fit  │ │ "What am I      │      │   ║
║  │  │  do I actually  │ │  my actual      │ │  deep into      │      │   ║
║  │  │  have?"         │ │  strengths?"    │ │  right now?"    │      │   ║
║  │  └─────────────────┘ └─────────────────┘ └─────────────────┘      │   ║
║  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │   ║
║  │  │ Learning Path   │ │ Milestone       │ │ Cognitive       │      │   ║
║  │  │ Generator Tool  │ │ & Reward Tool   │ │ Profile Tool    │      │   ║
║  │  │                 │ │                 │ │                 │      │   ║
║  │  │ "Optimize my    │ │ "What's my next │ │ "What's my      │      │   ║
║  │  │  path to land   │ │  milestone?"    │ │  cognitive      │      │   ║
║  │  │  a motion       │ │  (triggers      │ │  fingerprint?"  │      │   ║
║  │  │  design role"   │ │   on-chain      │ │                 │      │   ║
║  │  │                 │ │   reward)       │ │                 │      │   ║
║  │  └─────────────────┘ └─────────────────┘ └─────────────────┘      │   ║
║  └─────────────────────────────┬───────────────────────────────────────┘   ║
╚════════════════════════════════╪════════════════════════════════════════════╝
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
┌────────────────────────┐ ┌─────────┐ ┌──────────────────────┐
│  MEMORY BACKEND        │ │   KG    │ │  ALCHEMY LAYER       │
│  (LongMemEval 3-Stage) │ │ (Neo4j) │ │  (On-Chain)          │
└────────────────────────┘ └─────────┘ └──────────────────────┘
         │                      │              │
         ▼                      ▼              ▼
   ┌─────────────────────────────────────────────────────────┐
   │              DETAILED BELOW                              │
   └─────────────────────────────────────────────────────────┘
```

---

## Layer 1: Memory Backend (LongMemEval 3-Stage)

### Indexing

```
Data Sources (porthon/data/)
┌──────────┬──────────────┬──────────┬──────────┬──────────┬──────────┐
│AI Chat   │Calendar      │Emails    │Lifelog   │Social    │Transac-  │
│Turns     │Events        │          │          │Posts     │tions     │
│          │              │          │          │          │          │
│Hyperfocus│Learning time │Client    │Reflec-   │Public    │Tool subs │
│episodes, │blocks, skill │invoices, │tions,    │skill     │(Figma,   │
│coaching  │sessions      │proposals │mood,     │showcases │School of │
│depth     │              │          │energy    │          │Motion)   │
└────┬─────┴──────┬───────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
     └────────────┴────────────┴──────────┴──────────┴──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ ROUND-LEVEL        │
                    │ DECOMPOSITION      │
                    │ Each entry = 1 unit │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ SKILL-AUGMENTED    │
                    │ KEY EXPANSION      │
                    │                    │
                    │ LLM extracts:      │
                    │ • Skills mentioned  │
                    │ • Depth indicators  │
                    │ • Engagement level  │
                    │ • Domain tags       │
                    │ • Time invested     │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ TIME-AWARE         │
                    │ ASSOCIATION        │
                    │                    │
                    │ Every fact stamped  │
                    │ with source ts →    │
                    │ enables hyperfocus  │
                    │ episode detection   │
                    │ (burst of related   │
                    │ queries in window)  │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ QDRANT VECTOR DB    │
                    │                     │
                    │ Schema.org objects:  │
                    │ DataFeedItem with   │
                    │ skill metadata      │
                    └─────────────────────┘
```

### Retrieval

Hybrid: dense embeddings + BM25 + KG traversal + temporal window filtering → Reciprocal Rank Fusion

### Reading

NLWeb's ranking.py + post_ranking.py with Chain-of-Note synthesis. Extended with knowledge update resolution (skill levels change over time).

---

## Layer 2: Knowledge Graph (Neo4j)

This is the **core profiling engine**. The KG maps the ADHD cognitive landscape.

```
                        ┌─────────────────┐
                        │  (:Person)       │
                        │  name: Theo      │
                        │  adhd: true      │
                        │  cognitive_fp:   │
                        │    {...}         │
                        └────────┬────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ (:SkillCluster) │  │ (:SkillCluster) │  │ (:SkillCluster) │
│ name: "Visual   │  │ name: "Web &    │  │ name: "Business │
│  Design"        │  │  Interactive"   │  │  & Freelance"   │
│ depth: 7/10     │  │ depth: 4/10     │  │ depth: 3/10     │
│ momentum: ↑     │  │ momentum: →     │  │ momentum: ↑     │
└────┬────────────┘  └────┬────────────┘  └────┬────────────┘
     │                    │                    │
     ▼                    ▼                    ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│(:Skill)  │  │(:Skill)  │  │(:Skill)  │  │(:Skill)  │
│Figma     │  │Blender   │  │Motion    │  │Pricing   │
│level: 8  │  │level: 2  │  │Design    │  │Strategy  │
│hrs: 2000+│  │hrs: 40   │  │level: 3  │  │level: 4  │
│src: conv,│  │src: conv,│  │hrs: 60   │  │src: conv │
│ txn, post│  │ social   │  │src: conv,│  │          │
│          │  │          │  │ txn, cal │  │          │
└──────────┘  └──────────┘  └──────────┘  └──────────┘

Edges:
─[:HAS_SKILL {since, evidence_count, last_active}]→
─[:HYPERFOCUSED_ON {start_ts, end_ts, depth_score, trigger}]→
─[:CONVERGES_WITH]→  (Figma + Motion Design → "UI Animation")
─[:MARKETS_TO]→ (:Opportunity {role, salary_range, demand_trend})
─[:SUSTAINS_ENGAGEMENT {avg_duration, problem_type}]→
─[:TRIGGERS_DISENGAGEMENT {pattern, context}]→
─[:LEARNED_DURING {episode_id}]→ (:HyperfocusEpisode)
─[:MILESTONE_COMPLETED {ts}]→ (:Milestone {on_chain_id})
```

### Cognitive Fingerprint (stored on Person node)

```json
{
  "sustained_engagement": {
    "visual_problem_solving": {"avg_mins": 180, "flow_probability": 0.8},
    "code_debugging": {"avg_mins": 120, "flow_probability": 0.6},
    "financial_planning": {"avg_mins": 25, "flow_probability": 0.1}
  },
  "hyperfocus_cycle": {
    "avg_episode_days": 18,
    "avg_depth_before_pivot": 4,
    "return_rate": 0.6
  },
  "learning_style": {
    "prefers": "project-based",
    "avoids": "sequential curriculum",
    "optimal_session": "90-120 min"
  },
  "dopamine_triggers": ["visible_progress", "social_validation", "novelty"]
}
```

---

## Layer 3: Alchemy On-Chain Integration

Alchemy provides the **web3 infrastructure** for three key features:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ALCHEMY INTEGRATION                                     │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  1. ON-CHAIN SKILL CREDENTIALS (Soulbound NFTs)                     │   │
│  │                                                                      │   │
│  │  When user completes a skill milestone:                              │   │
│  │  → System mints a Soulbound Token (SBT) via Alchemy Wallet API     │   │
│  │  → Token contains: skill name, level, evidence hash, timestamp      │   │
│  │  → Non-transferable (it's YOUR skill, not tradeable)                │   │
│  │  → Verifiable by any employer/client                                │   │
│  │                                                                      │   │
│  │  Alchemy APIs used:                                                  │   │
│  │  • Smart Wallets (account abstraction) — gasless minting for user   │   │
│  │  • NFT API — verify/display credentials                             │   │
│  │  • Webhooks — listen for mint confirmation                          │   │
│  │                                                                      │   │
│  │  Schema.org output:                                                  │   │
│  │  {                                                                   │   │
│  │    "@type": "EducationalOccupationalCredential",                    │   │
│  │    "name": "Motion Design — Level 3",                               │   │
│  │    "credentialCategory": "skill-credential",                        │   │
│  │    "recognizedBy": {"@type": "Organization", "name": "Porthon"},   │   │
│  │    "dateCreated": "2024-07-15",                                     │   │
│  │    "proof": {                                                        │   │
│  │      "type": "BlockchainVerification",                              │   │
│  │      "chain": "base",                                               │   │
│  │      "tokenId": "0x...",                                            │   │
│  │      "contract": "0x..."                                            │   │
│  │    }                                                                 │   │
│  │  }                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  2. MICRO-MILESTONE TOKEN REWARDS (Dopamine Loop)                   │   │
│  │                                                                      │   │
│  │  ADHD brains need immediate feedback. Each milestone step:          │   │
│  │                                                                      │   │
│  │  ┌──────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐        │   │
│  │  │Learn │ → │ System   │ → │ Alchemy  │ → │ User sees    │        │   │
│  │  │a     │   │ verifies │   │ mints    │   │ token +      │        │   │
│  │  │thing │   │ from chat│   │ reward   │   │ progress bar │        │   │
│  │  │      │   │ evidence │   │ token    │   │ IMMEDIATELY  │        │   │
│  │  └──────┘   └──────────┘   └──────────┘   └──────────────┘        │   │
│  │                                                                      │   │
│  │  Token economics:                                                    │   │
│  │  • Micro-rewards for each learning step (ERC-20 utility token)     │   │
│  │  • Accumulate → unlock premium features / marketplace visibility    │   │
│  │  • Streak bonuses for consistent engagement (ADHD-friendly)         │   │
│  │                                                                      │   │
│  │  Alchemy APIs used:                                                  │   │
│  │  • Smart Wallets — embedded wallet, no MetaMask friction            │   │
│  │  • Bundler API — batch milestone rewards into single tx             │   │
│  │  • Transaction Simulation — preview reward before minting           │   │
│  │  • Token Balances API — display reward portfolio                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  3. HIRING MARKETPLACE (On-Chain Verification)                      │   │
│  │                                                                      │   │
│  │  Employers/clients can:                                              │   │
│  │  • Query profiles via NLWeb /mcp endpoint                           │   │
│  │  • Verify skill credentials on-chain (Alchemy NFT API)             │   │
│  │  • See cognitive profile match score for their role                  │   │
│  │  • Hire with confidence: skills are evidence-based, not self-report │   │
│  │                                                                      │   │
│  │  Marketplace smart contract:                                         │   │
│  │  • Escrow for freelance gigs (Alchemy Wallet API)                  │   │
│  │  • Fee on successful match (revenue model)                          │   │
│  │  • Reputation accrual from completed gigs                           │   │
│  │                                                                      │   │
│  │  Alchemy APIs used:                                                  │   │
│  │  • NFT API — query skill SBTs for candidate profiles                │   │
│  │  • Token Balances — verify engagement history                       │   │
│  │  • Webhooks — notify on escrow release                              │   │
│  │  • Alchemy MCP Server — AI agents can search marketplace            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## NLWeb Custom Tools (tools.xml)

| Tool | Trigger | What It Does | Backend |
|------|---------|--------------|---------|
| **Skill Portfolio** | "What skills do I have?" | Builds dynamic portfolio from conversational evidence across ALL sources. Not a resume — a living proof-of-skill map. | Vector DB + KG aggregate |
| **Career Match** | "What jobs fit me?" | Maps skill clusters + cognitive fingerprint → market opportunities. Filters by engagement sustainability (won't suggest roles that trigger disengagement). | KG (:Opportunity) nodes + market API |
| **Hyperfocus Tracker** | "What am I deep into right now?" | Detects current hyperfocus episode from temporal pattern of recent queries. Shows domain, depth, duration, and whether it's converging with past skills. | Temporal query on Vector DB |
| **Learning Path Generator** | "How do I get to [role]?" | Generates ADHD-optimized learning path: micro-milestones, project-based, builds on existing hyperfocus patterns. Avoids sequential curriculum. | KG skill gaps + cognitive fingerprint |
| **Milestone & Reward** | "What's my next milestone?" | Returns next micro-milestone. On completion, triggers Alchemy mint of skill credential + reward token. Immediate feedback. | KG milestones + Alchemy APIs |
| **Cognitive Profile** | "What's my cognitive fingerprint?" | Shows which problem types sustain engagement, typical hyperfocus cycle, learning style, dopamine triggers. | KG Person node |

---

## Hyperfocus Detection Algorithm

The **key differentiator** — detecting hyperfocus episodes from conversational data:

```
INPUT: Timestamped conversation entries from Vector DB

ALGORITHM:
1. TEMPORAL WINDOWING
   - Sliding window (7 days) across all entries
   - Count entries per domain tag per window

2. BURST DETECTION
   - If entries_in_domain(window) > 2σ above user's baseline → HYPERFOCUS CANDIDATE
   - Example: Theo normally mentions "Blender" 0.5x/week
     Week of May 10: 8 mentions → burst detected

3. DEPTH SCORING
   - Analyze question complexity progression within burst:
     Day 1: "How do I start with Blender?" → depth=1 (intro)
     Day 3: "How to do UV unwrapping?" → depth=4 (intermediate)
     Day 5: "Best topology for subdivision modeling?" → depth=7 (advanced)
   - LLM scores each question's expertise level (1-10)

4. ENGAGEMENT DURATION
   - Track hours between first and last entry in burst
   - Cross-reference with calendar (learning blocks) and transactions (course purchases)

5. CONVERGENCE DETECTION (KG)
   - When burst domain has (:CONVERGES_WITH) edge to existing skill cluster:
     "Blender + Figma → 3D UI Design" (emerging market signal)
   - Alert user: "Your Blender deep-dive + Figma expertise = spatial design niche"

OUTPUT:
{
  "episode_id": "hf_042",
  "domain": "3D Modeling / Blender",
  "start": "2024-05-10",
  "duration_days": 12,
  "depth_progression": [1, 2, 4, 5, 7],
  "peak_depth": 7,
  "convergences": ["UI Design → Spatial/3D UI"],
  "market_signal": "3D UI designers: 340% demand increase, avg $95/hr",
  "recommended_next": "Complete one 3D UI prototype to reach milestone level"
}
```

---

## Data Flow (Complete)

```
User conversations (AI chat, coaching, questions)
  + Calendar (learning blocks, client meetings)
  + Emails (invoices, proposals → client evidence)
  + Lifelog (reflections, energy, mood)
  + Social (public skill showcases)
  + Transactions (tool subscriptions, course purchases)
       │
       ▼
[Schema.org Transform] → DataFeedItem objects
       │
       ▼
[LongMemEval Indexing]
  → Round-level decomposition
  → Skill-augmented key expansion (LLM extracts skills + depth + engagement)
  → Time-aware association
       │
       ├──────────────────────────────┐
       ▼                              ▼
[Qdrant Vector DB]            [Neo4j Knowledge Graph]
  Schema.org items              Person → SkillClusters → Skills
  with skill metadata           → HyperfocusEpisodes → Milestones
  + embeddings                  → Opportunities → CognitiveFingerprint
       │                              │
       └──────────────┬───────────────┘
                      │
                      ▼
[NLWeb Handler Pipeline]
  Decontextualize → Hyperfocus Detection → Memory Extraction
  → Tool Selection → Retrieve → Rank → Respond
       │
       ├── /ask → Questline UI (skill map, milestones, career paths)
       ├── /mcp → AI agents (Claude, Copilot query profile as tool)
       │
       ├── Milestone completed? → Alchemy Smart Wallet
       │     → Mint Soulbound Skill Credential (NFT)
       │     → Issue reward token (ERC-20)
       │     → Immediate UI feedback (dopamine)
       │
       └── Hiring marketplace
              → Employer queries /mcp for candidate profiles
              → Verifies credentials on-chain (Alchemy NFT API)
              → Match score based on cognitive profile alignment
              → Escrow + fee on successful match
```

---

## NLWeb Custom Prompts

### Hyperfocus Detection (Pre-Retrieval)

```xml
<Prompt ref="DetectHyperfocusPrompt">
  <promptString>
    Analyze this user interaction for signals of a hyperfocus episode.

    Look for:
    - Deep, specific questions about a single domain
    - Rapid skill progression (beginner → advanced questions)
    - Extended engagement duration
    - Emotional investment (excitement, curiosity, urgency)
    - Cross-referencing with other skills they know

    The user's query is: {request.rawQuery}.
    Recent queries (last 7 days): {request.previousQueries}.
    Known skill clusters: {user.skillClusters}.
  </promptString>
  <returnStruc>
    {
      "is_hyperfocus": "True or False",
      "domain": "The domain being hyperfocused on",
      "depth_level": "1-10 expertise level of current question",
      "convergences": ["domains this connects to"],
      "engagement_signal": "high/medium/low"
    }
  </returnStruc>
</Prompt>
```

### Memory Extraction (Extended for Skills)

```xml
<Prompt ref="DetectMemoryRequestPrompt">
  <promptString>
    Analyze this interaction for implicit skill evidence and personal facts.

    Extract ALL of these if present:
    - Skills demonstrated or discussed (with depth level)
    - Tools/technologies mentioned
    - Problems being solved (what type sustains engagement?)
    - Emotional state (confidence, frustration, excitement)
    - Career goals or aspirations mentioned
    - Financial information (rates, income, expenses)
    - Time investments (hours spent on learning/projects)

    Do NOT require explicit "remember this" — extract implicitly.

    The interaction is: {request.rawQuery}.
  </promptString>
  <returnStruc>
    {
      "skills_detected": [{"name": "...", "depth": 1-10, "evidence": "..."}],
      "tools_mentioned": ["..."],
      "engagement_type": "problem_type that sustained attention",
      "emotional_state": "...",
      "career_signals": ["..."],
      "financial_facts": ["..."],
      "kg_updates": [{"entity": "...", "relation": "...", "value": "..."}]
    }
  </returnStruc>
</Prompt>
```

---

## Gamification: Micro-Milestone Structure

```
ADHD-Optimized Milestone Design:
─────────────────────────────────

❌ Traditional: "Complete 12-week Motion Design course"
   (ADHD brain: too far away, no dopamine, abandoned by week 3)

✅ Ours: Break into micro-milestones with IMMEDIATE on-chain rewards

  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │ Milestone 1  │ ──→ │ Milestone 2  │ ──→ │ Milestone 3  │
  │              │     │              │     │              │
  │ "Animate     │     │ "Ease a      │     │ "Animate     │
  │  your logo   │     │  bounce      │     │  a UI        │
  │  in AE"      │     │  effect"     │     │  transition" │
  │              │     │              │     │              │
  │ ⏱ ~2 hours  │     │ ⏱ ~1 hour   │     │ ⏱ ~3 hours  │
  │ 🪙 +10 token │     │ 🪙 +10 token │     │ 🪙 +15 token │
  │ 🏅 SBT mint  │     │              │     │ 🏅 SBT mint  │
  │ (Level 1)    │     │              │     │ (Level 2)    │
  └─────────────┘     └─────────────┘     └─────────────┘

  Each completion:
  1. User tells system "I did it" (or system detects from chat)
  2. NLWeb Milestone Tool verifies evidence from conversation
  3. Alchemy Smart Wallet mints reward (gasless for user)
  4. UI shows: progress bar moves + token count + streak counter
  5. IMMEDIATE dopamine hit

  Streak bonus: 3 milestones in 7 days → 2x tokens
  (Leverages ADHD tendency for burst productivity)
```

---

## Business Model Integration

```
┌─────────────────────────────────────────────────────────────────┐
│  REVENUE STREAMS                                                 │
│                                                                  │
│  1. FREEMIUM USER PLATFORM                                      │
│     Free: Skill portfolio, basic hyperfocus tracking             │
│     Premium ($15/mo): Career pathing, learning paths,            │
│       advanced cognitive profile, milestone rewards              │
│                                                                  │
│  2. HIRING MARKETPLACE FEES                                     │
│     • 10-15% placement fee on successful matches                │
│     • Employers pay for access to cognitive-profile search       │
│     • "ADHD-aligned roles" filter → premium listing fee         │
│                                                                  │
│  3. ENTERPRISE TALENT LICENSE (B2B)                             │
│     • Companies license the cognitive profiling engine           │
│     • Identify ADHD employees + match to optimal roles           │
│     • Reduce turnover by aligning work to cognitive strengths   │
│     • API access via NLWeb /mcp → agents query talent pool      │
│                                                                  │
│  4. ON-CHAIN (Alchemy-powered)                                  │
│     • Skill credential verification fees (employers pay)         │
│     • Marketplace escrow fees                                    │
│     • Premium token features (boost marketplace visibility)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core Memory + Skill Extraction
1. NLWeb + Qdrant setup with porthon/data ingestion
2. Skill-augmented key expansion during indexing
3. Neo4j KG: Person → SkillCluster → Skill schema
4. Basic Skill Portfolio and Cognitive Profile tools

### Phase 2: Hyperfocus Detection
5. Temporal windowing algorithm on Vector DB
6. Burst detection + depth scoring
7. Convergence detection via KG traversal
8. Hyperfocus Tracker tool + Learning Path Generator

### Phase 3: Alchemy Integration
9. Smart Wallet setup (embedded, gasless)
10. Soulbound skill credential contract (Base chain)
11. Micro-milestone reward token (ERC-20)
12. Milestone & Reward tool wired to Alchemy APIs

### Phase 4: Career Matching
13. Market demand data integration (job APIs)
14. Career Match tool: skills + cognitive profile → opportunities
15. Hiring marketplace smart contract (escrow + fees)
16. Employer-facing NLWeb /mcp interface

### Phase 5: UI + Launch
17. Questline UI: skill map, milestones, rewards, career paths
18. Hiring marketplace web app
19. Enterprise talent API (B2B)
20. MCP server exposure for AI agent access
