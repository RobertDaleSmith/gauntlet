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

Gauntlet's domain is **AI game-playing agents**. The worker plays a game through
a controller interface; the harness governs it — validating controller inputs,
measuring real progress, carrying game state in and out, and raising structured
alarms when the agent gets stuck. When a checkpoint fails, the harness feeds
corrective feedback back into the agent, and the agent changes what it does.

Any worker that implements `decide(state) -> action` can be dropped in — Claude,
GPT, a local model, or a scripted bot — with no changes to the harness.

Demo target: an agent playing Super Mario in a browser NES emulator, with the
harness driving the controller, scoring progress, and escalating to a human (or
swapping in a recovery worker) when it can't move forward.

## Status

🚧 In planning. Architecture locked.

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — design source of truth
- [`Joypad_Harness_Architecture_Defense.pdf`](Joypad_Harness_Architecture_Defense.pdf) — 1-page planning doc
- [`24-hour Build Challenge.pdf`](24-hour%20Build%20Challenge.pdf) — challenge spec

## Deliverables

- [x] 1-page Harness Planning Document (Friday 11:30 PM)
- [ ] Project repo URL (Saturday 4:30 PM)
- [ ] Deployed Harness URL (Saturday 4:30 PM)
- [ ] `HARNESS.md` — architecture and design documentation (Saturday 4:30 PM)
- [ ] 5-minute demo video (Saturday 4:30 PM)
