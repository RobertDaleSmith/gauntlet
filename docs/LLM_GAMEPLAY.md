# Can an LLM actually play Tetris by driving a controller?

A short, honest experiment run inside Joypad Harness. The constraint throughout:
the agent **drives real controller buttons** (LEFT / RIGHT / ROTATE / DROP,
executed one press at a time) — never abstract "teleport this piece to column 5"
placements. The question was how much the *harness* has to help.

**TL;DR — perception was never the wall, and neither was strategy. Execution was.**
A pure LLM can read the board fine and knows *what* it wants, but it can't reliably
do the spatial + button-count arithmetic to land a shape in a specific gap, over
and over — even Opus. The moment the harness does that geometry and the model just
*judges* scored options, it plays a genuinely good game.

## The setup

The agent only ever decides; the harness owns everything else (guardrails,
checkpoints, alarms, material, recovery). Each Tetris piece is one decision. We
measured with **recovery OFF** so the numbers are pure LLM, with no heuristic
rescue. Model: Claude Haiku 4.5 unless noted; Opus 4.8 for the tier A/B.

## The arc

| Approach | Geometry / move-counting done by | Result |
|---|---|---|
| **Pure planner** — JSON board in, button plan out, no room to reason | the model | tops out ~24s, **0 lines** |
| **+ reasoning + 2-piece plan + per-row fill hints** (Haiku) | the model | tidy, hole-free, ~74s, **0 lines** |
| same, on **Opus** | the model | tidy, ~58s, **0 lines** (no better) |
| **Candidate-select** — harness enumerates every legal placement + its consequences; model picks the best `id` | **the harness** | **14 lines / 100s, low & stable, never tops out** |

Each pure-LLM lever improved *board management* (survival, flatness, zero holes)
but **none produced a single line clear**. Giving the model a reasoning scratchpad
and planning two pieces from one snapshot roughly tripled survival — yet still 0
lines. Upgrading Haiku → Opus did not help, which rules out "just needs a smarter
model."

You can watch it try: in the planner runs the model emits things like
`RIGHT ×9 + DROP` — it *knows* it wants the last column — but the exact shape never
quite fits the exact gap, so rows never complete and the stack slowly wins.

## Why candidate-select works

`workers/tetris_sim.py` mirrors the game's exact input semantics (CW rotation with
wall-kick offsets `[0,-1,1,-2,2]`, single-step moves, hard drop) and enumerates
every distinct legal placement for the current piece, each with:

- the **exact button sequence** that produces it, and
- its **consequences**: `lines`, `holes`, `max_h`, `bumpiness`.

The LLM is handed that list and only chooses the best `id`. We then drive the
chosen placement's real button sequence, one press at a time. The model does what
it's good at (judging trade-offs); the harness does what the model is bad at
(geometry and move arithmetic). That is the whole thesis of the project: a
well-designed harness makes the hard, error-prone mechanics invisible to the agent.

## Try it

Dashboard agents (LLM ones need `ANTHROPIC_API_KEY`):

- **Pick · Haiku — harness-scored** → the candidate-select agent. Plays well.
- **State / Plan / Vision · Haiku**, **Plan · Opus** → the pure-LLM experiments
  above (kept so you can see them stall).

Turn **Recovery OFF** to see an agent's true, unaided play.

## Honest caveats

- Numbers are single runs, not averaged — piece order is random, so survival/line
  counts vary run to run. The qualitative gap (0 lines pure vs. steady clears
  scored) is large and reproducible.
- "Plays well" means it clears lines and stays alive, not that it's optimal — the
  built-in heuristic worker (pure Python, El-Tetris) still plays stronger.

## Postscript: playing from video alone (no game state)

To confirm perception was never the bottleneck, we added a vision-only path: the
browser reconstructs the board **from the rendered pixels** — sample each grid
cell's center pixel for occupancy, isolate the falling piece as the floating
connected component — and sends *that* as the agent's perception. The referee
still grades on ground truth; the agent sees only what the camera could.

The **Heuristic · Vision (pixels only)** agent, playing purely from this
reconstruction, cleared **35 lines in 90s and kept the stack at height 1–5,
never topping out** — essentially as strong as it plays on ground truth. So a
clean grid render is trivially recoverable by CV, and "see the screen, drive the
controller" works end to end. The perception layer is shared, so the LLM agents
can run vision-only on the same reconstructed board.

### Capstone: the whole thesis in one agent

**Pick · Haiku · Vision** combines everything: it perceives the **pixel-
reconstructed board** (no game state), the harness enumerates the legal
placements, the **LLM judges** which is best, and we **drive the chosen
placement's buttons** one press at a time. Vision-only, recovery off, it cleared
**16 lines in 100s and held height 2–9, never topping out** — on par with the
ground-truth candidate-select. An LLM that sees the screen, reasons about scored
options, and drives the controller like a human, playing a real game. The harness
makes that possible by owning exactly the parts the model is bad at (precise
geometry and move arithmetic) and nothing more.
