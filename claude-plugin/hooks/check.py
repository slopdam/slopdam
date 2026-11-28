# SPDX-License-Identifier: MIT
"""PostToolUse hook: run `slopdam check` on the file Claude just wrote or edited.

Findings go back to Claude as additional context next to the tool result; nothing is blocked
and the file is not changed. The project's own slopdam settings (slopdam.toml or
[tool.slopdam] in pyproject.toml) apply, as they do on the command line.

slopdam is taken from, in order: $SLOPDAM_CMD, `slopdam` on PATH, this Python's slopdam
package, `uvx --from slopdam slopdam`. If none is there, Claude is told once per project.
Standard library only, Python 3.9 or later.
"""
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys

# The extensions `slopdam check` scans in a directory; other files are skipped here too.
SOURCE_EXTS = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rb", ".php", ".rs", ".swift"}
MAX_LISTED = 20


def command():
    if os.environ.get("SLOPDAM_CMD"):
        return shlex.split(os.environ["SLOPDAM_CMD"])
    if shutil.which("slopdam"):
        return ["slopdam"]
    try:
        import slopdam  # noqa: F401
        return [sys.executable, "-c", "import sys; from slopdam.cli import main; sys.exit(main())"]
    except ImportError:
        pass
    if shutil.which("uvx"):
        return ["uvx", "--from", "slopdam", "slopdam"]
    return None


def say(text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}))


def missing_once(project):
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if data:
        marker = os.path.join(data, "told-missing", hashlib.sha1(project.encode()).hexdigest()[:16])
        if os.path.exists(marker):
            return
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        open(marker, "w").close()
    say("The slopdam plugin could not find slopdam, so log messages are not being checked. "
        "Ask the user to run `pip install slopdam` (or install uv), or set SLOPDAM_CMD.")


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    path = (event.get("tool_input") or {}).get("file_path") or ""
    if os.path.splitext(path)[1] not in SOURCE_EXTS or not os.path.isfile(path):
        return 0
    cmd = command()
    if cmd is None:
        missing_once(event.get("cwd") or os.getcwd())
        return 0
    try:
        run = subprocess.run(cmd + ["check", "--format", "json", path], capture_output=True, text=True,
                             timeout=50, cwd=event.get("cwd") or None)
        found = json.loads(run.stdout or "[]")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0  # a broken check must never get in the way of the edit
    if not found:
        return 0
    name = os.path.relpath(path, event.get("cwd") or os.getcwd())
    lines = []
    for f in found[:MAX_LISTED]:
        fix = "report only" if f["fix"] is None else f"replace with {f['fix']!r}"
        lines.append(f"- line {f['line']}: {f['rule']} {f['text']!r}, {fix}")
    if len(found) > MAX_LISTED:
        lines.append(f"- and {len(found) - MAX_LISTED} more")
    how = f" `slopdam fix {name}` can rewrite them." if path.endswith(".py") else ""
    say(f"slopdam found {len(found)} AI-style trace(s) in log messages in {name}:\n" + "\n".join(lines)
        + f"\nRewrite those messages in plain text, keeping their meaning.{how} "
        "Leave a line alone if the character is intended, and say why.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
