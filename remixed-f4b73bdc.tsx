import { useState, useEffect, useRef, useCallback } from "react";

/* ═══════════════════════════════════════════════════════════════════════════
   QUESTLINE — Full App Mock
   Screens: Onboarding (consent → loading → patterns → scenarios)
            Dashboard (home, weekly actions, stats, chat agent)
   ═══════════════════════════════════════════════════════════════════════════ */

// ─── DATA ────────────────────────────────────────────────────────────────────
const DATA_SOURCES = [
  { id: "financial", label: "Financial Records", desc: "Transactions, spending categories, savings trends", icon: "💰", records: "2,847 transactions" },
  { id: "health", label: "Health & Fitness", desc: "Steps, sleep, heart rate, workout history", icon: "❤️", records: "365 daily logs" },
  { id: "calendar", label: "Calendar & Time", desc: "Events, meetings, free blocks, patterns", icon: "📅", records: "1,203 events" },
  { id: "social", label: "Social Activity", desc: "Messages, meetups, community engagement", icon: "👥", records: "4,120 interactions" },
];

const CHARACTER_STATS = [
  { name: "Financial Literacy", level: 6, max: 10, trend: "up", detail: "Savings rate 18% — up from 12% six months ago", prev: 5 },
  { name: "Physical Vitality", level: 4, max: 10, trend: "down", detail: "Average 4.2k steps/day — down 38% since Q2", prev: 6 },
  { name: "Social Bond", level: 7, max: 10, trend: "stable", detail: "3-4 social events/week — consistent for 8 months", prev: 7 },
  { name: "Time Mastery", level: 5, max: 10, trend: "down", detail: "32% of calendar is meetings — up from 24%", prev: 6 },
  { name: "Self Awareness", level: 5, max: 10, trend: "up", detail: "Journaling 4x/week — new habit started 2 months ago", prev: 3 },
];

const PATTERNS = [
  { id: 1, type: "single", domain: "financial", text: "Monthly discretionary spending up 14% over 6 months.", severity: "warning" },
  { id: 2, type: "single", domain: "health", text: "Exercise frequency dropped 40% since August. Sleep declining in parallel.", severity: "danger" },
  { id: 3, type: "cross", domains: ["financial", "calendar"], text: "Spending spikes 22% in weeks following 30+ hours of meetings.", severity: "insight" },
  { id: 4, type: "cross", domains: ["health", "social"], text: "Weeks with 3+ social events correlate with 60% more steps.", severity: "positive" },
  { id: 5, type: "single", domain: "social", text: "Deep 1-on-1 conversations declining — group events replacing intimate connections.", severity: "warning" },
  { id: 6, type: "cross", domains: ["calendar", "health", "financial"], text: "After high-meeting weeks, exercise drops and delivery spending triples — burnout cascade.", severity: "insight" },
];

