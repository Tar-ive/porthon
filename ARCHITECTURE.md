# System Architecture: Hyperfocus Monetization & Career Trajectory Advisor

> An ADHD-optimized career intelligence platform that captures hyperfocus episodes from conversation data, maps skill acquisition to market demand, and provides dopamine-friendly micro-milestone career pathing — powered by NLWeb (conversational protocol), LongMemEval memory framework (temporal knowledge graph), Alchemy (blockchain infrastructure), and x402 (HTTP-native payments for micro-rewards and placement fee collection).

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
                                  →  Micro-rewards via x402 stablecoin payments
                                  →  Lands job → platform takes cut of signing bonus
```

---

## Business Model: The Income Share Agreement (x402-Enforced)

```
THE DEAL:
─────────
We invest in you (free platform + micro-rewards while you skill up).
When you land a job through us, we take a % of your signing bonus.

┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  USER JOURNEY                          MONEY FLOW                │
│  ───────────                           ──────────                │
│                                                                  │
│  1. Signs up (free)                    $0 from user              │
│  2. Uses platform, gets coaching       We pay micro-rewards      │
│     completes milestones               ($0.25-$2.00 per step     │
│                                        via x402 stablecoin)      │
│  3. Builds verified skill portfolio    Platform cost: ~$50-200   │
│     with on-chain evidence             total per user            │
│  4. Gets matched to job                                          │
│  5. Lands role with signing bonus      ──────────────────────    │
│                                        │ Employer pays signing  │ │
│                                        │ bonus to ESCROW        │ │
│                                        │ (smart contract)       │ │
│                                        │                        │ │
│                                        │ Escrow splits:         │ │
│                                        │ • 85% → User           │ │
│                                        │ • 15% → Platform       │ │
│                                        └────────────────────────┘ │
│                                                                  │
│  If user finds job WITHOUT us:         $0 — we eat the cost     │
│  If user doesn't get hired:            $0 — we eat the cost     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### How We Guarantee Payment (The Hard Problem)

