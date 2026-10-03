"""
Supervisor helpers — deterministic parts only (syntax check, file I/O, human gate).
The AI work (creator, reviewer) is done by Claude Code agents lip-creator and lip-reviewer.
This module is imported by Claude Code when running the pipeline.
"""
from __future__ import annotations

import ast
import os
import shutil
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def syntax_check(files: list[dict]) -> list[str]:
    """Return list of syntax error strings for any .py files."""
    errors = []
    for f in files:
        if not f["path"].endswith(".py"):
            continue
        try:
            ast.parse(f["content"])
        except SyntaxError as e:
            errors.append(f"{f['path']}: line {e.lineno} — {e.msg}")
    return errors


def save_preview(files: list[dict]) -> str:
    """Save proposed files to agents/output/<timestamp>/ and return the path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(OUTPUT_DIR, ts)
    os.makedirs(out, exist_ok=True)
    for f in files:
        dest = os.path.join(out, f["path"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as fh:
            fh.write(f["content"])
    return out


def write_to_project(files: list[dict]):
    """Write approved files into the project directory, backing up originals as .bak."""
    for f in files:
        dest = os.path.join(_ROOT, f["path"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest):
            shutil.copy2(dest, dest + ".bak")
        with open(dest, "w") as fh:
            fh.write(f["content"])
        print(f"  ✓  {f['path']}  (backup → {f['path']}.bak)")


def human_gate(feature_spec: str, result: dict, review: dict, out_dir: str) -> str:
    """Print summary and prompt for A/R/Q. Returns 'approve', 'reject', or 'quit'."""
    files = result.get("files", [])
    w = 62
    bar = "━" * w

    print(f"\n{bar}")
    print("  READY FOR YOUR REVIEW")
    print(bar)
    print(f"  Feature : {feature_spec}")
    print(f"  Files   : {', '.join(f['path'] for f in files)}")
    print(f"  Score   : {review['score']:.1f}/10  [{review['verdict'].upper()}]")

    issues = review.get("issues", [])
    if issues:
        print(f"  Issues  : {len(issues)}")
        for issue in issues:
            print(f"    • {issue}")
    else:
        print("  Issues  : none")

    print(f"\n  {result.get('explanation', '')}")
    print(f"\n  Preview : {out_dir}")
    print(bar)
    print("  [A]pprove — write files to project")
    print("  [R]eject  — loop creator again with your notes")
    print("  [Q]uit    — discard and exit")
    print(bar)

    while True:
        raw = input("  Your choice (A/R/Q): ").strip().lower()
        if raw in ("a", "approve"):
            return "approve"
        if raw in ("r", "reject"):
            return "reject"
        if raw in ("q", "quit"):
            return "quit"
        print("  Enter A, R, or Q")