const SCENARIOS = [
  {
    id: "drift", title: "The Comfortable Drift", likelihood: "Most Likely", color: "#f59e0b",
    timeframes: { y1: "Savings rate drops to 10%. Fitness continues declining. Social life stays active but shallow.", y5: "Lifestyle inflation absorbs raises. Health issues start appearing.", y10: "Financial stress emerges. Chronic health conditions likely." },
    patterns: [1, 2, 5], narrative: "If current trends continue unchanged, rising spending and declining fitness creates a slow erosion across all domains.",
  },
  {
    id: "rebalance", title: "The Rebalance", likelihood: "Possible", color: "#10b981",
    timeframes: { y1: "Spending stabilizes. Exercise returns to spring levels. Calendar restructured.", y5: "Emergency fund built. Running a 10K. Deep friendships restored.", y10: "Financial independence track. Excellent health markers." },
    patterns: [3, 4, 6], narrative: "Your data shows the building blocks are there — the key lever is breaking the burnout cascade by protecting recovery time.",
  },
  {
    id: "transform", title: "The Transformation", likelihood: "Aspirational", color: "#8b5cf6",
    timeframes: { y1: "Savings rate hits 25%. Daily movement locked in. Calendar redesigned around energy.", y5: "Side income from reclaimed time. Competitive athlete. Community connector.", y10: "Full financial freedom. Peak health. Purpose-driven relationships." },
    patterns: [1, 2, 3, 4, 5, 6], narrative: "Aggressive but achievable — leverage your social-exercise correlation as the foundation habit.",
  },
];

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const buildWeeklyActions = (scenarioId) => {
  const bases = {
    drift: [
      { action: "Transfer $50 to savings account", icon: "💰", time: "2 min", day: "Mon", domain: "financial", cal: "7:30 AM", rationale: "Discretionary spending up 14%. Small transfers reverse the trend. $50/week = $2,600/year." },
      { action: "30-minute walk — your 6pm is free", icon: "🚶", time: "30 min", day: "Mon", domain: "health", cal: "6:00 PM", rationale: "Step count down 38%. One walk starts rebuilding the habit." },
      { action: "Text a close friend for a 1-on-1 this week", icon: "💬", time: "3 min", day: "Tue", domain: "social", cal: "12:00 PM", rationale: "Deep connections declining while group events stay high." },
      { action: "Pack lunch instead of ordering delivery", icon: "🥗", time: "15 min", day: "Wed", domain: "financial", cal: "7:00 AM", rationale: "Delivery spending triples after heavy weeks. Building the counter-habit." },
      { action: "Evening walk — invite someone", icon: "🚶", time: "30 min", day: "Wed", domain: "health", cal: "6:00 PM", rationale: "Social + exercise boosts both metrics by 60% (Pattern #4)." },
      { action: "5-min spending check-in on banking app", icon: "📊", time: "5 min", day: "Thu", domain: "financial", cal: "8:00 PM", rationale: "Midweek awareness catches stress-spending before the weekend." },
      { action: "Journal: what drained vs. energized me?", icon: "📝", time: "10 min", day: "Thu", domain: "self", cal: "9:00 PM", rationale: "Self-awareness score rising — this accelerates the trend." },
      { action: "Active social outing (hike, sport, walk)", icon: "👥", time: "60 min", day: "Sat", domain: "social", cal: "10:00 AM", rationale: "Highest-leverage activity: social + physical combined." },
      { action: "Meal prep 3 lunches for next week", icon: "🥗", time: "45 min", day: "Sun", domain: "health", cal: "11:00 AM", rationale: "Reduces weekday delivery spending and decision fatigue." },
      { action: "Transfer $50 + review weekly progress", icon: "💰", time: "5 min", day: "Sun", domain: "financial", cal: "7:00 PM", rationale: "$100/week in savings. The review cements the habit loop." },
    ],
    rebalance: [
      { action: "Block Wednesday afternoons — no meetings after 3pm", icon: "🛡️", time: "5 min", day: "Mon", domain: "calendar", cal: "8:00 AM", rationale: "Your burnout cascade triggers after heavy meeting weeks. Protected time breaks the cycle." },
      { action: "Walk + call a friend (combine social & exercise)", icon: "🚶", time: "30 min", day: "Mon", domain: "health", cal: "6:00 PM", rationale: "Social + exercise together is your highest-leverage habit (Pattern #4)." },
      { action: "Set $200/week spending alert in banking app", icon: "📊", time: "3 min", day: "Tue", domain: "financial", cal: "8:00 AM", rationale: "Your stress-spending pattern is invisible without real-time tracking." },
      { action: "Convert tomorrow's 9am meeting to async update", icon: "📅", time: "10 min", day: "Tue", domain: "calendar", cal: "4:00 PM", rationale: "Reclaiming one morning meeting/week reduces load by 8%." },
      { action: "Use protected Wednesday afternoon for a long walk", icon: "🚶", time: "45 min", day: "Wed", domain: "health", cal: "3:30 PM", rationale: "This is the keystone — exercise in your protected block." },
      { action: "Cook dinner instead of ordering (stress-spend block)", icon: "🥗", time: "30 min", day: "Thu", domain: "financial", cal: "6:30 PM", rationale: "Thursday is historically your highest delivery day. Interrupt the pattern." },
      { action: "Journal: rate your energy 1-10 each day this week", icon: "📝", time: "5 min", day: "Thu", domain: "self", cal: "9:00 PM", rationale: "Tracking energy reveals which meetings drain vs. energize you." },
      { action: "Schedule next week's protected time blocks", icon: "🛡️", time: "10 min", day: "Fri", domain: "calendar", cal: "4:00 PM", rationale: "Pre-scheduling protection before others claim your calendar." },
      { action: "Social activity — keep it active (park, hike, gym)", icon: "👥", time: "60 min", day: "Sat", domain: "social", cal: "10:00 AM", rationale: "Maintain your social-exercise correlation on the weekend." },
      { action: "Review: spending, energy scores, steps. Plan next week.", icon: "📊", time: "15 min", day: "Sun", domain: "financial", cal: "7:00 PM", rationale: "Weekly review is the habit that holds all other habits together." },
    ],
    transform: [
      { action: "Auto-transfer $100 to savings (set up recurring)", icon: "🏦", time: "10 min", day: "Mon", domain: "financial", cal: "7:30 AM", rationale: "Hitting 25% savings rate requires automation. $100/week = $5,200/year." },
      { action: "Deep Work block: 6-7am (no meetings, no email)", icon: "⚡", time: "60 min", day: "Mon", domain: "calendar", cal: "6:00 AM", rationale: "One protected hour daily = 365 hours/year of skill compounding." },
      { action: "Sign up for a local running group (Saturday meetup)", icon: "🏃", time: "5 min", day: "Tue", domain: "health", cal: "12:00 PM", rationale: "Running group locks in social + exercise simultaneously." },
      { action: "Cancel one recurring meeting that could be an email", icon: "✂️", time: "5 min", day: "Tue", domain: "calendar", cal: "2:00 PM", rationale: "Meeting load is 32% and rising. Remove the lowest-value one permanently." },
      { action: "Deep Work block + skill-building session", icon: "⚡", time: "60 min", day: "Wed", domain: "calendar", cal: "6:00 AM", rationale: "Consistency in the morning block is what creates the side-income path." },
      { action: "Cook a new recipe (replace 2 delivery orders)", icon: "🥗", time: "40 min", day: "Wed", domain: "financial", cal: "6:30 PM", rationale: "Each home-cooked meal saves ~$15 and builds self-sufficiency." },
      { action: "1-on-1 deep conversation (not group, not screen)", icon: "💬", time: "45 min", day: "Thu", domain: "social", cal: "7:00 PM", rationale: "The Transformation requires depth, not breadth, in relationships." },
      { action: "Journal: what did I build this week? What compounds?", icon: "📝", time: "10 min", day: "Fri", domain: "self", cal: "9:00 PM", rationale: "Self-awareness score rising — connecting effort to outcomes accelerates all stats." },
      { action: "Running group meetup", icon: "🏃", time: "60 min", day: "Sat", domain: "health", cal: "8:00 AM", rationale: "Social + intense exercise. The cornerstone habit of the Transformation path." },
      { action: "Weekly review: finances, energy, social, fitness", icon: "📊", time: "20 min", day: "Sun", domain: "financial", cal: "6:00 PM", rationale: "The meta-habit. Review → adjust → compound. This is how trajectories shift." },
    ],
  };
  return (bases[scenarioId] || bases.drift).map((a, i) => ({ ...a, id: i }));
};

// Mock weekly history
const WEEK_HISTORY = [
  { week: "Week 1", completed: 3, total: 10, stats: { financial: 5, health: 4, social: 6, time: 5, self: 3 } },
  { week: "Week 2", completed: 6, total: 10, stats: { financial: 5, health: 4, social: 7, time: 5, self: 4 } },
  { week: "Week 3", completed: 7, total: 10, stats: { financial: 6, health: 4, social: 7, time: 5, self: 4 } },
  { week: "Week 4", completed: 5, total: 10, stats: { financial: 6, health: 4, social: 7, time: 5, self: 5 } },
];

// Agent chat responses
const AGENT_RESPONSES = {
  "too hard": "I hear you — let's scale back. Which action feels most overwhelming? I can break it into something smaller, or swap it for a gentler alternative that still moves you toward your chosen scenario.",
  "walk": "Walking 30 minutes feeling like a lot? Let's try this: just put your shoes on and step outside for 10 minutes. If you want to keep going, great. If not, 10 minutes still counts. Your data shows even short walks improve your sleep score.",
  "savings": "The $50 transfer feeling too steep right now? Let's start with $20. The habit of transferring matters more than the amount. Once it's automatic, we can increase it. $20/week still adds $1,040 this year.",
  "time": "Feeling short on time? Let's look at your calendar — you have a 45-min gap Tuesday afternoon and Thursday evening is mostly free. Want me to move the hardest actions into those windows?",
  "meeting": "Canceling a meeting feels risky? Start softer: pick one meeting and propose making it biweekly instead of weekly. That reclaims 2 hours/month with almost no social risk.",
  "cooking": "Meal prep feeling overwhelming? Start with just one meal — make a double batch of something you already like on Sunday. That covers one weekday lunch for zero extra planning.",
  "default": "Tell me more about what's feeling off. I can adjust any action — make it smaller, move it to a different day, swap it for something equivalent, or remove it entirely. The goal is progress you'll actually do, not a perfect plan you won't."
};

