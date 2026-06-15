# Plan: governing a vision-only agent on real NES Tetris

The endgame of the LLM-gameplay arc (see [LLM_GAMEPLAY.md](LLM_GAMEPLAY.md)):
take everything we proved on the toy game and point the harness at the **real
1989 NES Tetris**, with the agent perceiving **pixels only** (no emulator RAM)
and driving a **controller** like a human. This is the architecture, the genuinely
hard parts, and a staged plan. No code yet — alignment first.

## Status / decisions

- **Emulator: nes-rust (not jsnes).** jsnes renders NES Tetris *menus* but not
  *gameplay* — the playfield background goes black, leaving only the sprite
  pieces (reproduced in headless with both a Tengen and a Nintendo dump, and
  confirmed by the user on raw jsnes.org). jsnes is too inaccurate for this
  timing-sensitive game. Swapped to **`nes-rust`** (accurate Rust→WASM, MIT) which
  renders gameplay correctly and has the exact API we need: `step_frame()`,
  `update_pixels()` (RGBA framebuffer), `press_button()/release_button()`.
- **ROM: Nintendo *Tetris (USA)*** (mapper 1, loads natively — no header hacks).
- **M1 done** (emulator in the harness, ROM boots, controllable) and **M2 done**
  (vision-only board reconstruction; Nintendo well calibrated to x0=96, y0=48,
  8px cells, 10×20). Both on nes-rust. Next: **M3**.

## Goal & constraints

- **World:** real NES Tetris running in `jsnes` (MIT, pure-JS NES emulator) in the
  browser, exactly where our toy game lived. Renders a 256×240 framebuffer to a
  canvas; takes the 8 NES buttons.
- **Vision only, no memory state.** The agent — *and the referee* — read only the
  rendered pixels. We never read emulator RAM. Stronger and purer than the toy,
  where the referee had ground truth.
- **Drive the controller like a human.** Logical actions become real NES inputs
  (D-pad + A/B + Down + Start), fed frame-accurately.
- **Ship no ROM.** NES Tetris is copyrighted. The user supplies a legally-obtained
  `.nes` via a local file-picker; `*.nes` is gitignored; nothing is committed or
  uploaded.

## What transfers (most of the project)

- **The harness pillars** (guardrails, checkpoints, alarms, material) and the
  **dual-worker recovery**, **coach directives**, and **agent log** are
  board-agnostic — they govern whatever adapter sits underneath.
- **The candidate-select worker** is the proven path: the harness enumerates legal
  placements with consequences (+ now positions), the LLM/heuristic *judges*. The
  judging code is unchanged; only the *enumerator* and *adapter* are NES-specific.
- **The CV idea**: the toy proved an agent can play from a reconstructed grid.
  NES Tetris is also a fixed grid of solid cells — cleaner than the real world.

## What's new / genuinely hard

### 1. NES mechanics ≠ the toy game
- **No hard drop.** You *hold Down* to soft-drop; the piece also falls under
  gravity and **locks** when it can't descend (after a short lock delay).
- **Rotation = Nintendo Rotation System (NRS).** `A` = clockwise, `B` =
  counter-clockwise, about a fixed center, **no wall kicks** — a rotation that
  would collide simply fails. `O` doesn't rotate; `I`/`S`/`Z` have 2 states;
  `T`/`J`/`L` have 4.
- **DAS (Delayed Auto-Shift).** Tapping Left/Right moves one cell; holding waits
  ~16 frames then auto-shifts every ~6. Precise column targeting means either
  timed taps or a charged DAS to the wall.
- **Gravity by level.** ~48 frames/cell at level 0, accelerating to 1–3 at the
  kill screen. **Recommendation: play level 0–8** so there's time to position;
  the enumerator/executor must still respect gravity so a piece doesn't fall past
  its target mid-input.

### 2. Real-time vs. our pace — solved by frame-stepping
An LLM is ~1s/decision; the NES runs 60fps. We **drive the emulator's clock**:
advance frames under harness control, read the frame, decide a full frame-timed
input sequence for the current piece, feed it while stepping, run until the piece
locks, then repeat. We own the clock (legitimate — it's how AI-plays-NES setups
work). The cost: inputs must be scheduled on the right frames (DAS charge, gravity
ticks), not just "a list of buttons."

### 3. Referee from pixels (no RAM)
- **Board height / holes:** computed from the reconstructed locked board.
- **Line clears:** detect the row-clear flash animation, or diff the board across
  piece-locks (stack drop), or OCR the LINES counter.
- **Score / level:** OCR fixed-position digits (NES font is a fixed bitmap) if we
  want them for checkpoints; otherwise derive progress from lines.
