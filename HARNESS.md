# HARNESS.md — Gauntlet Joypad Harness

A runtime safety harness that governs an AI game-playing agent. The agent plays
**like a human**: it sees the rendered screen (pixels) and presses controller
buttons. The harness is the cage around it — it decides which inputs are legal,
measures real progress, carries game state in and out, and raises structured
alarms. When the agent fails, the harness feeds corrective feedback back in and
the agent changes course; on repeated failure it stops and asks a human.

**The harness, not the agent, is the system being evaluated.** Demo domain:
Tetris (a custom browser game), chosen because its forgiving cadence lets a
vision-LLM actually play by looking at the screen.

---

## System shape (as built)

```
  BROWSER (the "video")                    SERVER (FastAPI, the harness)
  ┌───────────────────────┐   observe      ┌──────────────────────────────┐
  │ Tetris on a <canvas>  │  state+frame   │ HarnessSession (per WS conn)  │
  │ renders the game      │ ─────────────▶ │   loop.observe(prev,new) ✅📦🚨 │
  │ applies controller    │                │   loop.decide(state)      🛡️   │
  │ inputs                │ ◀───────────── │     worker.decide(...)         │
  │ live dashboard        │  act + events  │   (scripted | heuristic |      │
  └───────────────────────┘                │    claude-vision)              │
        ▲  agent sees pixels               └──────────────────────────────┘
        │  referee reads ground-truth state (never shown to the agent)
```

- **Agent** = the worker. It perceives only the frame (an image). It is swappable
  and is *not* a graded pillar — it's the thing being governed.
- **Referee** = the harness. It reads ground-truth state (board, score, lines,
  stack height, holes) to grade. A referee knowing the score is not the player
  cheating.

Code: `harness/` (pillars + loop + session), `workers/` (agents),
`server/` (FastAPI + the browser game/dashboard).

---

## The four pillars (each a separate, identifiable component)

### 🛡️ Guardrails — `harness/guardrails.py`
A **declared** list of rules on controller input, validated *before* an action
reaches the game:
```python
DEFAULT_GUARDRAILS = [AllowedButtons(), MaxHoldFrames(120), RateLimit(4), NoImpossibleCombos()]
```
`GuardrailSet.validate(action, state)` returns the first blocking `Verdict`. A
blocked action never executes; the reason is fed back to the agent to retry. If
the agent can't produce a legal action within the retry budget, a
`GUARDRAIL_DEADLOCK` alarm fires and the run stops.

### ✅ Checkpoints — `harness/checkpoints.py`
Explicit **pass/fail** evaluation read from ground-truth state (objective, no
fuzzy judging):
```python
DEFAULT_CHECKPOINTS = [StackHeightSafe(danger=12), NotGameOver(), NoNewHoles()]
```
Each returns a `CheckpointResult(name, passed, detail)`. Results are persisted.
The first checkpoint is the "primary" one whose repeated failure escalates.

### 📦 Material handling — `harness/material.py`
Clean in/out + persistence. `normalize(raw)` turns the browser's state dict into
a typed `GameState`. Every step is persisted to SQLite (`persist`), and any run
can be replayed (`replay`) or resumed from a frame (`load_state`).

### 🚨 Alarms — `harness/alarms.py`
Structured failures: `Alarm(type, severity, context, recommended_action)` with
`Severity ∈ {LOW, MEDIUM, HIGH, CRITICAL}`. Emitted on a bus the dashboard
subscribes to. Examples: `CHECKPOINT_FAILED` (HIGH), `ESCALATE` (CRITICAL),
`GAME_OVER` (CRITICAL), `GUARDRAIL_BLOCKED` (HIGH), `WORKER_ERROR` (CRITICAL).

---

## The control loop — `harness/loop.py`

Action-window model (one decision per beat, not per frame), split into two
reusable halves so both the local runner and the browser path share it:

- **`decide(state)`** → runs the worker, validates with guardrails (with retry),
  returns a legal `Action` (or stops on deadlock).