// ─── STYLES ──────────────────────────────────────────────────────────────────
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Alegreya+Sans:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg-deep: #090c11;
  --bg-surface: #0f1319;
  --bg-card: #141a24;
  --bg-card-hover: #1a2236;
  --bg-elevated: #1e2738;
  --border: #1e293b;
  --border-glow: #334155;
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --gold: #f59e0b;
  --gold-dim: rgba(245, 158, 11, 0.15);
  --emerald: #10b981;
  --emerald-dim: rgba(16, 185, 129, 0.12);
  --violet: #8b5cf6;
  --violet-dim: rgba(139, 92, 246, 0.12);
  --rose: #f43f5e;
  --rose-dim: rgba(244, 63, 94, 0.1);
  --cyan: #06b6d4;
  --font-display: 'Cinzel', serif;
  --font-body: 'Alegreya Sans', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #root, #__next { background: var(--bg-deep) !important; color: var(--text-primary); }
html { min-height: 100vh; }

.ql-noise {
  position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

.ql-app {
  position: relative; z-index: 1;
  min-height: 100vh;
  max-width: 920px;
  margin: 0 auto;
  padding: 20px 16px 80px;
  font-family: var(--font-body);
  color: var(--text-primary);
  background: var(--bg-deep);
}

/* Header */
.ql-header { text-align: center; padding: 16px 0 8px; margin-bottom: 8px; position: relative; }
.ql-header h1 {
  font-family: var(--font-display); font-size: 2rem; font-weight: 700;
  letter-spacing: 0.12em; color: var(--gold);
  text-shadow: 0 0 40px rgba(245,158,11,0.15);
}
.ql-header .sub { font-weight: 300; font-size: 0.95rem; color: var(--text-secondary); letter-spacing: 0.03em; margin-top: 2px; }
.ql-reanalyze {
  position: absolute; top: 18px; right: 0;
  display: inline-flex; align-items: center; gap: 5px;
  padding: 7px 14px; border: 1px solid var(--border); border-radius: 7px;
  font-family: var(--font-mono); font-size: 0.68rem; letter-spacing: 0.03em;
  background: transparent; color: var(--text-muted); cursor: pointer; transition: all 0.2s;
}
.ql-reanalyze:hover { border-color: var(--gold); color: var(--gold); }

/* Step indicator */
.ql-steps { display: flex; justify-content: center; gap: 6px; margin-bottom: 8px; }
.ql-step-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--border); transition: all 0.4s; }
.ql-step-dot.active { background: var(--gold); box-shadow: 0 0 10px rgba(245,158,11,0.5); }
.ql-step-dot.done { background: var(--emerald); }
.ql-step-labels { display: flex; justify-content: center; gap: 32px; margin-bottom: 28px; }
.ql-step-lbl { font-family: var(--font-mono); font-size: 0.65rem; letter-spacing: 0.07em; text-transform: uppercase; color: var(--text-muted); transition: color 0.3s; }
.ql-step-lbl.active { color: var(--gold); }
.ql-step-lbl.done { color: var(--emerald); }

/* Cards */
.ql-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
  padding: 18px 22px; margin-bottom: 12px; transition: all 0.25s; cursor: pointer;
}
.ql-card:hover { background: var(--bg-card-hover); border-color: var(--border-glow); transform: translateY(-1px); }
.ql-card.selected { border-color: var(--gold); box-shadow: 0 0 20px rgba(245,158,11,0.08); }

/* Toggle */
.ql-toggle { width: 42px; height: 22px; border-radius: 11px; background: var(--border); position: relative; cursor: pointer; transition: background 0.25s; flex-shrink: 0; }
.ql-toggle.on { background: var(--emerald); }
.ql-toggle-thumb { width: 16px; height: 16px; border-radius: 50%; background: #fff; position: absolute; top: 3px; left: 3px; transition: transform 0.25s; }
.ql-toggle.on .ql-toggle-thumb { transform: translateX(20px); }

/* Buttons */
.ql-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 13px 28px; border: none; border-radius: 8px;
  font-family: var(--font-display); font-size: 0.88rem; font-weight: 600;
  letter-spacing: 0.07em; cursor: pointer; transition: all 0.25s;
  background: linear-gradient(135deg, var(--gold), #d97706); color: #0a0d13; text-transform: uppercase;
}
.ql-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(245,158,11,0.3); }
.ql-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.ql-btn-ghost {
  display: inline-flex; align-items: center; gap: 6px; padding: 9px 18px;
  border: 1px solid var(--border); border-radius: 8px; font-family: var(--font-body);
  font-size: 0.82rem; background: transparent; color: var(--text-secondary); cursor: pointer; transition: all 0.2s;
}
.ql-btn-ghost:hover { border-color: var(--text-muted); color: var(--text-primary); }

.ql-btn-sm {
  padding: 7px 14px; border: 1px solid var(--border); border-radius: 6px;
  font-family: var(--font-mono); font-size: 0.7rem; background: transparent;
  color: var(--text-muted); cursor: pointer; transition: all 0.2s; letter-spacing: 0.03em;
}
.ql-btn-sm:hover { border-color: var(--gold); color: var(--gold); }
.ql-btn-sm.active { border-color: var(--gold); color: var(--gold); background: var(--gold-dim); }

/* Tags */
.ql-tag { display: inline-block; padding: 2px 9px; border-radius: 20px; font-family: var(--font-mono); font-size: 0.62rem; letter-spacing: 0.04em; text-transform: uppercase; font-weight: 500; }
.ql-tag.cross { background: var(--violet-dim); color: var(--violet); border: 1px solid rgba(139,92,246,0.3); }
.ql-tag.single { background: rgba(100,116,139,0.12); color: var(--text-secondary); border: 1px solid rgba(100,116,139,0.25); }
.ql-tag.financial { background: rgba(245,158,11,0.08); color: var(--gold); }
.ql-tag.health { background: var(--rose-dim); color: var(--rose); }
.ql-tag.calendar { background: rgba(6,182,212,0.08); color: var(--cyan); }
.ql-tag.social { background: var(--emerald-dim); color: var(--emerald); }
.ql-tag.self { background: var(--violet-dim); color: var(--violet); }

