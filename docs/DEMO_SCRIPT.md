# Gauntlet — 5-Minute Demo Script

A timed shot list. **[DO]** = what to click. **[SAY]** = narration (paraphrase, don't read robotically).
Record at the deployed URL (or `http://localhost:8000`). Window: just the browser.

## Before you hit record
- Server up / URL live. If you'll show the LLM, `ANTHROPIC_API_KEY` is set (Render secret or local `.env`).
- Open the page fresh, agent **paused**, **Recovery: ON**, worker = **Heuristic** (the default).
- Have the repo open in a second tab (for the ~10s code peek).
- Screen recorder with mic (macOS: ⌘⇧5). Aim for 4:45–5:00.

---

### 0:00–0:30 — What this is
**[SAY]** "The challenge was to build a *harness* — not an agent. The harness is the cage an AI agent
lives inside: guardrails, checkpoints, material handling, and alarms. My agent plays Tetris by driving a
controller — which is my actual domain, I build game controllers. The harness is what's being evaluated."
**[DO]** Gesture at the on-screen explainer and the four pillar labels on the right.

### 0:30–1:30 — The four pillars, live
**[DO]** Press **Start** (heuristic is the default — it plays cleanly).
**[SAY]** "Four distinct components, all separate from the agent:
- **Agent intent** — the controller buttons the agent wants to press.
- 🛡️ **Guardrails** — declared rules validate every input *before* it reaches the game.
- ✅ **Checkpoints** — explicit pass/fail read from game state: stack height, holes, game-over. Watch them go green.
- 📦 **Material** — every step is captured and persisted.
- 🚨 **Alarms** — structured: type, severity, context, recommended action."
**[DO]** Point at a checkpoint flipping, and the calm `[LOW]` alarm when a hole appears.

### 1:30–2:25 — The graded must: behavior changes from feedback → escalation
**[DO]** Click **Reckless**. Let it stack.
**[SAY]** "This agent plays badly on purpose. Watch the harness react: `STACK_HEIGHT_SAFE` goes red,
a `CHECKPOINT_FAILED` alarm fires, and the harness feeds corrective feedback into the agent. The
agent's behavior is driven by that feedback — that's the core requirement."
**[DO]** Let it reach the danger line so a HIGH/CRITICAL alarm shows.

### 2:25–3:25 — Dual-worker recovery + live swap (the bonus)
**[SAY]** "But the harness doesn't just stop a failing agent — it *manages* it. On repeated failure it
hands off to a recovery worker."
**[DO]** Keep watching: **WORKER flips to `heuristic`** (`RECOVERY_SWAP` alarm) → it digs the stack
down → `RECOVERED` → hands back.
**[SAY]** "That's a real safety pattern — a capable fallback takes over, then returns control. And any
agent drops into the same interface with zero harness changes."
**[DO]** Toggle **Recovery: OFF**, let reckless run again → it escalates to a human **STOP** (`ESCALATE`,
recommended action: request human intervention). Toggle back ON.

### 3:25–4:15 — The real AI: an LLM driving the controller
**[DO]** Click **State · Haiku** (or **Vision · Haiku** for the "it sees the screen" beat). Press Start.
**[SAY]** "And here's a real modern LLM driving the same controller — reading the board and pressing
buttons, like a human." (Vision mode: "it's literally looking at a screenshot.")
**[SAY] (honest + strong)** "It plays imperfectly — reading a Tetris board and reacting is hard for an
LLM. That's exactly the point: the harness governs a real, fallible AI the same way it governs the
others — grading it, nudging it, and handing off when it's in trouble."

### 4:15–4:45 — Material / replay + portability
**[DO]** Pause, click **Replay last run**.
**[SAY]** "Every checkpoint and board is persisted, so any run replays from the start — that's the
material pillar. And the agent is fully swappable: a scripted bot, a search AI, or an LLM, all behind
one `decide(state) -> action` interface."

### 4:45–5:00 — Close
**[DO]** Quick cut to the repo (`HARNESS.md` / the `harness/` folder).
**[SAY]** "The harness — not the agent — is the system: four declared pillars, governing a swappable
agent, with feedback, recovery, and human escalation. Thanks."

---

## Rubric coverage (every box ticked on camera)
- Four pillars, separate from the worker → 0:30 segment
- Behavior changes on guardrail/checkpoint feedback → 1:30
- Guardrails declared → 0:30 (+ optional code peek)
- Checkpoints explicit pass/fail → 0:30
- Structured alarms (type/severity/context/action) → 0:30 & 1:30
- Real input from your own work (controller domain, real game) → 0:00
- Swappable agent, no harness changes (Should) → 2:25 & 4:15
- Replay from checkpoint (Should) → 4:15
- Human escalation (Should) → 2:25 (Recovery OFF)
- Second worker swapped in live (Bonus) → 2:25

## Tips
- The reckless → recovery → escalate arc is your strongest 60 seconds. Rehearse it once.
- If the LLM segment is slow, narrate over the "🤔 thinking" pause — it reads as deliberation.
- Keep the heuristic as the opener; it looks the best and needs no key.
```