- **`observe(prev, new, action)`** → grades checkpoints, persists, then drives the
  behavior-change loop:
  - **game over** → `GAME_OVER` alarm, STOP.
  - **checkpoint(s) failed** → build a feedback hint, emit `CHECKPOINT_FAILED`.
    The same agent gets the hint on its next decision and changes course.
  - **primary checkpoint fails `escalate_after` times in a row** → `ESCALATE`
    (CRITICAL), STOP and ask a human.
  - **all pass** → clear feedback, reset the streak.

This is the graded "must": *the agent's behavior changes meaningfully based on
guardrail/checkpoint feedback.* Watch the reckless worker stack up, trip
`STACK_HEIGHT_SAFE`, fire an alarm, and (with a smarter worker) recover.

---

## Worker independence (Should) + live swap (Bonus)

Any worker implementing `decide(state, feedback) -> Action` drops in with **no
harness changes** (`workers/base.py`). Three ship today:

| Worker | Perception | Behavior |
|---|---|---|
| `scripted` | none | Reckless (drops straight) — demos escalation/STOP |
| `heuristic` | ground-truth board | Competent Tetris AI (El-Tetris) — plays low/flat |
| `claude` | **vision (the frame)** | Sees the board as an image, returns a controller action via structured output (Haiku 4.5) |

Swap live from the dashboard (`set_worker` over WS) — verified scripted →
heuristic mid-run. The Claude worker receives only the rendered frame via
`set_frame()`; it never sees the ground-truth board.

---

## Human escalation (Should)

Repeated primary-checkpoint failure (or a guardrail deadlock) trips a `STOP`
state with an `ESCALATE` (CRITICAL) alarm whose `recommended_action` is "request
human intervention." The dashboard surfaces the STOP and the human resets or
swaps the worker rather than letting the agent guess.

## Replay (Should)

Every checkpoint + state snapshot is written to SQLite, so a run can be replayed
from any frame forward without re-running prior steps (`MaterialHandler.replay` /
`load_state`).

## Domain portability

Swap the checkpoints + game and the same harness governs a different domain — the
loop, guardrails, alarms, material, and worker contract are game-agnostic. (The
project pivoted from a Mario/RAM concept to Tetris/vision without touching the
pillar interfaces.)

---

## Running it

```bash
# one-time: deps in a venv
uv venv .venv && uv pip install --python .venv -r requirements.txt

# verification hook (must stay green)
.venv/bin/python -m pytest -q

# run the harness + game + dashboard
.venv/bin/python -m uvicorn server.app:create_app --factory --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000  → press Start, swap workers, watch the pillars fire
```

The Claude (vision) worker needs `ANTHROPIC_API_KEY` in the environment; the
scripted and heuristic workers run with no key.

---

## Requirements coverage

| Requirement | Where |
|---|---|
| Must — four pillars, separate from worker | `harness/{guardrails,checkpoints,material,alarms}.py`; worker in `workers/` |
| Must — behavior changes on feedback | `loop.observe` feedback loop (reckless → alarm → hint → adapt) |
| Must — guardrails declared | literal `DEFAULT_GUARDRAILS` |
| Must — checkpoints explicit pass/fail | `CheckpointResult.passed` |
| Must — structured alarms | `Alarm{type, severity, context, recommended_action}` |
| Must — real input from own work | controller-input domain (joypad); a real game played live |
| Must — HARNESS.md | this file |
| Should — swappable agent | `Worker` protocol, zero harness changes |
| Should — replay from checkpoint | SQLite `replay` / `load_state` |
| Should — human escalation | `ESCALATE` STOP state |
| Bonus — swap a second worker live | scripted ↔ heuristic ↔ claude over WS |

---

## File map

```
harness/   types · guardrails · checkpoints · material · alarms · loop · session · adapters
workers/   base · scripted (reckless) · heuristic (Tetris AI) · claude (vision)
server/    app.py (FastAPI + WS) · static/{index.html (game+dashboard), tetris.js}
tests/     30+ tests — the Ralph verification hook
docs/      Harness_Planning.* (1-page plan) · challenge spec
```
