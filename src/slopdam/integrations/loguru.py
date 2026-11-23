# SPDX-License-Identifier: MIT
"""loguru patcher.

    from loguru import logger
    logger = logger.patch(SlopdamPatcher(profile="dev"))

The patch applies to every sink of the patched logger. To give sinks different
profiles, bind a value and use a format function per sink, or patch two loggers.
"""
from __future__ import annotations

from typing import Any, Optional

from ..rules import Sanitizer


class SlopdamPatcher:
    def __init__(self, profile: str = "reader", level: str = "basic", sanitizer: Optional[Sanitizer] = None):
        self.sanitizer = sanitizer or Sanitizer(profile, level)

    def __call__(self, record: Any) -> None:
        # loguru's numbers match the logging module for WARNING and ERROR (30, 40).
        record["message"] = self.sanitizer.clean(record["message"], record["level"].no)
