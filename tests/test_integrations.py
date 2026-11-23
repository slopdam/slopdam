# SPDX-License-Identifier: MIT
import io
import json

import pytest

import slopdam


def test_core_import_does_not_need_integrations():
    import slopdam.integrations  # noqa: F401  (imports neither library)

    assert slopdam.clean("✅ 완료 ㅡ 다음") == "완료: 다음"


def test_structlog_processor():
    structlog = pytest.importorskip("structlog")
    from slopdam.integrations.structlog import SlopdamProcessor

    out = io.StringIO()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            SlopdamProcessor(profile="dev", keys=["note"]),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        logger_factory=structlog.PrintLoggerFactory(out),
        cache_logger_on_first_use=False,
    )
    log = structlog.get_logger()
    log.info("✅ 저장 — 완료", note="**확인** 필요", user="a—b")
    log.error("❌ 실패")
    first, second = (json.loads(line) for line in out.getvalue().splitlines())
    assert first["event"] == "[OK] 저장 - 완료"
    assert first["note"] == "확인 필요"
    assert first["user"] == "a—b"          # not listed in keys: data stays as it is
    assert second["event"] == "실패"        # the level already says it failed
    structlog.reset_defaults()


def test_structlog_processor_without_level():
    pytest.importorskip("structlog")
    from slopdam.integrations.structlog import SlopdamProcessor

    event = SlopdamProcessor(profile="dev")(None, "warning", {"event": "⚠️ 디스크 부족"})
    assert event == {"event": "디스크 부족"}
    assert SlopdamProcessor()(None, "msg", {"event": 3}) == {"event": 3}  # non-strings untouched


def test_loguru_patcher():
    loguru = pytest.importorskip("loguru")
    from slopdam.integrations.loguru import SlopdamPatcher

    out = io.StringIO()
    logger = loguru.logger.patch(SlopdamPatcher(profile="dev"))
    sink = logger.add(out, format="{level} {message}")
    try:
        logger.info("✅ 저장 — 완료")
        logger.error("❌ 실패 https://a.com/x—y")
    finally:
        logger.remove(sink)
    assert out.getvalue().splitlines() == ["INFO [OK] 저장 - 완료", "ERROR 실패 https://a.com/x—y"]
