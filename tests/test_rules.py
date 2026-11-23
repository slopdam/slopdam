# SPDX-License-Identifier: MIT
import io
import json
import logging

import pytest

from slopdam import PlainFilter, PlainFormatter, Sanitizer, clean
from slopdam.cli import main

READER, DEV = Sanitizer("reader"), Sanitizer("dev")


# (input, reader, dev)
DASH_CASES = [
    ("완료 ㅡ 다음", "완료: 다음", "완료 - 다음"),
    ("완료ㅡ다음", "완료: 다음", "완료 - 다음"),
    ("완료 —다음", "완료: 다음", "완료 - 다음"),
    ("완료 ￚ 다음", "완료: 다음", "완료 - 다음"),       # halfwidth ㅡ
    ("완료 ᅳ 다음", "완료: 다음", "완료 - 다음"),       # conjoining ㅡ (NFKC form of ㅡ)
    ("완료 ― 다음", "완료: 다음", "완료 - 다음"),
    ("완료 ﹘ 다음", "완료: 다음", "완료 - 다음"),
    ("ㅡㅡ 진짜", "진짜", "진짜"),
    ("ㅡㅡㅡㅡㅡ", "", ""),
    ("──── 시작 ────", "시작", "시작"),
    ("═══════", "", ""),
    ("一一一一", "", ""),
    ("ㅡ 항목", "- 항목", "- 항목"),
    ("완료 ㅡ", "완료", "완료"),
    ("완료 ㅡ, 다음", "완료, 다음", "완료, 다음"),
    ("3ㅡ5개", "3~5개", "3-5개"),
    ("2024–2025년", "2024~2025년", "2024-2025년"),
    ("값－1", "값-1", "값-1"),
    ("1〜3", "1~3", "1~3"),
    ("===== 시작 =====", "시작", "시작"),
]


@pytest.mark.parametrize("src, reader, dev", DASH_CASES)
def test_dash_family(src, reader, dev):
    assert READER.clean(src) == reader
    assert DEV.clean(src) == dev


@pytest.mark.parametrize(
    "src, reader, dev",
    [
        ("✅ **저장 완료** ㅡ 2024–2025년 데이터 3건 처리했습니다! 🎉",
         "저장 완료: 2024~2025년 데이터 3건 처리했습니다.",
         "[OK] 저장 완료 - 2024-2025년 데이터 3건 처리했습니다!"),
        ("❌ 실패", "실패", "[FAIL] 실패"),
        ("⚠️ 디스크 부족", "디스크 부족", "[WARN] 디스크 부족"),
        ("저장 ✅ 완료", "저장 완료", "저장 완료"),           # status tag only at message start
        ("🚀 서버 시작 ✨", "서버 시작", "서버 시작"),
        ("1️⃣ 단계", "1 단계", "1 단계"),
        ("👨‍👩‍👧 가족", "가족", "가족"),
        ("저장되었습니다!!", "저장되었습니다.", "저장되었습니다!!"),
        ("`config.yaml` 로드", "config.yaml 로드", "`config.yaml` 로드"),
    ],
)
def test_profiles(src, reader, dev):
    assert READER.clean(src) == reader
    assert DEV.clean(src) == dev


@pytest.mark.parametrize(
    "src, expected",
    [
        ("**중요** 설정 변경", "중요 설정 변경"),
        ("### 단계 1", "단계 1"),
        ("---", ""),
        ("```python", ""),
        ("“따옴표” ‘작은’", "\"따옴표\" '작은'"),
        ("로딩 중…", "로딩 중..."),
        ("A → B", "A -> B"),
        ("• 항목", "- 항목"),
        ("▶ 실행", "- 실행"),
        ("값​확인", "값확인"),
        ("결과：성공（3건）", "결과:성공(3건)"),
    ],
)
def test_shared_rules(src, expected):
    assert READER.clean(src) == expected
    assert DEV.clean(src) == expected


PRESERVE = [
    "2026-11-21 user_id=3",
    "a -- b",
    "--dry-run 옵션",
    "k8s-node-01",
    "x = y * z",
    "UTF-8",
    "一般 설정",
    "コーヒー",
    "ㅋㅋ",
    "그는 의사다",
    "※ 참고",
    "© 2026",
    "module __main__ started",  # dunder names are not markdown
]


@pytest.mark.parametrize("src", PRESERVE)
def test_no_false_positive(src):
    assert READER.clean(src) == src
    assert DEV.clean(src) == src


@pytest.mark.parametrize(
    "src",
    ["url https://a.com/x—y 확인", "`a—b` 파일", 'title="—" 저장', "/tmp/a—b.txt 생성"],
)
def test_protected_spans(src):
    assert DEV.clean(src) == src
    assert READER.clean(src) == src  # backticks stay when the code itself is not clean


