# Joypad Harness — Architecture

**A runtime safety harness that governs any AI game-playing agent.**

The agent plays a game through a controller interface. The harness is everything
wrapped around it: it decides what controller inputs are legal, measures whether
the agent is actually making progress, carries game state in and out, and raises
structured alarms when things go wrong. When the agent gets stuck, the harness
feeds corrective feedback back into it, and the agent changes what it does.

> The harness, not the agent, is the system being evaluated. Agents focus on
> playing. The harness focuses on constraints.

---

## Thesis

Drop in any worker that implements `decide(state) -> action` — GPT, Claude, a
local model, or a scripted bot — and the harness governs it without changes. The
game is Super Mario (browser NES emulator) at demo time, but the harness is
domain-shaped around *controller input*, which is the engineer's real-world
domain (joypad/controller hardware and software).

---

## The four pillars (graded)

| Pillar | Responsibility in this harness |
|---|---|
| 🛡️ **Guardrails** | Declared rules on controller actions: allowed buttons, max hold duration, rate limits, no physically-impossible input combos. Validated *before* an action reaches the game. |
| ✅ **Checkpoints** | Explicit pass/fail evaluation of progress measured from game state: forward progress, score delta, life lost, level advance. Results persisted for replay. |
| 📦 **Material Handling** | Capture frames, normalize raw pixels into agent-readable state, persist every checkpoint to SQLite, replay a run from any checkpoint forward. |
| 🚨 **Alarms** | Structured failure objects: `{type, severity, context, recommended_action}`. Drive escalation and recovery. |

The **worker agent** is deliberately *not* a pillar. It is the thing being
governed, and it is swappable.

---

## Control loop (action-window model)

An LLM cannot be called 60 times a second. So the loop does **not** run per
frame. The agent decides an *intent* over a window of frames; the harness
executes it, then evaluates the result. This is what makes the design feasible
in real time.

```
                ┌──────────────────────────────────────────────┐
                │                                                │
                ▼                                                │
   ┌────────────────────────┐                                   │
   │ 📦 MATERIAL HANDLER     │  capture frame, normalize state   │
   │    state = read_game()  │                                   │
   └───────────┬────────────┘                                   │
               │ state                                           │
               ▼                                                 │
   ┌────────────────────────┐                                   │
   │ 🤖 WORKER AGENT         │  decide(state) -> intended action │
   │    (Claude / GPT / bot) │  e.g. {button:"RIGHT", hold:60}   │
   └───────────┬────────────┘                                   │
               │ proposed action                                 │
               ▼                                                 │
   ┌────────────────────────┐   BLOCKED                         │
   │ 🛡️ GUARDRAILS           │ ───────────► feed reason back ────┤
   │  validate action legal? │             (agent re-decides)    │
   └───────────┬────────────┘                                   │
               │ allowed                                         │
               ▼                                                 │
   ┌────────────────────────┐                                   │
   │ 🎮 CONTROLLER OUTPUT    │  execute action for the window    │
   └───────────┬────────────┘                                   │
               │                                                 │
               ▼                                                 │
   ┌────────────────────────┐                                   │
   │ ✅ CHECKPOINT           │  measure state delta -> PASS/FAIL │
   │  persist result (SQLite)│                                   │
   └───────────┬────────────┘                                   │
        PASS    │    FAIL                                        │
        ────────┘     │                                         │
                      ▼                                         │
   ┌────────────────────────┐                                  │
   │ 🚨 ALARM + FEEDBACK     │                                  │
   │  1st/2nd FAIL: feed     │ ── corrective feedback ──────────┘
   │   "you're stuck, try X" │    (THE behavior-change loop)
   │  Nth FAIL: escalate     │
   │   STOP → human, or swap │
   │   recovery worker       │
   └────────────────────────┘
```

### The centerpiece: behavior changes from feedback

This is the harness's most important graded requirement — *the agent's behavior
changes meaningfully based on checkpoint feedback.*

When `FORWARD_PROGRESS` fails, the harness does not silently retry the same
thing. It injects a structured note into the agent's next context:

```
checkpoint FORWARD_PROGRESS failed: x-position unchanged for 120 frames.
hint: a wall or pipe is likely blocking you. try JUMP or JUMP+RIGHT.
```

The same agent then proposes a different action and gets past the obstacle. That
visible change — stuck, told why, adapts, succeeds — is the demo's hero moment.
Worker-swapping is the *encore* (portability bonus), not a substitute for this.

---

## Component contracts

### Worker interface (swappable)
```python
class Worker(Protocol):
    def decide(self, state: GameState) -> Action: ...
```
`GPTWorker`, `ClaudeWorker`, `ScriptedWorker` all implement this. The harness
holds a `Worker`, never a concrete model. Swapping a worker requires zero harness
changes (the "Should" requirement) and enables the demo bonus (swap a recovery
worker live).