The user can't just take our training, get a job offer, and skip the platform. Here's our multi-layer approach:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  GUARANTEE MECHANISMS                                                    │
│                                                                          │
│  LAYER 1: EMPLOYER-SIDE ESCROW (Primary — strongest guarantee)          │
│  ─────────────────────────────────────────────────────────────           │
│  The employer pays the signing bonus INTO our smart contract escrow.    │
│  The contract auto-splits to user (85%) and platform (15%).             │
│  The user never touches our cut — it's enforced at the protocol level.  │
│                                                                          │
│  How this works with x402:                                               │
│  • Employer's HR system hits our /api/place endpoint                    │
│  • Server responds HTTP 402 with PaymentRequired header                  │
│  • Payment = signing bonus amount in USDC                                │
│  • x402 facilitator routes: 85% to user wallet, 15% to platform wallet  │
│  • Atomic: either both parties get paid or neither does                  │
│  • No chargebacks (stablecoin settlement is final)                       │
│                                                                          │
│  Why employers agree: They pay the SAME signing bonus either way.       │
│  The split is transparent. They're not paying more — just routing       │
│  through our escrow instead of direct to the candidate.                  │
│                                                                          │
│  ──────────────────────────────────────────────────────────────────      │
│                                                                          │
│  LAYER 2: PLACEMENT AGREEMENT (Legal backstop)                          │
│  ──────────────────────────────────────────────                          │
│  When user enters the "job matching" phase:                              │
│  • Digital signature on Income Share Agreement (ISA)                     │
│  • Terms: 15% of signing bonus for jobs placed through platform          │
│  • Duration: 12 months from first employer introduction                  │
│  • Cap: Maximum $15,000 total obligation                                │
│  • If no signing bonus: $0 owed (we only take from bonuses)             │
│                                                                          │
│  ISA hash stored on-chain for immutable proof of agreement.              │
│  Standard legal enforceability if employer pays user directly            │
│  (bypassing escrow).                                                     │
│                                                                          │
│  ──────────────────────────────────────────────────────────────────      │
│                                                                          │
│  LAYER 3: EMPLOYER INTEGRATION (Prevent bypass)                         │
│  ──────────────────────────────────────────────                          │
│  Employers who use our marketplace agree to:                             │
│  • Route signing bonuses through our escrow for placed candidates       │
│  • This is a condition of accessing our talent pool                      │
│  • Standard in recruiting (recruiters always have placement terms)       │
│                                                                          │
│  Value prop for employers:                                               │
│  • Pre-verified skills (not self-reported resumes)                       │
│  • Cognitive profile matching → lower turnover for ADHD employees       │
│  • x402 payment = instant, no invoicing, no net-30                      │
│                                                                          │
│  ──────────────────────────────────────────────────────────────────      │
│                                                                          │
│  LAYER 4: REPUTATION & ACCESS (Soft guarantee)                          │
│  ─────────────────────────────────────────────                           │
│  Users who bypass payment lose:                                          │
│  • Platform access (skill tracking, career matching, rewards)            │
│  • Verified skill portfolio (employers can't verify credentials)         │
│  • Future placement services                                             │
│  • Community access                                                      │
│                                                                          │
│  The platform becomes MORE valuable over time (compounding skill data), │
│  so leaving has increasing cost.                                         │
│                                                                          │
│  ──────────────────────────────────────────────────────────────────      │
│                                                                          │
│  LAYER 5: GRADUATED COMMITMENT (Align incentives)                       │
│  ────────────────────────────────────────────────                        │
│  • Free tier: skill tracking + basic hyperfocus detection                │
│  • Active tier ($0): micro-rewards enabled, ISA signed                  │
│  • Matching tier ($0): career matching begins, employer introductions   │
│  • Placed tier: signing bonus split executes                             │
│                                                                          │
│  The ISA only activates when we make introductions.                      │
│  If user finds job on their own → they owe nothing.                     │
│  This is FAIR — we only collect when we deliver value.                  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Why This Works Economically

```
UNIT ECONOMICS:
───────────────
Cost per user (micro-rewards + compute): ~$150
Average signing bonus for design/tech roles: $10,000-$25,000
Our 15% cut: $1,500-$3,750
Placement rate needed to break even: ~1 in 10 users placed

Comparison to traditional recruiting:
  Recruiter fee: 15-25% of FIRST YEAR SALARY ($15k-$40k)
  Our fee: 15% of SIGNING BONUS only ($1.5k-$3.75k)

  We're 10x cheaper than a recruiter.
  Employers love this. Users love this. We make money.
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                             │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Questline UI │  │ MCP Agents   │  │ Employer     │  │ Enterprise   │   │
│  │ (User App)   │  │ (Claude,     │  │ Portal       │  │ Talent API   │   │
│  │              │  │  Copilot...) │  │              │  │ (B2B)        │   │
│  │ • Skill map  │  │              │  │ • Search     │  │              │   │
│  │ • Milestones │  │ Query user's │  │   candidates │  │ Search for   │   │
│  │ • Career path│  │ profile as   │  │ • Verify     │  │ cognitive    │   │
│  │ • Rewards    │  │ an MCP tool  │  │   skills     │  │ profiles     │   │
│  │ • x402 wallet│  │              │  │ • Place &    │  │              │   │
│  │              │  │              │  │   pay (x402) │  │              │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         └──────────────────┴─────────────────┴─────────────────┘           │
│                                    │                                        │
│                     REST /ask + /mcp (Schema.org JSON)                      │
│                     x402 payment headers on paid endpoints                  │
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
║  │  │ Resolve refs    │ │                 │ │                 │      │   ║
║  │  │ from convo      │ │ Is user in a    │ │ Extract skills, │      │   ║
║  │  │ history         │ │ hyperfocus      │ │ interests,      │      │   ║
║  │  │                 │ │ episode?        │ │ engagement      │      │   ║
║  │  └─────────────────┘ └────────┬────────┘ └────────┬────────┘      │   ║
║  │                               │                    │               │   ║
║  │                    ┌──────────▼────────────────────▼──────────┐    │   ║
║  │                    │  COGNITIVE FINGERPRINT UPDATER            │    │   ║
║  │                    │  • Problem types that sustain attention   │    │   ║
║  │                    │  • Disengagement triggers                 │    │   ║
║  │                    │  • Hyperfocus cycle patterns              │    │   ║
║  │                    │  • Accelerated depth domains              │    │   ║
║  │                    └──────────┬───────────────────────────────┘    │   ║
║  └───────────────────────────────┼─────────────────────────────────────┘   ║
║                                  │                                         ║
║  ┌───────────────────────────────▼─────────────────────────────────────┐   ║
║  │              TOOL ROUTING (tools.xml)                                │   ║
║  │                                                                     │   ║
║  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │   ║
║  │  │ Skill Portfolio │ │ Career Match    │ │ Hyperfocus      │      │   ║
║  │  │ Tool            │ │ Tool            │ │ Tracker Tool    │      │   ║
║  │  └─────────────────┘ └─────────────────┘ └─────────────────┘      │   ║
║  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │   ║
║  │  │ Learning Path   │ │ Milestone &     │ │ Cognitive       │      │   ║
║  │  │ Generator       │ │ Reward Tool     │ │ Profile Tool    │      │   ║
║  │  │                 │ │ (triggers x402) │ │                 │      │   ║
║  │  └─────────────────┘ └─────────────────┘ └─────────────────┘      │   ║
║  └─────────────────────────────┬───────────────────────────────────────┘   ║
╚════════════════════════════════╪════════════════════════════════════════════╝
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
┌────────────────────────┐ ┌─────────┐ ┌──────────────────────┐
│  MEMORY BACKEND        │ │   KG    │ │  x402 + ALCHEMY      │
│  (LongMemEval 3-Stage) │ │ (Neo4j) │ │  PAYMENT LAYER       │
└────────────────────────┘ └─────────┘ └──────────────────────┘
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
               ┌──────────────▼──────────────┐
               │  ROUND-LEVEL DECOMPOSITION  │
               │  + SKILL-AUGMENTED KEY      │
               │    EXPANSION (LLM)          │
               │  + TIME-AWARE ASSOCIATION   │
               └──────────────┬──────────────┘
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
          ┌─────────────────┐  ┌─────────────────┐
          │ QDRANT VECTOR DB│  │ NEO4J KG        │
          │ Schema.org items│  │ Person→Skills→  │
          │ + embeddings    │  │ Clusters→Market │
          └─────────────────┘  └─────────────────┘
```

### Retrieval

Hybrid: dense + BM25 + KG traversal + temporal filtering → Reciprocal Rank Fusion

### Reading

NLWeb ranking.py + post_ranking.py with Chain-of-Note. Extended for knowledge updates (skill levels change).

---

## Layer 2: Knowledge Graph (Neo4j)

```
(:Person {name, adhd: true, cognitive_fingerprint: {...}})
  │
  ├──[:HAS_SKILL {since, depth, evidence_count, last_active}]──→ (:Skill)
  ├──[:HYPERFOCUSED_ON {start, end, depth_score}]──→ (:HyperfocusEpisode)
  ├──[:IN_CLUSTER]──→ (:SkillCluster {name, momentum})
  │                      └──[:CONVERGES_WITH]──→ (:SkillCluster)
  ├──[:MATCHES_TO]──→ (:Opportunity {role, salary, demand_trend})
  ├──[:COMPLETED]──→ (:Milestone {step, reward_amount, reward_tx_hash})
  ├──[:SIGNED_ISA {hash, date, terms}]──→ (:Agreement)
  └──[:PLACED_AT {date, bonus, escrow_tx}]──→ (:Placement)

Cognitive Fingerprint (on Person node):
{
  "sustained_engagement": {"visual_problem_solving": {avg_mins: 180, flow_prob: 0.8}},
  "hyperfocus_cycle": {avg_episode_days: 18, return_rate: 0.6},
  "learning_style": {prefers: "project-based", optimal_session: "90-120 min"},
  "dopamine_triggers": ["visible_progress", "social_validation", "novelty"]
}
```

---

## Layer 3: x402 + Alchemy Payment Layer

### How x402 Works in Our System

x402 is the HTTP 402 "Payment Required" protocol by Coinbase. Payments happen **inside HTTP requests** — no accounts, no API keys, no invoicing. Stablecoin (USDC) settlement, zero protocol fees, instant and final.

We use x402 for **three payment flows**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FLOW 1: MICRO-MILESTONE REWARDS (Platform → User)                      │
│  ────────────────────────────────────────────────                        │
│                                                                          │
│  User completes a milestone → platform pays user via x402.              │
│  Small stablecoin amounts ($0.25 - $2.00 USDC per step).               │
│                                                                          │
│  Implementation:                                                         │
│  • Milestone & Reward Tool verifies completion from chat evidence       │
│  • Platform's Alchemy Smart Wallet signs x402 payment                   │
│  • USDC sent to user's embedded wallet (Alchemy account abstraction)   │
│  • User sees balance update IMMEDIATELY in Questline UI                 │
│  • No gas fees for user (platform sponsors via Alchemy paymaster)      │
│                                                                          │
│  Code (server-side, on milestone completion):                            │
│                                                                          │
│    // Platform pays user for completing milestone                        │
│    const payment = await x402Client.pay({                                │
│      to: userWalletAddress,                                              │
│      amount: milestone.rewardUSDC,  // e.g., "0.50"                     │
│      token: "USDC",                                                      │
│      network: "base",                                                    │
│      memo: `milestone:${milestone.id}`                                   │
│    });                                                                    │
│                                                                          │
│  Dopamine loop:                                                          │
│  ┌──────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐             │
│  │Learn │ → │ System   │ → │ x402     │ → │ User sees    │             │
│  │a     │   │ verifies │   │ sends    │   │ $0.50 USDC   │             │
│  │thing │   │ from chat│   │ USDC     │   │ + progress   │             │
│  │      │   │ evidence │   │ instant  │   │ IMMEDIATELY  │             │
│  └──────┘   └──────────┘   └──────────┘   └──────────────┘             │
│                                                                          │
│  Streak bonus: 3 milestones in 7 days → 2x reward                      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  FLOW 2: EMPLOYER PLACEMENT ESCROW (Employer → Split → User + Platform) │
│  ──────────────────────────────────────────────────────────────────      │
│                                                                          │
│  This is the core revenue mechanism. When a candidate is placed:        │
│                                                                          │
│  1. Employer hits POST /api/place with candidate + bonus amount          │
│  2. Server responds HTTP 402 with:                                       │
│     X-PAYMENT-REQUIRED: {                                                │
│       amount: "10000.00",        // signing bonus in USDC                │
│       network: "base",                                                   │
│       scheme: "exact",                                                   │
│       resource: "/api/place",                                            │
│       description: "Placement fee for candidate [id]"                   │
│     }                                                                    │
│  3. Employer's system pays via x402 (USDC on Base)                      │
│  4. Our ESCROW SMART CONTRACT receives the full amount                  │
│  5. Contract auto-executes split:                                        │
│     • 85% → User's wallet (their signing bonus)                         │
│     • 15% → Platform wallet (our placement fee)                         │
│  6. Both parties receive funds atomically                                │
│  7. Server returns 200 OK with placement confirmation                   │
│                                                                          │
│  Smart contract logic:                                                   │
│                                                                          │
│    function settlePlacement(                                              │
│      address candidate,                                                  │
│      uint256 totalBonus,                                                 │
│      uint256 platformBps  // 1500 = 15%                                 │
│    ) external {                                                          │
│      uint256 platformCut = (totalBonus * platformBps) / 10000;          │
│      uint256 candidateCut = totalBonus - platformCut;                   │
│      USDC.transfer(candidate, candidateCut);                            │
│      USDC.transfer(platformWallet, platformCut);                        │
│      emit PlacementSettled(candidate, candidateCut, platformCut);       │
│    }                                                                     │
│                                                                          │
│  Why x402 for this:                                                      │
│  • Instant settlement (no net-30 invoicing)                             │
│  • No chargebacks (stablecoin is final)                                 │
│  • Atomic split (user + platform paid in same tx)                       │
│  • Employer doesn't need a crypto wallet — x402 abstracts this         │
│  • Transparent: both parties see the split on-chain                     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  FLOW 3: ENTERPRISE API ACCESS (B2B → Platform)                         │
│  ──────────────────────────────────────────────                          │
│                                                                          │
│  Enterprise clients pay per-query for talent search API:                │
│                                                                          │
│  • GET /api/talent/search?skills=motion-design&cognitive=visual         │
│  • Server returns 402: pay $0.10 USDC per query                         │
│  • x402 client pays, gets results                                       │
│  • No API keys, no accounts, no subscriptions                           │
│  • Perfect for AI agents doing talent sourcing                          │
│                                                                          │
│  Server code (Express + x402 middleware):                                │
│                                                                          │
│    app.use(paymentMiddleware({                                           │
│      "GET /api/talent/search": {                                         │
│        price: "$0.10",                                                   │
│        network: "base",                                                  │
│        description: "Cognitive talent search query"                     │
│      },                                                                  │
│      "GET /api/talent/profile/:id": {                                   │
│        price: "$0.50",                                                   │
│        network: "base",                                                  │
│        description: "Full cognitive profile with skill verification"    │
│      }                                                                   │
│    }));                                                                   │
│                                                                          │
│  Alchemy APIs used:                                                      │
│  • Smart Wallets — embedded wallets for users (no MetaMask)             │
│  • Alchemy MCP Server — AI agents query on-chain data                   │
│  • Webhooks — confirm payment settlement                                │
│  • Token Balances API — display user reward balance                     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Hyperfocus Detection Algorithm

```
INPUT: Timestamped conversation entries from Vector DB

1. TEMPORAL WINDOWING (7-day sliding window)
   Count entries per domain tag per window

2. BURST DETECTION
   If entries_in_domain(window) > 2σ above baseline → HYPERFOCUS

3. DEPTH SCORING
   LLM rates question complexity (1-10) within burst:
   Day 1: "How do I start with Blender?" → depth=1
   Day 5: "Best topology for subdivision modeling?" → depth=7

4. CONVERGENCE DETECTION (KG)
   New burst domain + existing skill cluster → emerging niche
   "Blender + Figma = spatial UI design (340% demand increase)"

OUTPUT: {episode_id, domain, depth_progression, convergences, market_signal}
```

---

## NLWeb Custom Tools

| Tool | Trigger | Backend |
|------|---------|---------|
| **Skill Portfolio** | "What skills do I have?" | Vector DB + KG aggregate. Builds from chat evidence, not self-report. |
| **Career Match** | "What jobs fit me?" | KG skill clusters + cognitive fingerprint → market opportunities. Filters by engagement sustainability. |
| **Hyperfocus Tracker** | "What am I deep into?" | Temporal burst detection on Vector DB. Shows domain, depth, convergences. |
| **Learning Path Generator** | "How do I get to [role]?" | KG skill gaps + cognitive fingerprint. ADHD-optimized: micro-milestones, project-based. |
| **Milestone & Reward** | "What's my next step?" | Next micro-milestone. On completion: x402 USDC reward. Immediate. |
| **Cognitive Profile** | "What's my cognitive fingerprint?" | KG Person node. Problem types, hyperfocus cycle, dopamine triggers. |

---

## Gamification: Micro-Milestones with x402 Rewards

```
❌ Traditional: "Complete 12-week Motion Design course"
   (ADHD brain: too far, no dopamine, abandoned week 3)

✅ Ours: Micro-milestones + REAL MONEY rewards via x402

  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │ Milestone 1  │ ──→ │ Milestone 2  │ ──→ │ Milestone 3  │
  │              │     │              │     │              │
  │ "Animate     │     │ "Ease a      │     │ "Animate     │
  │  your logo   │     │  bounce      │     │  a UI        │
  │  in AE"      │     │  effect"     │     │  transition" │
  │              │     │              │     │              │
  │ ⏱ ~2 hours  │     │ ⏱ ~1 hour   │     │ ⏱ ~3 hours  │
  │ 💵 $0.50 USDC│     │ 💵 $0.25 USDC│     │ 💵 $1.00 USDC│
  │  (x402)      │     │  (x402)      │     │  (x402)      │
  └─────────────┘     └─────────────┘     └─────────────┘

  Why REAL MONEY > points/tokens:
  • USDC is actual money, not platform points that expire
  • ADHD brains respond to tangible rewards
  • x402 settlement is instant — no "pending" delays
  • User accumulates real value while skilling up
  • Creates sunk-cost attachment to the platform

  Typical user journey: ~80 milestones × avg $0.50 = ~$40 earned
  Platform cost: $40 per user in rewards
  ROI on placement: $1,500-$3,750 (37x-94x return)
```

---

## Revenue Model Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  REVENUE STREAMS (all x402-powered)                             │
│                                                                  │
│  1. PLACEMENT FEES (primary)                                    │
│     15% of signing bonus, collected via escrow smart contract    │
│     Expected: $1,500-$3,750 per placement                       │
│     x402 flow: employer → escrow → auto-split                   │
│                                                                  │
│  2. ENTERPRISE TALENT API (secondary)                           │
│     Per-query pricing via x402 paywall                           │
│     $0.10/search, $0.50/full profile                            │
│     No subscriptions — pure usage-based                          │
│     AI agents can pay natively (x402 is agent-friendly)         │
│                                                                  │
│  3. PREMIUM FEATURES (tertiary)                                 │
│     Advanced career pathing, priority matching                   │
│     $15/mo via x402 recurring (or ISA-funded post-placement)    │
│                                                                  │
│  COSTS:                                                          │
│  • Micro-rewards: ~$40-200 per user (x402 USDC)                │
│  • Compute (NLWeb, LLM calls, Qdrant, Neo4j): ~$5-10/mo/user  │
│  • Alchemy: usage-based (low cost on Base L2)                   │
│  • x402 facilitator: zero protocol fees                         │
│                                                                  │
│  BREAK-EVEN: 1 in 10 users placed (conservative)               │
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
8. Hyperfocus Tracker + Learning Path Generator tools

### Phase 3: x402 Payment Layer
9. Alchemy Smart Wallet integration (embedded, gasless for users)
10. x402 micro-reward flow: milestone → verify → pay USDC
11. Escrow smart contract for placement fee splitting
12. x402 Express middleware on employer-facing endpoints

### Phase 4: Career Matching + Marketplace
13. Market demand data integration
14. Career Match tool: skills + cognitive profile → opportunities
15. Employer portal with x402-gated placement flow
16. ISA agreement system (digital signature + on-chain hash)

### Phase 5: UI + Enterprise
17. Questline UI: skill map, milestones, x402 wallet, career paths
18. Enterprise talent search API with x402 paywall
19. MCP server exposure for AI agent access
20. Alchemy MCP Server integration for on-chain verification