@pytest.mark.parametrize("src", [c[0] for c in DASH_CASES] + PRESERVE + ["`a—b` 파일", "✅ **x** ㅡ y!"])
def test_idempotent(src):
    for s in (READER, DEV, Sanitizer("reader", "strong")):
        once = s.clean(src)
        assert s.clean(once) == once


@pytest.mark.parametrize("src", [c[0] for c in DASH_CASES] + ["✅ **저장 완료** ㅡ 2024–2025년 3건! 🎉", "### 단계 ㅡ 1"])
def test_findings_follow_the_pipeline(src):
    # Applying every finding's fix at its original span must give what clean() gives,
    # because findings run the rules in the same order as clean().
    for s in (READER, DEV):
        out, last = [], 0
        for f in s.findings(src):
            if f.fix is None:
                continue
            out.append(src[last:f.start])
            out.append(f.fix)
            last = f.end
        out.append(src[last:])
        assert s.clean("".join(out)) == s.clean(src)


def test_emoji_at_line_start_leaves_no_stray_space():
    src = "🚀 배포 완료\n⚠️ 일부 지표\n  ✅ 들여쓴 항목"
    assert READER.clean(src) == "배포 완료\n일부 지표\n  들여쓴 항목"
    assert READER.clean("1️⃣ 단계") == "1 단계"  # keycap mark keeps its space


def test_findings_dash_after_markdown_uses_final_context():
    [dash] = [f for f in READER.findings("**저장 완료** ㅡ 다음") if f.rule_id == "dash.run"]
    assert dash.fix == ": "


def test_findings_skip_protected_spans():
    assert READER.findings("url https://a.com/x—y 확인") == []


def test_dash_inline_option():
    assert Sanitizer(dash_inline="comma").clean("완료 ㅡ 다음") == "완료, 다음"
    assert Sanitizer(dash_inline="hyphen").clean("완료 ㅡ 다음") == "완료 - 다음"
    assert Sanitizer(dash_inline="space").clean("완료 ㅡ 다음") == "완료 다음"


def test_levels():
    assert clean("성공적으로 저장되었습니다!") == "성공적으로 저장되었습니다."
    assert clean("성공적으로 저장되었습니다!", level="strong") == "저장되었습니다."
    assert clean("성공적으로 저장", "dev", "strong") == "성공적으로 저장"  # dev only reports
    strict = Sanitizer(level="strict")
    assert strict.clean("※ 참고") == "※ 참고"
    assert [f.rule_id for f in strict.findings("※ 참고")] == ["symbol.non-ascii"]


def test_status_tag_skipped_when_level_says_it():
    assert DEV.clean("❌ 실패", logging.ERROR) == "실패"
    assert DEV.clean("❌ 실패", logging.INFO) == "[FAIL] 실패"
    assert DEV.clean("✅ 완료", logging.ERROR) == "[OK] 완료"


def test_disable_by_prefix():
    assert Sanitizer(disable=["emoji"]).clean("✅ ok") == "✅ ok"
    assert Sanitizer(disable=["dash"]).clean("a ㅡ b") == "a ㅡ b"


@pytest.mark.parametrize("kwargs", [{"profile": "nope"}, {"level": "nope"}, {"dash_inline": "nope"}])
def test_bad_options(kwargs):
    with pytest.raises(ValueError):
        Sanitizer(**kwargs)


def _logger(handler):
    log = logging.getLogger(f"slopdam-test-{id(handler)}")
    log.handlers[:] = [handler]
    log.propagate = False
    log.setLevel(logging.INFO)
    return log


def test_formatter_routes_by_profile_and_keeps_traceback():
    reader_out, dev_out = io.StringIO(), io.StringIO()
    reader_h, dev_h = logging.StreamHandler(reader_out), logging.StreamHandler(dev_out)
    reader_h.setFormatter(PlainFormatter("%(message)s"))
    dev_h.setFormatter(PlainFormatter("%(levelname)s %(message)s", profile="dev"))
    log = _logger(reader_h)
    log.addHandler(dev_h)

    log.info("✅ 처리 %s건 ㅡ 완료!", 3)
    try:
        raise RuntimeError("boom — 원본")
    except RuntimeError:
        log.exception("🚀 재시도 ㅡ 실패")

    assert reader_out.getvalue().splitlines()[:2] == ["처리 3건: 완료.", "재시도: 실패"]
    assert dev_out.getvalue().splitlines()[:2] == ["INFO [OK] 처리 3건 - 완료!", "ERROR 재시도 - 실패"]
    assert "boom — 원본" in dev_out.getvalue()  # traceback untouched


def test_filter_drops_separator_only_records():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(PlainFilter())
    log = _logger(handler)
    log.info("ㅡㅡㅡㅡㅡㅡ")
    log.info("✅ 완료")
    assert stream.getvalue() == "완료\n"