/* Stat bar */
.ql-bar-bg { height: 7px; background: var(--border); border-radius: 4px; overflow: hidden; flex: 1; }
.ql-bar-fill { height: 100%; border-radius: 4px; transition: width 0.8s ease; }

/* Scenario cards */
.ql-sc { background: var(--bg-card); border: 2px solid var(--border); border-radius: 14px; padding: 22px; margin-bottom: 14px; cursor: pointer; transition: all 0.3s; position: relative; overflow: hidden; }
.ql-sc:hover { transform: translateY(-2px); border-color: var(--border-glow); }
.ql-sc.selected { border-color: var(--gold); box-shadow: 0 0 28px rgba(245,158,11,0.1); }
.ql-sc-bar { position: absolute; top: 0; left: 0; right: 0; height: 3px; opacity: 0; transition: opacity 0.3s; }
.ql-sc.selected .ql-sc-bar, .ql-sc:hover .ql-sc-bar { opacity: 1; }

/* Timeframe tabs */
.ql-tf { display: flex; gap: 3px; margin: 10px 0; background: rgba(30,41,59,0.4); border-radius: 7px; padding: 3px; }
.ql-tf button { flex: 1; padding: 6px; text-align: center; border-radius: 5px; font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); cursor: pointer; transition: all 0.2s; border: none; background: transparent; }
.ql-tf button.active { background: var(--bg-card-hover); color: var(--text-primary); }

