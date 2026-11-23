# SPDX-License-Identifier: MIT
"""Adapters for the standard library ``logging`` module.

Typical routing: one logger, a ``reader`` handler for people and a ``dev`` handler for files.

    console.setFormatter(PlainFormatter("%(message)s"))                          # reader (default)
    file.setFormatter(PlainFormatter("%(asctime)s %(message)s", profile="dev"))
"""
from __future__ import annotations

import logging as _logging
import sys
from typing import Optional, Union

from .rules import Sanitizer

# Where PlainFilter keeps the message it replaced (Python < 3.12), so the next handler,
# which may use another profile, starts from the original text and not from ours.
_ORIGINAL = "slopdam_original"


def _message(record: _logging.LogRecord) -> str:
    msg, args = getattr(record, _ORIGINAL, (record.msg, record.args))
    msg = str(msg)
    return msg % args if args else msg


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
        copy.msg, copy.args = self.sanitizer.clean(_message(record), record.levelno), None
        return super().format(copy)


class PlainFilter(_logging.Filter):
    """Filter that cleans the message and drops records that end up empty
    (for example a log call that only prints a separator line).

    Each handler gets its own result: on Python 3.12+ the filter hands its handler a
    cleaned copy; before that it changes the record but keeps the original message,
    which PlainFilter and PlainFormatter on later handlers start from. Other formatters
    on later handlers see the cleaned text on Python before 3.12.
    """

    def __init__(self, name: str = "", *, profile: str = "reader", level: str = "basic",
                 sanitizer: Optional[Sanitizer] = None):
        super().__init__(name)
        self.sanitizer = sanitizer or Sanitizer(profile, level)

    def filter(self, record: _logging.LogRecord) -> Union[bool, _logging.LogRecord]:
        if not super().filter(record):
            return False
        cleaned = self.sanitizer.clean(_message(record), record.levelno)
        if not cleaned and not record.exc_info:
            return False
        if sys.version_info >= (3, 12):
            copy = _logging.makeLogRecord(record.__dict__)
            copy.msg, copy.args = cleaned, None
            return copy
        if not hasattr(record, _ORIGINAL):
            setattr(record, _ORIGINAL, (record.msg, record.args))
        record.msg, record.args = cleaned, None
        return True
