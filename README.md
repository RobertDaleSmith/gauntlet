# Gauntlet

A harness — a framework that an AI agent lives inside.

Built for a 24-hour build challenge. The harness provides four pillars, each a
distinct component separate from the worker agent:

- **Guardrails** — declared constraints on agent behavior
- **Checkpoints** — explicit pass/fail evaluation of agent outputs
- **Material handling** — clean interfaces for passing material in and out
- **Alarms** — structured alerts (type, context, severity, recommended action)

> Agents focus on tasks. Harnesses focus on constraints. A well-designed
> harness makes constraint-handling invisible to the agent.

## The Joypad Harness

Gauntlet governs an **AI game-playing agent that plays like a human** — it sees
the rendered screen (pixels) and presses controller buttons. The harness decides
which inputs are legal, measures real progress, carries game state in and out,
and raises structured alarms. When a checkpoint fails it feeds corrective
feedback back to the agent; on repeated failure it stops and asks a human.

Any worker implementing `decide(state, feedback) -> action` drops in with no
harness changes. Three ship today: **scripted** (reckless baseline — demos
escalation), **heuristic** (a real Tetris AI), and **claude** (vision — sees the
frame as an image). Swap them live from the dashboard.

Demo domain: **Tetris** (a custom browser game), chosen because its forgiving
cadence lets a vision-LLM actually play by looking at the screen.

## Run it

```bash
uv venv .venv && uv pip install --python .venv -r requirements.txt
.venv/bin/python -m pytest -q                 # 30+ tests (the verification hook)
./run.sh                                       # serve at http://127.0.0.1:8000
```

Open the URL, press **Start**, and watch the four pillars fire next to the game.
The Claude (vision) worker needs `ANTHROPIC_API_KEY`; scripted/heuristic don't.

## Status

🚧 Building. Core harness + live dashboard working; agent plays Tetris under the
four pillars with live worker-swap.

- [`HARNESS.md`](HARNESS.md) — architecture & design (the as-built system)
- [`PROGRESS.md`](PROGRESS.md) — build checklist
- [`docs/Harness_Planning.pdf`](docs/Harness_Planning.pdf) — 1-page planning doc (source: [`docs/Harness_Planning.md`](docs/Harness_Planning.md))
- [`docs/24-hour Build Challenge.pdf`](docs/24-hour%20Build%20Challenge.pdf) — challenge spec

## Deliverables

- [x] 1-page Harness Planning Document (Friday 11:30 PM)
- [x] Project repo URL (Saturday 4:30 PM)
- [ ] Deployed Harness URL (Saturday 4:30 PM)
- [x] `HARNESS.md` — architecture and design documentation (Saturday 4:30 PM)
- [ ] 5-minute demo video (Saturday 4:30 PM)
