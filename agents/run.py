"""
Lock-In Police — Agent Pipeline
─────────────────────────────────
Don't run this directly. Instead, ask Claude Code to run the pipeline:

  "run the agent pipeline: add a timer sound when pomodoro ends"

Claude Code acts as the supervisor, spawning lip-creator and lip-reviewer agents
from .claude/agents/. No API key needed — it runs through your existing session.

This file documents the flow for reference:

  1. lip-creator reads the codebase and proposes code changes (JSON)
  2. supervisor.syntax_check() catches Python syntax errors instantly
  3. lip-reviewer scores the changes against checklist.md (0–10)
  4. If score < 8.5 → feedback loops back to creator (max 3 iterations)
  5. If score ≥ 8.5 → supervisor.human_gate() asks you to A/R/Q
  6. Approve → supervisor.write_to_project() writes files + .bak backups
"""
