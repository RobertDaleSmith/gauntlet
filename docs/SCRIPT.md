# Joypad Harness Demo Script

## 1. Intro

Hey, I'm Robert, founder of Joypad AI, a startup building AI-powered companion game controllers.

One of the problems I've become obsessed with is what happens when an AI agent is actually controlling something.

Not generating text. Not answering questions.

Actually taking actions.

The reality is these agents make mistakes. They get stuck, repeat bad decisions, and often have no idea they're failing.

So for this challenge I built **Joypad Harness**.

Joypad Harness is a runtime system that sits between an AI agent and a game. The agent decides what to do. The harness decides whether those actions are valid, whether they're making progress, and what happens when things go wrong.

Let me show you.

---

## 2. The Four Pillars

On the left is the worker agent.

On the right is Joypad Harness.

The worker only has one responsibility: choose an action.

Everything else lives inside the harness.

The harness handles game state, enforces guardrails, evaluates checkpoints, and raises structured alarms.

Right now the agent is playing clean, so the checkpoints are passing and the harness is happy.

The key idea is that the harness is completely separate from the worker. I can swap agents without changing the harness itself.

---

## 3. Failure and Human Escalation

Now let's switch to a deliberately terrible agent.

This is where the harness starts earning its keep.

You can see the board getting worse. Checkpoints begin failing. The harness feeds corrective feedback back into the worker and keeps evaluating whether it's making meaningful progress.

Eventually it decides the worker is no longer recovering.

At that point it stops the run and escalates to a human.

The goal isn't to let the AI fail forever.

The goal is to recognize when it's failing and know when to stop.

---

## 4. Recovery Worker

Stopping is useful. Recovery is the next layer.

This time recovery is enabled.

When the primary worker starts failing, the harness doesn't give up right away. It automatically swaps in a backup worker to try to save the run.

And the harness doesn't care what that worker is.

It could be a language model.

A heuristic bot.

A future game-playing model.

As long as it implements the interface, the harness can manage it.

This board is already too far gone to rescue, so when the backup can't recover it either, the harness escalates to a human.

Swap first. Escalate only as a last resort. Layered defense, not a single off switch.

---

## 5. Real Language Model

And here's my favorite part.

This worker is an actual language model.

It's reading the board, deciding where pieces should go, and pressing buttons through the exact same interface as every other worker.

And honestly?

It's not a very good Tetris player.

But that's exactly why I built this.

At Joypad we're interested in AI that can interact with games in the real world.

The challenge isn't building a perfect agent.

The challenge is building systems that remain reliable when the agent isn't.

That's what the harness is for.

---

## 6. Replay and Closing

Every decision, checkpoint result, alarm, worker swap, and recovery action is recorded.

That means I can replay any run and understand exactly what happened and why.

That's Joypad Harness.

The worker generates actions.

The harness governs outcomes.

Thank you for your time, and for the glimpse into Gauntlet AI.
