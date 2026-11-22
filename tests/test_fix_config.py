# SPDX-License-Identifier: MIT
import ast
import json
import textwrap

import pytest

from slopdam import Sanitizer
from slopdam.cli import main
from slopdam.config import Config, ConfigError, _parse_toml_subset, find_config, load_config
from slopdam.fixer import fix_source

READER, DEV = Sanitizer("reader"), Sanitizer("dev")

SAMPLE = textwrap.dedent('''\
    """Module doc — keep."""
    import logging
    logger = logging.getLogger(__name__)
    name = "x"


    def run(n):
        """Doc ✅ keep."""
        logger.info("✅ 저장 완료 ㅡ %s건 처리!", n)
        logger.warning(f"{name} 동기화 — {n}건 🚀")
        print("“인용” 테스트…")
        print(r"“raw”")
        title = "— 로그 아님"
        logger.error("❌ 실패 — 재시도")  # slopdam: ignore[emoji]
        logger.info("ok — fine")  # slopdam: ignore
        return b"\\xe2", title
''')


def strings_of(source):
    return [n.value for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


# --- fix -------------------------------------------------------------------------------

def test_fix_reader():
    new, edits = fix_source(SAMPLE, READER)
    assert 'logger.info("저장 완료: %s건 처리.", n)' in new
    assert 'logger.warning(f"{name} 동기화: {n}건")' in new
    assert 'print("\\"인용\\" 테스트...")' in new
    assert ast.literal_eval('"\\"인용\\" 테스트..."') == '"인용" 테스트...'
    assert all(e.after is not None for e in edits if e.rule_id != "tone.chatty")


def test_fix_dev_keeps_info():
    new, _ = fix_source(SAMPLE, DEV)
    assert 'logger.info("[OK] 저장 완료 - %s건 처리!", n)' in new
    assert 'logger.warning(f"{name} 동기화 - {n}건")' in new


@pytest.mark.parametrize("kept", ['"""Module doc — keep."""', '"""Doc ✅ keep."""', 'r"“raw”"', '"— 로그 아님"',
                                  '"ok — fine"', 'b"\\xe2"', "❌ 실패"])
def test_fix_leaves_untouched(kept):
    new, _ = fix_source(SAMPLE, READER)
    assert kept in new


def test_fix_honours_rule_ignore():
    new, _ = fix_source(SAMPLE, READER)
    assert 'logger.error("❌ 실패: 재시도")' in new  # emoji kept, dash fixed


def test_fix_is_idempotent_and_compiles():
    for s in (READER, DEV):
        once, _ = fix_source(SAMPLE, s)
        twice, edits = fix_source(once, s)
        assert once == twice
        assert [e for e in edits if e.after is not None] == []
        compile(once, "x", "exec")


def test_fix_scope_strings_includes_plain_strings_but_not_docstrings():
    new, _ = fix_source(SAMPLE, READER, scope="strings")
    assert 'title = "- 로그 아님"' in new  # a leading dash reads as a list marker, as in clean()
    assert '"""Doc ✅ keep."""' in new


def test_fix_keeps_format_placeholders_and_escapes():
    src = 'logger.info("완료 ㅡ %(count)d건 — {0} 처리\\n")\n'
    new, _ = fix_source(src, READER)
    assert strings_of(new) == ["완료: %(count)d건: {0} 처리\n"]


def test_fix_multiline_implicit_concatenation():
    src = 'logger.info(\n    "✅ 저장"\n    " 완료 ㅡ 다음"\n)\n'
    new, _ = fix_source(src, DEV)
    assert strings_of(new) == ["[OK] 저장 완료 - 다음"]


def test_fix_rejects_unparsable_source():
    with pytest.raises(SyntaxError):
        fix_source("logger.info(", READER)


# --- config ----------------------------------------------------------------------------

TOML = textwrap.dedent('''\
    # written by the policy screen
    profile = "dev"
    level = "strong"
    disable = ["emoji.status", "md"]

    [dash]
    inline = "comma"

    [lint]
    scope = "strings"
    exclude = [
      "tests/**",   # fixtures keep their symbols
    ]

    [github]
    mode = "warn"
    suggestions = true
''')


def test_subset_parser_reads_policy_file():
    data = _parse_toml_subset(TOML)
    assert data["profile"] == "dev" and data["disable"] == ["emoji.status", "md"]
    assert data["lint"] == {"scope": "strings", "exclude": ["tests/**"]}
    assert data["github"] == {"mode": "warn", "suggestions": True}


def test_load_slopdam_toml(tmp_path):
    (tmp_path / "slopdam.toml").write_text(TOML, encoding="utf-8")
    cfg = load_config(start=str(tmp_path))
    assert (cfg.profile, cfg.level, cfg.dash_inline, cfg.scope) == ("dev", "strong", "comma", "strings")
    assert cfg.disable == ("emoji.status", "md") and cfg.exclude == ("tests/**",)
    assert not cfg.selects(str(tmp_path / "tests" / "a.py")) and cfg.selects(str(tmp_path / "src" / "a.py"))


def test_load_pyproject_tool_table(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n\n[tool.slopdam]\nprofile = "dev"\n', encoding="utf-8")
    sub = tmp_path / "pkg"
    sub.mkdir()
    assert find_config(str(sub)) == tmp_path / "pyproject.toml"
    assert load_config(start=str(sub)).profile == "dev"


def test_pyproject_without_table_is_ignored(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    (tmp_path / ".git").mkdir()
    assert load_config(start=str(tmp_path)) == Config()


def test_invalid_value_is_an_error(tmp_path):
    (tmp_path / "slopdam.toml").write_text('profile = "robot"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(start=str(tmp_path))


# --- CLI -------------------------------------------------------------------------------

def test_cli_config_and_override(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("SLOPDAM_CONFIG", raising=False)
    (tmp_path / "slopdam.toml").write_text('profile = "dev"\n', encoding="utf-8")
    (tmp_path / "a.py").write_text('log.info("완료 ㅡ 다음")\n', encoding="utf-8")
    assert main(["check", "--format", "json", str(tmp_path)]) == 1
    assert json.loads(capsys.readouterr().out)[0]["fix"] == " - "      # from slopdam.toml
    assert main(["--profile", "reader", "check", "--format", "json", str(tmp_path)]) == 1
    assert json.loads(capsys.readouterr().out)[0]["fix"] == ": "       # option wins


def test_cli_config_error_exit_code(tmp_path, capsys):
    (tmp_path / "slopdam.toml").write_text('level = "loud"\n', encoding="utf-8")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 2
    assert "level must be one of" in capsys.readouterr().err


def test_cli_exclude(tmp_path):
    (tmp_path / "slopdam.toml").write_text('[lint]\nexclude = ["gen/**"]\n', encoding="utf-8")
    (tmp_path / "gen").mkdir()
    (tmp_path / "gen" / "a.py").write_text('log.info("✅ x")\n', encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 0


def test_cli_fix_diff_then_write(tmp_path, capsys):
    target = tmp_path / "a.py"
    target.write_text('import logging\nlogging.info("✅ 완료 ㅡ 다음")\n', encoding="utf-8")
    assert main(["fix", "--diff", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert '+logging.info("완료: 다음")' in out
    assert "✅" in target.read_text(encoding="utf-8")                   # --diff does not write
    assert main(["fix", str(tmp_path)]) == 0
    assert target.read_text(encoding="utf-8") == 'import logging\nlogging.info("완료: 다음")\n'
    assert main(["fix", "--diff", str(tmp_path)]) == 0                 # nothing left


def test_cli_check_scope_strings_uses_literals(tmp_path, capsys):
    (tmp_path / "a.py").write_text('MSG = "완료 ㅡ 다음"  # not a log call\n', encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 0
    assert main(["check", "--scope", "strings", "--format", "json", str(tmp_path)]) == 1
    hit = json.loads(capsys.readouterr().out)[-1]
    assert (hit["line"], hit["col"], hit["rule"]) == (1, 10, "dash.run")  # the span starts at the space before the dash
