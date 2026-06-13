# Build Progress — Gauntlet Joypad Harness

Ralph-loop worklist. Each iteration: read `ARCHITECTURE.md` + this file → build the
**next unchecked item** → run the verification hook → if green, check the box and
commit → if red, fix. Keep changes scoped to one item per iteration.

**Verification hook (must stay green):**
```
.venv/bin/python -m pytest -q
```

Legend: `[x]` built & tested · `[ ]` not built yet.

## Scaffold (done)
- [x] Package layout — `harness/`, `workers/`, `server/`
- [x] Shared types — `GameState`, `Action` (`harness/types.py`)
- [x] 🛡️ Guardrails — `AllowedButtons`, `MaxHoldFrames`, `NoImpossibleCombos`, `GuardrailSet`
- [x] ✅ Checkpoints — `ForwardProgress`, `StillAlive`, `ScoreNonDecreasing`
- [x] 🚨 Alarms — `Alarm` (type/severity/context/recommended_action) + `AlarmBus`
- [x] 📦 Material — SQLite persist, `replay`, `load_state`, `normalize`
- [x] Control loop — feedback on checkpoint fail + escalation to `STOP` (`harness/loop.py`)
- [x] `FakeGameAdapter` — simulates the stuck-at-pipe hero beat for tests
- [x] `ScriptedWorker` — rule-based, adapts to "try jump" feedback
- [x] Smoke tests — 15 green (`tests/`)
- [x] FastAPI + dashboard skeleton (`server/app.py`, `server/static/index.html`)

## To build (in order)
- [x] **RateLimit guardrail** — min-hold lower bound in `DEFAULT_GUARDRAILS` + test
- [x] **More checkpoints** — `LevelAdvanced` (default), `ScoreMilestone` (gate); `level` field; tests
- [x] **ClaudeWorker.decide** — Haiku 4.5, structured-output `{buttons, hold_frames}`,
      feedback in prompt, injectable client, mock-based test
- [x] **WebSocketGameAdapter** — `GameAdapter` over a `Transport`; drop-in (loop-compat test)
- [x] **Tetris game** (custom, `server/static/tetris.js`) — canvas render (the video the agent
      watches), controller input, ground-truth `state()` (board/score/lines/level/stack_height/holes);
      human-playable. Replaces the ROM/jsnes path — no legal issue, we own the state API.
- [ ] **Tetris checkpoints** — `LINES_CLEARED`, `STACK_HEIGHT_SAFE`, `NOT_GAME_OVER`, `NO_NEW_HOLES`;
      retire the Mario `ForwardProgress`/`StillAlive` defaults + update `FakeGameAdapter` to a Tetris sim
- [ ] **WS protocol** in `server/app.py` — browser sends the rendered FRAME (base64) + ground-truth
      state; harness sends controller actions; stream intent/checkpoint/alarm/guardrail to the dashboard
- [ ] **Vision agent** — `ClaudeWorker` takes the frame as image input (agent sees pixels, like a
      human); the harness keeps ground-truth state only for grading, never feeds it to the agent
- [ ] **Dashboard rendering** — live worker, agent intent, checkpoints (green/red), alarms, guardrail blocks
- [ ] **Update docs** — `ARCHITECTURE.md` + planning doc to the Tetris + vision-first design
- [ ] **Replay** — endpoint + UI to scrub a finished run from SQLite (`load_state` / `replay`)
- [ ] **Human escalation UI** — `STOP` state surfaces a prompt to the operator
- [ ] **Live worker swap** (bonus) — control to swap scripted ↔ claude mid-run
- [ ] **HARNESS.md** — expand `ARCHITECTURE.md` into the named Saturday deliverable
- [ ] **Run scripts / deploy** — Makefile or run.sh; deploy config for the live URL

## Ralph loop prompt (copy into the loop)
```
Read ARCHITECTURE.md and PROGRESS.md. Pick the FIRST unchecked [ ] item in
"To build". Implement just that item, matching the existing module style. Add or
extend a test for it. Run: .venv/bin/python -m pytest -q
If green: check the box in PROGRESS.md, then commit with a one-line message.
If red: fix until green before committing. Do exactly one item, then stop.
Never commit with failing tests. Do not commit a copyrighted ROM.
```