/* Action check */
.ql-check {
  width: 20px; height: 20px; border: 2px solid var(--border-glow); border-radius: 5px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.2s; flex-shrink: 0; font-size: 11px; color: transparent;
}
.ql-check.done { background: var(--emerald); border-color: var(--emerald); color: #fff; }

/* Dashboard nav */
.ql-nav { display: flex; gap: 2px; margin-bottom: 24px; background: rgba(30,41,59,0.3); border-radius: 8px; padding: 3px; }
.ql-nav button {
  flex: 1; padding: 10px 8px; text-align: center; border-radius: 6px;
  font-family: var(--font-mono); font-size: 0.72rem; letter-spacing: 0.04em;
  color: var(--text-muted); cursor: pointer; transition: all 0.2s; border: none; background: transparent;
}
.ql-nav button.active { background: var(--bg-elevated); color: var(--text-primary); }

/* Chat */
.ql-chat-container { display: flex; flex-direction: column; height: 480px; }
.ql-chat-msgs { flex: 1; overflow-y: auto; padding: 12px 0; display: flex; flex-direction: column; gap: 10px; }
.ql-chat-bubble { max-width: 82%; padding: 12px 16px; border-radius: 14px; font-size: 0.9rem; line-height: 1.55; }
.ql-chat-bubble.user { align-self: flex-end; background: var(--gold-dim); color: var(--text-primary); border-bottom-right-radius: 4px; }
.ql-chat-bubble.agent { align-self: flex-start; background: var(--bg-elevated); color: var(--text-secondary); border-bottom-left-radius: 4px; border: 1px solid var(--border); }
.ql-chat-input-row { display: flex; gap: 8px; padding-top: 12px; border-top: 1px solid var(--border); }
.ql-chat-input {
  flex: 1; padding: 11px 16px; border-radius: 8px; border: 1px solid var(--border);
  background: var(--bg-card); color: var(--text-primary); font-family: var(--font-body);
  font-size: 0.9rem; outline: none; transition: border-color 0.2s;
}
.ql-chat-input:focus { border-color: var(--gold); }
.ql-chat-input::placeholder { color: var(--text-muted); }
.ql-chat-send {
  padding: 0 18px; border: none; border-radius: 8px; background: var(--gold);
  color: #0a0d13; font-family: var(--font-display); font-size: 0.78rem; font-weight: 600;
  letter-spacing: 0.06em; cursor: pointer; transition: all 0.2s;
}
.ql-chat-send:hover { background: #d97706; }

/* Quick chips */
.ql-chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px 0; }
.ql-chip {
  padding: 6px 12px; border-radius: 20px; border: 1px solid var(--border);
  background: transparent; color: var(--text-muted); font-family: var(--font-body);
  font-size: 0.78rem; cursor: pointer; transition: all 0.2s;
}
.ql-chip:hover { border-color: var(--gold); color: var(--gold); }

/* Calendar sync banner */
.ql-sync-banner {
  background: linear-gradient(135deg, rgba(6,182,212,0.08), rgba(139,92,246,0.08));
  border: 1px solid rgba(6,182,212,0.2); border-radius: 12px;
  padding: 16px 20px; margin-bottom: 16px; display: flex; align-items: center; gap: 14px;
}

/* Progress mini chart */
.ql-progress-chart { display: flex; align-items: flex-end; gap: 6px; height: 60px; }
.ql-progress-bar-outer { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.ql-progress-bar { border-radius: 3px 3px 0 0; transition: height 0.5s ease; min-height: 4px; }
.ql-progress-bar-label { font-family: var(--font-mono); font-size: 0.58rem; color: var(--text-muted); }

/* Streak */
.ql-streak {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px;
  border-radius: 20px; background: var(--gold-dim); border: 1px solid rgba(245,158,11,0.25);
  font-family: var(--font-mono); font-size: 0.72rem; color: var(--gold);
}

/* Section titles */
.ql-title { font-family: var(--font-display); font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; letter-spacing: 0.04em; }
.ql-desc { font-size: 0.92rem; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.5; }

/* Loading animation */
@keyframes ql-pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
.ql-loading-dot { animation: ql-pulse 1.4s ease-in-out infinite; }

/* Fade up */
@keyframes ql-fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.ql-fade { animation: ql-fadeUp 0.45s ease forwards; }

/* Compound box */
.ql-compound {
  background: linear-gradient(135deg, var(--emerald-dim), var(--violet-dim));
  border: 1px solid rgba(16,185,129,0.2); border-radius: 12px; padding: 18px 22px; margin-top: 16px;
}

/* Likelihood badge */
.ql-likelihood { display: inline-block; padding: 3px 11px; border-radius: 20px; font-family: var(--font-mono); font-size: 0.65rem; letter-spacing: 0.05em; text-transform: uppercase; font-weight: 500; }

/* Scrollbar */
.ql-chat-msgs::-webkit-scrollbar { width: 4px; }
.ql-chat-msgs::-webkit-scrollbar-track { background: transparent; }
.ql-chat-msgs::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
`;

// ─── SMALL COMPONENTS ────────────────────────────────────────────────────────

const Toggle = ({ on, onToggle }) => (
  <div className={`ql-toggle ${on ? "on" : ""}`} onClick={onToggle}><div className="ql-toggle-thumb" /></div>
);

const StatBar = ({ stat, delay = 0 }) => {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW((stat.level / stat.max) * 100), 80 + delay); return () => clearTimeout(t); }, [stat, delay]);
  const c = stat.level >= 7 ? "var(--emerald)" : stat.level >= 5 ? "var(--gold)" : "var(--rose)";
  const ti = stat.trend === "up" ? "▲" : stat.trend === "down" ? "▼" : "—";
  const tc = stat.trend === "up" ? "var(--emerald)" : stat.trend === "down" ? "var(--rose)" : "var(--text-muted)";
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>{stat.name}</span>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ color: tc, fontSize: "0.65rem" }}>{ti}</span>
          <span style={{ fontFamily: "var(--font-display)", fontSize: "0.82rem", color: c, fontWeight: 600 }}>{stat.level}/{stat.max}</span>
        </div>
      </div>
      <div className="ql-bar-bg"><div className="ql-bar-fill" style={{ width: `${w}%`, background: `linear-gradient(90deg, ${c}, ${c}88)` }} /></div>
      <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginTop: 3 }}>{stat.detail}</div>
    </div>
  );
};

const StepDots = ({ current, steps }) => (
  <div>
    <div className="ql-steps">{steps.map((_, i) => <div key={i} className={`ql-step-dot ${i === current ? "active" : i < current ? "done" : ""}`} />)}</div>
    <div className="ql-step-labels">{steps.map((s, i) => <span key={s} className={`ql-step-lbl ${i === current ? "active" : i < current ? "done" : ""}`}>{s}</span>)}</div>
  </div>
);

// ─── ONBOARDING SCREENS ──────────────────────────────────────────────────────

const ConsentScreen = ({ onProceed }) => {
  const [sources, setSources] = useState({ financial: true, health: true, calendar: true, social: true });
  const anyOn = Object.values(sources).some(Boolean);
  return (
    <div className="ql-fade">
      <div className="ql-title">Choose Your Data Sources</div>
      <div className="ql-desc">Questline analyzes your behavioral data to project future scenarios. Toggle which sources to include. Your data stays local.</div>
      {DATA_SOURCES.map(src => (
        <div key={src.id} className={`ql-card ${sources[src.id] ? "selected" : ""}`} onClick={() => setSources(s => ({ ...s, [src.id]: !s[src.id] }))} style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ fontSize: "1.5rem", width: 36, textAlign: "center" }}>{src.icon}</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: "0.95rem", marginBottom: 2 }}>{src.label}</div>
            <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>{src.desc}</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem", color: "var(--text-muted)", marginTop: 2 }}>{src.records}</div>
          </div>
          <Toggle on={sources[src.id]} onToggle={() => {}} />
        </div>
      ))}
      <div style={{ textAlign: "center", marginTop: 24 }}>
        <button className="ql-btn" disabled={!anyOn} onClick={() => onProceed(sources)}>Begin Analysis ⚔️</button>
        {!anyOn && <div style={{ fontSize: "0.78rem", color: "var(--rose)", marginTop: 6 }}>Enable at least one source</div>}
      </div>
    </div>
  );
};

const LoadingScreen = ({ onDone }) => {
  const stages = ["Normalizing data formats…", "Extracting time-series patterns…", "Detecting cross-domain correlations…", "Building character profile…", "Generating future scenarios…"];
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setStage(s => { if (s >= stages.length - 1) { clearInterval(iv); setTimeout(onDone, 500); return s; } return s + 1; }), 650);
    return () => clearInterval(iv);
  }, []);
  return (
    <div style={{ textAlign: "center", paddingTop: 60 }} className="ql-fade">
      <div style={{ fontSize: "1.8rem", marginBottom: 16 }}>⚔️</div>
      <div style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem", color: "var(--gold)", marginBottom: 22, letterSpacing: "0.06em" }}>Analyzing Your Journey</div>
      <div style={{ maxWidth: 300, margin: "0 auto" }}>
        {stages.map((s, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, opacity: i <= stage ? 1 : 0.2, transition: "opacity 0.4s" }}>
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: i < stage ? "var(--emerald)" : i === stage ? "var(--gold)" : "var(--border)", boxShadow: i === stage ? "0 0 8px rgba(245,158,11,0.5)" : "none" }} className={i === stage ? "ql-loading-dot" : ""} />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: i <= stage ? "var(--text-secondary)" : "var(--text-muted)" }}>{s}</span>
            {i < stage && <span style={{ color: "var(--emerald)", fontSize: "0.7rem", marginLeft: "auto" }}>✓</span>}
          </div>
        ))}
      </div>
    </div>
  );
};

const PatternsScreen = ({ onProceed }) => {
  const [tab, setTab] = useState("stats");
  return (
    <div className="ql-fade">
      <div style={{ display: "flex", gap: 3, marginBottom: 22, background: "rgba(30,41,59,0.4)", borderRadius: 7, padding: 3 }}>
        {[{ k: "stats", l: "Character Stats" }, { k: "patterns", l: "Detected Patterns" }].map(t => (
          <button key={t.k} onClick={() => setTab(t.k)} style={{ flex: 1, padding: "9px 14px", border: "none", borderRadius: 5, fontFamily: "var(--font-mono)", fontSize: "0.75rem", cursor: "pointer", transition: "all 0.2s", background: tab === t.k ? "var(--bg-elevated)" : "transparent", color: tab === t.k ? "var(--text-primary)" : "var(--text-muted)" }}>{t.l}</button>
        ))}
      </div>
      {tab === "stats" ? (
        <div>
          <div className="ql-title">Your Character Profile</div>
          <div className="ql-desc">Stats derived from your behavioral data.</div>
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 14, padding: 22 }}>
            {CHARACTER_STATS.map((s, i) => <StatBar key={s.name} stat={s} delay={i * 100} />)}
          </div>
        </div>
      ) : (
        <div>
          <div className="ql-title">Detected Patterns</div>
          <div className="ql-desc">{PATTERNS.filter(p => p.type === "cross").length} cross-domain insights found.</div>
          {PATTERNS.map((p, i) => (
            <div key={p.id} className="ql-fade" style={{ animationDelay: `${i * 60}ms`, background: "var(--bg-card)", border: `1px solid ${p.type === "cross" ? "rgba(139,92,246,0.2)" : "var(--border)"}`, borderRadius: 11, padding: "14px 18px", marginBottom: 10 }}>
              <div style={{ display: "flex", gap: 5, marginBottom: 7, flexWrap: "wrap", alignItems: "center" }}>
                <span className={`ql-tag ${p.type}`}>{p.type === "cross" ? "⚡ Cross" : "Single"}</span>
                {p.type === "cross" ? p.domains.map(d => <span key={d} className={`ql-tag ${d}`}>{d}</span>) : <span className={`ql-tag ${p.domain}`}>{p.domain}</span>}
                <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-muted)" }}>#{p.id}</span>
              </div>
              <div style={{ fontSize: "0.88rem", lineHeight: 1.5 }}>{p.text}</div>
            </div>
          ))}
        </div>
      )}
      <div style={{ textAlign: "center", marginTop: 24 }}><button className="ql-btn" onClick={onProceed}>View My Futures →</button></div>
    </div>
  );
};

const ScenariosScreen = ({ onSelect }) => {
  const [sel, setSel] = useState(null);
  const [tf, setTf] = useState("y1");
  return (
    <div className="ql-fade">
      <div className="ql-title">Your Possible Futures</div>
      <div className="ql-desc">Select the future you want to build toward. Questline will plan your week around it.</div>
      <div className="ql-tf">{[{ k: "y1", l: "1 Year" }, { k: "y5", l: "5 Years" }, { k: "y10", l: "10 Years" }].map(t => <button key={t.k} className={tf === t.k ? "active" : ""} onClick={() => setTf(t.k)}>{t.l}</button>)}</div>
      {SCENARIOS.map(sc => (
        <div key={sc.id} className={`ql-sc ${sel === sc.id ? "selected" : ""}`} onClick={() => setSel(sc.id)}>
          <div className="ql-sc-bar" style={{ background: sc.color }} />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
            <div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "1.05rem", fontWeight: 600, marginBottom: 4 }}>{sc.title}</div>
              <span className="ql-likelihood" style={{ background: `${sc.color}15`, color: sc.color, border: `1px solid ${sc.color}35` }}>{sc.likelihood}</span>
            </div>
            <div style={{ width: 22, height: 22, borderRadius: "50%", border: `2px solid ${sel === sc.id ? sc.color : "var(--border-glow)"}`, display: "flex", alignItems: "center", justifyContent: "center", background: sel === sc.id ? sc.color : "transparent", transition: "all 0.2s" }}>
              {sel === sc.id && <span style={{ color: "#0a0d13", fontSize: "0.65rem", fontWeight: 700 }}>✓</span>}
            </div>
          </div>
          <div style={{ fontSize: "0.87rem", lineHeight: 1.5, color: "var(--text-secondary)", marginBottom: 10 }}>{sc.timeframes[tf]}</div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontStyle: "italic", borderTop: "1px solid var(--border)", paddingTop: 8 }}>{sc.narrative}</div>
        </div>
      ))}
      <div style={{ textAlign: "center", marginTop: 24 }}><button className="ql-btn" disabled={!sel} onClick={() => onSelect(sel)}>Lock In My Quest →</button></div>
    </div>
  );
};

// ─── DASHBOARD TABS ──────────────────────────────────────────────────────────

const DashOverview = ({ scenario, weekActions, checked, onCheck, weekHistory }) => {
  const sc = SCENARIOS.find(s => s.id === scenario);
  const todayIdx = new Date().getDay();
  const todayName = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][todayIdx];
  const todayActions = weekActions.filter(a => a.day === todayName);
  const weekCompleted = [...checked].length;
  const weekTotal = weekActions.length;
  const streak = WEEK_HISTORY.length;

  return (
    <div className="ql-fade">
      {/* Scenario banner */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: sc.color }} />
        <div>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "1.05rem", fontWeight: 600 }}>Active Quest: {sc.title}</div>
          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>{sc.likelihood} path · Week {streak + 1}</div>
        </div>
        <div style={{ marginLeft: "auto" }}><div className="ql-streak">🔥 {streak} week streak</div></div>
      </div>

      {/* Weekly progress chart */}
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: "16px 18px", marginBottom: 16 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 10, letterSpacing: "0.05em", textTransform: "uppercase" }}>Weekly Completion</div>
        <div className="ql-progress-chart">
          {[...WEEK_HISTORY, { week: `Week ${streak + 1}`, completed: weekCompleted, total: weekTotal }].map((w, i) => {
            const pct = (w.completed / w.total) * 100;
            const isCurrent = i === WEEK_HISTORY.length;
            return (
              <div key={i} className="ql-progress-bar-outer">
                <div className="ql-progress-bar" style={{ width: "100%", height: `${Math.max(pct, 8)}%`, background: isCurrent ? "var(--gold)" : "var(--emerald)", opacity: isCurrent ? 1 : 0.6 }} />
                <div className="ql-progress-bar-label" style={{ color: isCurrent ? "var(--gold)" : "var(--text-muted)" }}>{w.week.replace("Week ", "W")}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Today's actions */}
      <div style={{ marginTop: 8 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 10, letterSpacing: "0.05em", textTransform: "uppercase" }}>
          Today — {todayName} · {todayActions.length} actions
        </div>
        {todayActions.length === 0 && (
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: 20, textAlign: "center", color: "var(--text-muted)", fontSize: "0.88rem" }}>
            No actions scheduled for today. Check the weekly view for upcoming tasks.
          </div>
        )}
        {todayActions.map(a => (
          <div key={a.id} style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 11, padding: "14px 16px", marginBottom: 8, opacity: checked.has(a.id) ? 0.45 : 1, transition: "opacity 0.3s" }}>
            <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <div className={`ql-check ${checked.has(a.id) ? "done" : ""}`} onClick={() => onCheck(a.id)}>✓</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "0.9rem", fontWeight: 600, textDecoration: checked.has(a.id) ? "line-through" : "none" }}>{a.icon} {a.action}</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}>{a.rationale}</div>
              </div>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-muted)", background: "var(--bg-elevated)", padding: "2px 8px", borderRadius: 10, whiteSpace: "nowrap" }}>~{a.time}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const DashWeekly = ({ weekActions, checked, onCheck, calSynced, onSyncCal }) => {
  const [filterDay, setFilterDay] = useState("All");
  const filtered = filterDay === "All" ? weekActions : weekActions.filter(a => a.day === filterDay);
  const completedCount = [...checked].filter(id => weekActions.find(a => a.id === id)).length;

  return (
    <div className="ql-fade">
      {/* Calendar sync banner */}
      <div className="ql-sync-banner">
        <div style={{ fontSize: "1.4rem" }}>📅</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: "0.92rem", marginBottom: 2 }}>
            {calSynced ? "Synced to Google Calendar" : "Sync to Google Calendar"}
          </div>
          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            {calSynced ? "All actions are on your calendar. Changes sync automatically." : "Add this week's actions as calendar events with reminders."}
          </div>
        </div>
        <button className={calSynced ? "ql-btn-sm active" : "ql-btn-sm"} onClick={onSyncCal}>
          {calSynced ? "✓ Synced" : "Sync Now"}
        </button>
      </div>

      {/* Progress bar */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)" }}>THIS WEEK</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--emerald)" }}>{completedCount}/{weekActions.length}</span>
        </div>
        <div className="ql-bar-bg" style={{ height: 5 }}><div className="ql-bar-fill" style={{ width: `${(completedCount / weekActions.length) * 100}%`, background: "linear-gradient(90deg, var(--emerald), var(--cyan))" }} /></div>
      </div>

      {/* Day filter */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16, flexWrap: "wrap" }}>
        {["All", ...DAYS].map(d => (
          <button key={d} className={`ql-btn-sm ${filterDay === d ? "active" : ""}`} onClick={() => setFilterDay(d)}>
            {d}
          </button>
        ))}
      </div>

      {/* Actions list */}
      {filtered.map(a => (
        <div key={a.id} style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 11, padding: "14px 16px", marginBottom: 8, opacity: checked.has(a.id) ? 0.4 : 1, transition: "opacity 0.3s" }}>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
            <div className={`ql-check ${checked.has(a.id) ? "done" : ""}`} onClick={() => onCheck(a.id)}>✓</div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <div style={{ fontSize: "0.9rem", fontWeight: 600, textDecoration: checked.has(a.id) ? "line-through" : "none" }}>{a.icon} {a.action}</div>
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                <span className={`ql-tag ${a.domain}`}>{a.domain}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-muted)" }}>{a.day} · {a.cal} · ~{a.time}</span>
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 6, lineHeight: 1.45 }}>{a.rationale}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

const DashStats = ({ weekHistory }) => {
  const statNames = ["Financial Literacy", "Physical Vitality", "Social Bond", "Time Mastery", "Self Awareness"];
  const statKeys = ["financial", "health", "social", "time", "self"];
  const statColors = ["var(--gold)", "var(--rose)", "var(--emerald)", "var(--cyan)", "var(--violet)"];

  return (
    <div className="ql-fade">
      <div className="ql-title">Character Stats</div>
      <div className="ql-desc">Your attributes derived from behavioral data. Track how they shift week over week.</div>

      {/* Current stats */}
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 14, padding: 22, marginBottom: 20 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 14, letterSpacing: "0.05em", textTransform: "uppercase" }}>Current Levels</div>
        {CHARACTER_STATS.map((s, i) => <StatBar key={s.name} stat={s} delay={i * 80} />)}
      </div>

      {/* Stat history over weeks */}
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 14, padding: 22 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 14, letterSpacing: "0.05em", textTransform: "uppercase" }}>Progress Over Time</div>
        {statNames.map((name, si) => {
          const key = statKeys[si];
          const color = statColors[si];
          const current = CHARACTER_STATS[si].level;
          const history = weekHistory.map(w => w.stats[key]);
          const allVals = [...history, current];
          return (
            <div key={name} style={{ marginBottom: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>{name}</span>
                <span style={{ fontFamily: "var(--font-display)", fontSize: "0.8rem", color, fontWeight: 600 }}>{current}/10</span>
              </div>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 36 }}>
                {allVals.map((v, wi) => {
                  const isCurrent = wi === allVals.length - 1;
                  return (
                    <div key={wi} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
                      <div style={{
                        width: "100%", borderRadius: "3px 3px 0 0",
                        height: `${Math.max((v / 10) * 100, 10)}%`,
                        background: color,
                        opacity: isCurrent ? 1 : 0.35,
                        transition: "height 0.5s ease",
                      }} />
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.52rem", color: isCurrent ? color : "var(--text-muted)" }}>
                        {isCurrent ? "Now" : `W${wi + 1}`}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Detected patterns */}
      <div style={{ marginTop: 20 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 10, letterSpacing: "0.05em", textTransform: "uppercase" }}>Active Patterns</div>
        {PATTERNS.map(p => (
          <div key={p.id} style={{ background: "var(--bg-card)", border: `1px solid ${p.type === "cross" ? "rgba(139,92,246,0.2)" : "var(--border)"}`, borderRadius: 10, padding: "12px 16px", marginBottom: 8 }}>
            <div style={{ display: "flex", gap: 5, marginBottom: 5, flexWrap: "wrap", alignItems: "center" }}>
              <span className={`ql-tag ${p.type}`}>{p.type === "cross" ? "⚡ Cross" : "Single"}</span>
              {p.type === "cross" ? p.domains.map(d => <span key={d} className={`ql-tag ${d}`}>{d}</span>) : <span className={`ql-tag ${p.domain}`}>{p.domain}</span>}
            </div>
            <div style={{ fontSize: "0.85rem", lineHeight: 1.45, color: "var(--text-secondary)" }}>{p.text}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

const DashChat = ({ scenario, weekActions }) => {
  const sc = SCENARIOS.find(s => s.id === scenario);
  const [messages, setMessages] = useState([
    { role: "agent", text: `Hey! I'm your Questline guide. You're on the "${sc.title}" path. I can help adjust any of your weekly actions — if something feels too hard, not relevant, or you want to swap it out, just tell me. What's on your mind?` }
  ]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const msgsEndRef = useRef(null);

  useEffect(() => { msgsEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const getResponse = useCallback((msg) => {
    const lower = msg.toLowerCase();
    if (lower.includes("walk") || lower.includes("step") || lower.includes("exercise")) return AGENT_RESPONSES.walk;
    if (lower.includes("sav") || lower.includes("money") || lower.includes("$") || lower.includes("transfer")) return AGENT_RESPONSES.savings;
    if (lower.includes("time") || lower.includes("busy") || lower.includes("schedule")) return AGENT_RESPONSES.time;
    if (lower.includes("meeting") || lower.includes("cancel")) return AGENT_RESPONSES.meeting;
    if (lower.includes("cook") || lower.includes("meal") || lower.includes("prep") || lower.includes("lunch")) return AGENT_RESPONSES.cooking;
    if (lower.includes("hard") || lower.includes("overwhelm") || lower.includes("too much") || lower.includes("daunting") || lower.includes("can't")) return AGENT_RESPONSES["too hard"];
    return AGENT_RESPONSES.default;
  }, []);

  const send = () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages(m => [...m, { role: "user", text: userMsg }]);
    setInput("");
    setTyping(true);
    setTimeout(() => {
      setMessages(m => [...m, { role: "agent", text: getResponse(userMsg) }]);
      setTyping(false);
    }, 800 + Math.random() * 600);
  };

  const chips = ["This feels too hard", "Can we adjust the walks?", "I don't have time", "Cooking is overwhelming", "Can I skip savings this week?"];

  return (
    <div className="ql-fade ql-chat-container">
      <div className="ql-chat-msgs">
        {messages.map((m, i) => (
          <div key={i} className={`ql-chat-bubble ${m.role}`}>{m.text}</div>
        ))}
        {typing && (
          <div className="ql-chat-bubble agent" style={{ color: "var(--text-muted)" }}>
            <span className="ql-loading-dot">●</span> <span className="ql-loading-dot" style={{ animationDelay: "0.2s" }}>●</span> <span className="ql-loading-dot" style={{ animationDelay: "0.4s" }}>●</span>
          </div>
        )}
        <div ref={msgsEndRef} />
      </div>
      {messages.length < 3 && (
        <div className="ql-chips">
          {chips.map(c => <button key={c} className="ql-chip" onClick={() => { setInput(c); }}>{c}</button>)}
        </div>
      )}
      <div className="ql-chat-input-row">
        <input className="ql-chat-input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} placeholder="Tell me what's not working…" />
        <button className="ql-chat-send" onClick={send}>Send</button>
      </div>
    </div>
  );
};

// ─── MAIN APP ────────────────────────────────────────────────────────────────

export default function QuestlineApp() {
  // App state
  const [onboarded, setOnboarded] = useState(false);
  const [onboardStep, setOnboardStep] = useState("consent"); // consent, loading, patterns, scenarios
  const [scenario, setScenario] = useState(null);
  const [dashTab, setDashTab] = useState("overview");
  const [checked, setChecked] = useState(new Set());
  const [calSynced, setCalSynced] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  const weekActions = scenario ? buildWeeklyActions(scenario) : [];

  const toggleCheck = (id) => setChecked(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const finishOnboarding = (scId) => {
    setScenario(scId);
    setOnboarded(true);
    setShowOnboarding(false);
    setOnboardStep("consent");
    setChecked(new Set());
    setCalSynced(false);
    setDashTab("overview");
  };

  const restartOnboarding = () => {
    setShowOnboarding(true);
    setOnboardStep("consent");
  };

  const obStepIdx = { consent: 0, loading: 0, patterns: 1, scenarios: 2 }[onboardStep];
  const isOnboarding = !onboarded || showOnboarding;

  return (
    <>
      <style>{CSS}</style>
      <div className="ql-noise" />
      <div className="ql-app">
        {/* Header */}
        <div className="ql-header">
          <h1>Questline</h1>
          <div className="sub">{isOnboarding ? "Map your journey. Choose your future. Act today." : "Your quest is in progress."}</div>
          {!isOnboarding && onboarded && (
            <button className="ql-reanalyze" onClick={restartOnboarding}>🔄 Re-analyze</button>
          )}
        </div>

        {/* ── ONBOARDING FLOW ── */}
        {isOnboarding && (
          <>
            <StepDots current={obStepIdx} steps={["Consent", "Patterns", "Scenarios"]} />

            {onboardStep === "consent" && <ConsentScreen onProceed={() => setOnboardStep("loading")} />}
            {onboardStep === "loading" && <LoadingScreen onDone={() => setOnboardStep("patterns")} />}
            {onboardStep === "patterns" && <PatternsScreen onProceed={() => setOnboardStep("scenarios")} />}
            {onboardStep === "scenarios" && <ScenariosScreen onSelect={finishOnboarding} />}

            {showOnboarding && onboardStep === "consent" && (
              <div style={{ textAlign: "center", marginTop: 12 }}>
                <button className="ql-btn-ghost" onClick={() => setShowOnboarding(false)}>← Back to Dashboard</button>
              </div>
            )}
          </>
        )}

        {/* ── DASHBOARD ── */}
        {!isOnboarding && onboarded && (
          <>
            <div className="ql-nav">
              {[
                { k: "overview", l: "⚔️ Overview" },
                { k: "weekly", l: "📋 This Week" },
                { k: "stats", l: "🛡️ Stats" },
                { k: "chat", l: "💬 Adjust" },
              ].map(t => (
                <button key={t.k} className={dashTab === t.k ? "active" : ""} onClick={() => setDashTab(t.k)}>{t.l}</button>
              ))}
            </div>

            {dashTab === "overview" && (
              <DashOverview scenario={scenario} weekActions={weekActions} checked={checked} onCheck={toggleCheck} weekHistory={WEEK_HISTORY} />
            )}

            {dashTab === "weekly" && (
              <DashWeekly weekActions={weekActions} checked={checked} onCheck={toggleCheck} calSynced={calSynced} onSyncCal={() => setCalSynced(!calSynced)} />
            )}

            {dashTab === "stats" && (
              <DashStats weekHistory={WEEK_HISTORY} />
            )}

            {dashTab === "chat" && (
              <DashChat scenario={scenario} weekActions={weekActions} />
            )}
          </>
        )}
      </div>
    </>
  );
}
