# SPDX-License-Identifier: MIT
"""structlog processor.

Put it before the renderer:

    structlog.configure(processors=[
        SlopdamProcessor(profile="dev"),
        structlog.processors.JSONRenderer(),
    ])

The event (the message) is cleaned. Other values are cleaned only when their key
is listed in ``keys``, because structured fields are usually data, not prose.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, MutableMapping, Optional

from ..rules import Sanitizer

EventDict = MutableMapping[str, Any]


class SlopdamProcessor:
    def __init__(self, profile: str = "reader", level: str = "basic", keys: Iterable[str] = (),
                 sanitizer: Optional[Sanitizer] = None):
        self.sanitizer = sanitizer or Sanitizer(profile, level)
        self.keys = ("event", *keys)

    def __call__(self, logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
        # The level is known only once add_log_level has run; fall back to the method name.
        name = str(event_dict.get("level", method_name)).upper()
        levelno = logging.getLevelName("WARNING" if name == "WARN" else name)
        levelno = levelno if isinstance(levelno, int) else None
        for key in self.keys:
            value = event_dict.get(key)
            if isinstance(value, str):
                event_dict[key] = self.sanitizer.clean(value, levelno)
        return event_dict
