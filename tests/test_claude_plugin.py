# SPDX-License-Identifier: MIT
"""The Claude Code plugin in claude-plugin/: manifests parse, and the hook reports what check finds."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "claude-plugin"
HOOK = PLUGIN / "hooks" / "check.py"


def test_manifests():
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert [p["name"] for p in market["plugins"]] == [plugin["name"]] == ["slopdam"]
    assert (ROOT / market["plugins"][0]["source"]).resolve() == PLUGIN
    assert hooks["hooks"]["PostToolUse"][0]["matcher"] == "Write|Edit"
    assert (PLUGIN / "skills" / "clean-log-messages" / "SKILL.md").read_text(encoding="utf-8").startswith("---\nname: clean-log-messages\n")


def run_hook(tmp_path, path, cmd=None):
    event = {"hook_event_name": "PostToolUse", "tool_name": "Write", "cwd": str(tmp_path), "tool_input": {"file_path": str(path)}}
    env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(tmp_path / "data"), PYTHONPATH=str(ROOT / "src"))
    env["SLOPDAM_CMD"] = cmd if cmd is not None else f'"{sys.executable}" -c "import sys; from slopdam.cli import main; sys.exit(main())"'
    run = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True, text=True, env=env, timeout=60)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)["hookSpecificOutput"]["additionalContext"] if run.stdout.strip() else None


def test_hook_reports_findings(tmp_path):
    src = tmp_path / "app.py"
    src.write_text('import logging\nlogging.info("✅ Saved %d rows — done", 3)\nx = "not a log — here"\n', encoding="utf-8")
    said = run_hook(tmp_path, src)
    assert "2 AI-style trace(s)" in said and "line 2: dash.run" in said and "slopdam fix app.py" in said


def test_hook_is_quiet(tmp_path):
    clean = tmp_path / "ok.js"
    clean.write_text('console.log("plain message")\n', encoding="utf-8")
    notes = tmp_path / "notes.md"
    notes.write_text("print(\"a — b\")\n", encoding="utf-8")
    assert run_hook(tmp_path, clean) is None
    assert run_hook(tmp_path, notes) is None  # not a source file
    assert run_hook(tmp_path, tmp_path / "gone.py") is None


def test_hook_survives_a_broken_command(tmp_path):
    src = tmp_path / "app.py"
    src.write_text('import logging\nlogging.info("a — b")\n', encoding="utf-8")
    assert run_hook(tmp_path, src, cmd="slopdam-does-not-exist") is None