- **Game over:** template-match the game-over "curtain"/screen.

### 4. Perception specifics (calibrate in M2 against a real frame)
- **Playfield:** 10×20 grid of 8×8-px cells at a fixed screen offset (~x∈[96,176),
  y∈[40,200) — exact values TBD). Occupancy = cell-center pixel is non-black.
  **Block colors change per level**, so detect filled-vs-empty by "not background,"
  never by specific color.
- **Current piece:** the floating connected component above the stack (same trick
  as the toy), giving its cells → position + orientation.
- **Next piece:** NES renders a **next-piece preview box** (fixed region) — so
  vision-only finally gets lookahead for free.

### 5. Game flow from vision
Title → game-type/level select → in-game → line-clear pauses → game over. Each
screen is detected by pixel template-match and advanced with scripted inputs
(navigate the level menu, press Start). Bounded but fiddly.

## Architecture (mirrors the current browser-driven harness)

```
 jsnes (browser)                          harness (server, Python)
 ─────────────────                        ────────────────────────
 step frames ──▶ read 256×240 frame
   │            CV: board + current + next  ──(observe: vision)──▶  referee grades
   │                                                                 (height/holes/
   │                                                                  lines from pixels)
   │                                                                 enumerate NES
   │                                                                 placements (NRS +
   │                                                                 frame-timed plans)
   │                                                                 worker judges (pick)
   │            ◀──(act: frame-timed input plan)──────────────────  + coach/log/alarms
   ▼
 execute the input plan across frames (buttonDown/Up + nes.frame())
 run until the piece locks ──▶ next decision
```

- **Browser** owns jsnes, the frame-stepping loop, CV reconstruction, and executes
  the frame-timed input plan. It sends `observe` (the vision board/current/next)
  and receives an `act` (the input plan) — same shape as today, richer payload.
- **Server** runs the pillars (referee on the CV board, enumeration, worker pick,
  coach, alarms). The **candidate-select worker is reused**; a new
  `workers/nes_sim.py` models NRS rotation, DAS-aware movement, gravity, and
  emits **frame-timed** input plans (the toy `tetris_sim` emitted plain button
  lists — the NES version emits schedules).

## Milestones (build as a separate `nes.html` / module; the toy demo stays intact)

1. **Emulator integration.** `nes.html` loads a user ROM via file-picker, renders
   the framebuffer to a 2× canvas, maps keyboard → NES buttons, and can navigate
   the menus to start a game. **Done when:** you can play NES Tetris by keyboard
   inside the harness page.
2. **Perception.** Calibrate the playfield / next / HUD pixel regions; reconstruct
   board occupancy + current piece + next piece (+ optional lines/level OCR), with
   a live overlay to verify. **Done when:** the reconstruction visibly matches the
   screen across many frames and levels.
3. **Play it.** Frame-stepping harness loop + `nes_sim` enumerator + candidate-
   select; the **heuristic** plays from vision on level 0. **Done when:** it clears
   lines and survives, pixels-only.
4. **Full harness.** Referee-from-pixels (height/holes/lines/game-over), alarms,
   recovery, coach + agent log wired to the NES agent; the **LLM** candidate-select
   plays. **Done when:** the four pillars govern the NES agent on the dashboard.

## ROM handling

- `*.nes` and `roms/` are gitignored; the repo bundles no ROM.
- Load via browser file-picker (`FileReader` → `jsnes.loadROM(binary)`), in-memory
  only — no server upload, no persistence to the repo.

## Open decisions (resolve as we build)

- **Level:** start at 0 for maximum input headroom; expose a level choice later.
- **Movement:** timed taps (simple at low gravity) vs. charged DAS (faster, needed
  at high levels). Start with taps.
- **Line detection:** animation-diff vs. LINES-counter OCR. Start with board-diff.
- **Scope of "human":** we frame-step rather than hit 60fps real-time; perception
  is pure vision and input is a real controller stream — the spirit is preserved.

## Risks

| Risk | Mitigation |
|---|---|
| Frame-accurate input (DAS/gravity) is finicky | Play level 0, use timed taps, verify each placement lands where enumerated; treat a mis-land as a checkpoint failure → re-perceive and correct |
| NRS rotation modeled wrong → wrong candidates | Unit-test `nes_sim` against known piece/orientation cases before wiring |
| Perception drift across level palettes | Occupancy by "not background," not color; calibrate regions once |
| Menu/flow detection brittle | Template-match a few fixed screens; scripted, retriable |
| ROM legality | User-supplied, gitignored, never committed/uploaded |
