# SPDX-License-Identifier: MIT
"""Adapters for the standard library ``logging`` module.

Typical routing: one logger, a ``reader`` handler for people and a ``dev`` handler for files.

    console.setFormatter(PlainFormatter("%(message)s"))                          # reader (default)
    file.setFormatter(PlainFormatter("%(asctime)s %(message)s", profile="dev"))
"""
from __future__ import annotations

import logging as _logging
from typing import Optional

from .rules import Sanitizer


class PlainFormatter(_logging.Formatter):
    """Formatter that cleans the message before formatting.

    The original record is left untouched so other handlers still see it.
    Exception tracebacks are never modified.
    """

    def __init__(self, *args, profile: str = "reader", level: str = "basic",
                 sanitizer: Optional[Sanitizer] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sanitizer = sanitizer or Sanitizer(profile, level)

    def format(self, record: _logging.LogRecord) -> str:
        copy = _logging.makeLogRecord(record.__dict__)
        copy.msg, copy.args = self.sanitizer.clean(record.getMessage(), record.levelno), None
        return super().format(copy)


class PlainFilter(_logging.Filter):
    """Filter that cleans the message in place and drops records that end up empty
    (for example a log call that only prints a separator line)."""

    def __init__(self, name: str = "", *, profile: str = "reader", level: str = "basic",
                 sanitizer: Optional[Sanitizer] = None):
        super().__init__(name)
        self.sanitizer = sanitizer or Sanitizer(profile, level)

    def filter(self, record: _logging.LogRecord) -> bool:
        if not super().filter(record):
            return False
        cleaned = self.sanitizer.clean(record.getMessage(), record.levelno)
        if not cleaned and not record.exc_info:
            return False
        record.msg, record.args = cleaned, None
        return True
