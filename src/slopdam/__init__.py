# SPDX-License-Identifier: MIT
from .rules import LEVELS, PROFILES, RULES, Finding, Rule, Sanitizer
from .stdlib import PlainFilter, PlainFormatter

__all__ = ["LEVELS", "PROFILES", "RULES", "Finding", "PlainFilter", "PlainFormatter", "Rule", "Sanitizer", "clean"]
__version__ = "0.6.0"


def clean(text: str, profile: str = "reader", level: str = "basic") -> str:
    return Sanitizer(profile, level).clean(text)
