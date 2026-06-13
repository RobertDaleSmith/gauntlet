"""Joypad Harness — the four pillars that govern a game-playing agent.

Each pillar is a separate, importable component:
  guardrails  — declared rules on controller input (validated before execution)
  checkpoints — explicit pass/fail evaluation of progress
  material    — capture/normalize game state, persist, replay
  alarms      — structured failures {type, severity, context, recommended_action}

The worker (the agent being governed) lives in the `workers` package and is
swappable — the harness never imports a concrete worker.
"""
