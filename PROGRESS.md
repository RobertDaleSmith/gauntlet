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
- [x] **Tetris checkpoints** — `StackHeightSafe`, `NotGameOver`, `NoNewHoles`, `LinesMilestone`;
      Mario checkpoints/adapter retired; `FakeTetrisAdapter` sim; loop generalized (game-agnostic
      feedback + escalation + game-over); workers + state pivoted to Tetris; 21 tests green
- [x] **WS protocol** in `server/app.py` — observe/act/set_worker/reset; `HarnessSession` runs the
      pillars; TestClient protocol tests. Verified live end-to-end in the browser.
- [x] **Dashboard rendering** — live worker, agent intent, checkpoints (green/red), alarms, guardrails;
      Start/Pause, Reset, worker-swap controls. Verified via screenshot (all pillars firing).
- [x] **Vision agent** — `ClaudeWorker.set_frame()` + image content block (agent sees pixels);
      session forwards the frame; mock-tested. Live run just needs `ANTHROPIC_API_KEY`.
- [x] **Heuristic worker** — real Tetris placement AI (El-Tetris weights, reads board from state.raw),
      plays well (low/flat, no holes); scripted stays "reckless" to demo escalation. Live worker-swap
      verified (scripted→heuristic). + tests
- [x] **HARNESS.md** — as-built architecture deliverable (replaces ARCHITECTURE.md); README updated.
      (planning PDF left as the Friday submission record; HARNESS.md is canonical for current design)
- [x] **Replay** — `/api/runs/{id}` endpoint + dashboard playback of persisted board snapshots; verified
- [x] **Human escalation UI** — STOP banner surfaces `ESCALATE`/`GAME_OVER`; Reset/worker-swap to recover
- [x] **Live worker swap** (bonus) — swap scripted ↔ heuristic ↔ claude mid-run; verified live
- [x] **Run script** — `run.sh` (one-command serve)
- [ ] **Deploy config** — Dockerfile + platform config so the user can publish the live URL
- [ ] **Demo video** — 5-min walkthrough (manual; needs the user)

## Ralph loop prompt (copy into the loop)
```
Read ARCHITECTURE.md and PROGRESS.md. Pick the FIRST unchecked [ ] item in
"To build". Implement just that item, matching the existing module style. Add or
extend a test for it. Run: .venv/bin/python -m pytest -q
If green: check the box in PROGRESS.md, then commit with a one-line message.
If red: fix until green before committing. Do exactly one item, then stop.
Never commit with failing tests. Do not commit a copyrighted ROM.
```