### Guardrails (declared, not implicit)
A literal, inspectable ruleset — not logic buried in the loop:
```python
GUARDRAILS = [
    AllowedButtons({"LEFT","RIGHT","A","B","UP","DOWN","START"}),
    MaxHoldFrames(120),                 # no single input held forever
    RateLimit(max_actions_per_sec=10),  # no input flooding
    NoImpossibleCombos({("LEFT","RIGHT")}),  # can't press opposing dirs
]
```
Each guardrail returns allow / block(reason). A block never reaches the game; the
reason is fed back to the agent.

### Checkpoint contract (explicit pass/fail, persisted)
```python
@dataclass
class CheckpointResult:
    name: str          # FORWARD_PROGRESS
    passed: bool
    detail: str        # "x +7px over 60 frames"
    state_snapshot: dict   # persisted to SQLite for replay
```
Example checkpoints: `FORWARD_PROGRESS`, `SCORE_INCREASED`, `STILL_ALIVE`,
`LEVEL_ADVANCED`. All measured objectively from game state — no fuzzy LLM
judging.

### Alarm schema (structured)
```python
@dataclass
class Alarm:
    type: str          # AGENT_STUCK
    severity: str      # LOW | MEDIUM | HIGH | CRITICAL
    context: dict      # {frames_stuck:120, x:412, last_action:"RIGHT"}
    recommended_action: str  # "switch recovery worker" / "escalate to human"
```
Example: `AGENT_STUCK (HIGH)` — no forward progress for 120 frames →
recommended action: feed jump hint, then escalate if it persists.

### Material handling (capture, normalize, persist, replay)
- **Capture:** Playwright screenshots the browser game canvas each window.
- **Normalize:** raw pixels → compact `GameState` the agent can reason over
  (and/or a downscaled image for the vision worker).
- **Persist:** every `CheckpointResult` + state snapshot written to SQLite.
- **Replay:** reload any checkpoint and resume the run forward without re-running
  prior stages (the "Should" requirement).

### Human escalation
Repeated checkpoint failures past a threshold trip a `STOP` state. The harness
asks a human rather than letting the agent guess forever. Escalation is itself an
alarm with `recommended_action: "request human intervention"`.

---

## Tech stack

- **Python + FastAPI** — harness service and control loop
- **Worker interface** — OpenAI / Anthropic compatible, plus a scripted bot
- **Playwright** — browser NES emulator: frame capture + controller input injection
- **SQLite** — checkpoint + state persistence and replay
- **JSON** — alarm pipeline / structured logs

---

## Demo script (5 minutes)

1. Start a run. Agent (Claude) plays Mario, moving right. Checkpoints pass, green.
2. Mario hits a pipe. `FORWARD_PROGRESS` fails. `AGENT_STUCK (HIGH)` alarm fires.
3. Harness feeds the "try jump" hint back. **Same agent adapts**, jumps the pipe,
   checkpoints go green again. ← *the graded must, made visible.*
4. Trigger a guardrail live (agent tries an illegal combo) → blocked, reason shown.
5. Force repeated failure → escalation `STOP` → human-in-the-loop prompt.
6. **Bonus:** swap in a scripted recovery worker mid-run with zero harness change.
7. Replay the run from a mid-game checkpoint to prove persistence.

---

## Requirements coverage

| Requirement | How it's met |
|---|---|
| Must — four pillars, separate from worker | Guardrails / Checkpoints / Material / Alarms are distinct modules; worker is a swappable `decide()` |
| Must — behavior changes on feedback | Corrective-feedback loop on checkpoint failure (demo step 3) |
| Must — guardrails declared | Literal `GUARDRAILS` list |
| Must — checkpoints explicit pass/fail | `CheckpointResult.passed` |
| Must — structured alarms | `Alarm{type, severity, context, recommended_action}` |
| Must — real input from own work | Controller-input domain = engineer's actual field |
| Must — HARNESS.md | This architecture doc (see note below) |
| Should — swappable agent | `Worker` protocol, zero harness changes |
| Should — replay from checkpoint | SQLite snapshots + replay |
| Should — human escalation | `STOP` state on repeated failure |
| Bonus — swap second worker in demo | Recovery worker swap, demo step 6 |

> **Note:** the rubric names the deliverable `HARNESS.md`. This file is the
> architecture source of truth; before submission, copy or symlink it to
> `HARNESS.md` so the named deliverable exists.

---

## Open risks (tracked)

1. **Latency** — mitigated by the action-window model; if vision calls are still
   too slow, fall back to emulator RAM state (Mario x-pos, score) instead of
   pixels for both agent input and checkpoints.
2. **Runtime choice** — browser NES emulator chosen specifically because
   Playwright makes capture + input injection trivial. Do not fight a native
   emulator's input API under time pressure.
3. **Scope** — the four pillars + the feedback loop are the must. Replay and
   worker-swap are should/bonus; build them only after the core loop is green.
