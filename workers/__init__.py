"""Swappable workers. Each implements decide(state, feedback) -> Action.

The harness holds a Worker; it never imports a concrete one. Drop in Claude,
GPT, or a scripted bot with no harness changes.
"""