def test_filters_on_two_handlers_do_not_leak_into_each_other():
    # The README setup: reader for people, dev for the file, a PlainFilter on each.
    reader_out, dev_out = io.StringIO(), io.StringIO()
    reader_h, dev_h = logging.StreamHandler(reader_out), logging.StreamHandler(dev_out)
    reader_h.setFormatter(PlainFormatter("%(message)s"))
    reader_h.addFilter(PlainFilter())
    dev_h.setFormatter(PlainFormatter("%(levelname)s %(message)s", profile="dev"))
    dev_h.addFilter(PlainFilter(profile="dev"))
    log = _logger(reader_h)
    log.addHandler(dev_h)

    log.info("✅ **Saved** %s rows — done!", 3)
    log.info("==========")
    log.error("❌ 업로드 실패 ㅡ 재시도")
    assert reader_out.getvalue().splitlines() == ["Saved 3 rows: done!", "업로드 실패: 재시도"]
    assert dev_out.getvalue().splitlines() == ["INFO [OK] Saved 3 rows - done!", "ERROR 업로드 실패 - 재시도"]


def test_cli_check(tmp_path, capsys):
    (tmp_path / "app.py").write_text(
        'import logging\n'
        'logger = logging.getLogger(__name__)\n'
        'logger.info("✅ 저장 완료")\n'
        'title = "— 장식이지만 로그 아님"\n'
        'print("ok — fine")  # slopdam: ignore\n'
        'log.info("a ㅡ b ✅")  # slopdam: ignore[emoji]\n',
        encoding="utf-8",
    )
    (tmp_path / "app.js").write_text('console.log("=====");\n', encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "app.py:2:" not in out                       # __name__ is not markdown
    assert "app.py:3:" in out and "emoji.pictograph" in out
    assert "app.py:4:" not in out and "app.py:5:" not in out
    assert "app.py:6:" in out and "dash.run" in out
    assert out.count("app.py:6:") == 1                  # emoji on line 6 is ignored
    assert "app.js:1:" in out and "dash.ascii-run" in out  # other languages: line based


def test_cli_check_json(tmp_path, capsys):
    (tmp_path / "a.py").write_text('log.info("완료 ㅡ 다음")\n', encoding="utf-8")
    assert main(["--profile", "dev", "check", "--format", "json", str(tmp_path)]) == 1
    [hit] = json.loads(capsys.readouterr().out)
    assert hit["rule"] == "dash.run" and hit["fix"] == " - " and hit["line"] == 1


def test_cli_check_github_annotations(tmp_path, capsys):
    (tmp_path / "a,b.py").write_text('log.info("완료 ㅡ 100%")\n', encoding="utf-8")
    assert main(["check", "--format", "github", str(tmp_path)]) == 1
    line = capsys.readouterr().out.strip()
    assert line.startswith("::warning file=") and "a%2Cb.py,line=1,col=" in line
    assert "title=slopdam dash.run::" in line


def test_cli_check_sarif(tmp_path, capsys):
    (tmp_path / "a.js").write_text('console.log("🚀 started")\n', encoding="utf-8")
    assert main(["check", "--format", "sarif", str(tmp_path)]) == 1
    run = json.loads(capsys.readouterr().out)["runs"][0]
    assert run["tool"]["driver"]["rules"] == [{"id": "emoji.pictograph", "shortDescription": {"text": "emoji or pictograph"}}]
    [result] = run["results"]
    assert result["ruleId"] == "emoji.pictograph"
    assert result["locations"][0]["physicalLocation"]["region"] == {"startLine": 1, "startColumn": 14}


def test_cli_check_stdin_plain_text(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("배포 완료 ㅡ 3건\n문제 없음\n"))
    assert main(["check", "-"]) == 1  # plain text: every line is checked
    out = capsys.readouterr().out
    assert out.startswith("<stdin>:1:") and "dash.run" in out


def test_cli_check_stdin_as_python(monkeypatch, capsys):
    src = '# ✅ comment\nx = "— not a log"\nlog.info("✅ done")\n'
    monkeypatch.setattr("sys.stdin", io.StringIO(src))
    assert main(["check", "--stdin-filename", "app.py", "--format", "json", "-"]) == 1
    [hit] = json.loads(capsys.readouterr().out)
    assert hit["path"] == "app.py" and hit["line"] == 3 and hit["rule"] == "emoji.pictograph"


def test_cli_check_clean_tree(tmp_path):
    (tmp_path / "ok.py").write_text(
        'logger.info("saved %d rows", n)\n'
        '# example: logging.warning("✅ — done")\n'  # comment lines are not log calls
        '// console.log("🚀")\n',
        encoding="utf-8",
    )
    assert main(["check", str(tmp_path)]) == 0
