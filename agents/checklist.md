# Review Checklist

Used by the Reviewer agent to score proposed code changes (0–10).

## Items

1. **No syntax errors** — all Python files must parse cleanly (`ast.parse`)
2. **Interface compatibility** — `PhoneDetector`, `Phase`, `LockInPoliceApp` APIs unchanged
3. **Pattern consistency** — `rumps` for menubar, `subprocess` for popups, OpenCV DNN for detection
4. **Lightweight** — no PyTorch, no new servers, no heavy background daemons
5. **Edge cases** — camera unavailable, file not found, network errors wrapped in try/except
6. **No hardcoded paths** — uses `APP_DIR` / `os.path.join` patterns throughout
7. **Code style** — PEP 8, type hints consistent with existing files
8. **Security** — no `shell=True` with user input, no `eval`/`exec` on untrusted data

## Scoring

| Score  | Verdict      | Action                              |
|--------|--------------|-------------------------------------|
| 8.5–10 | `pass`       | Surface to human for approval       |
| 6–8.4  | `needs_work` | Auto-loop: send feedback to creator |
| 0–5.9  | `fail`       | Auto-loop: send feedback to creator |
