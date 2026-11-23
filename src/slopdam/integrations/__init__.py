# SPDX-License-Identifier: MIT
"""Adapters for third-party logging libraries.

Each module imports nothing from its library at import time, so slopdam keeps
working without them:

    slopdam.integrations.structlog   SlopdamProcessor for structlog
    slopdam.integrations.loguru      SlopdamPatcher for loguru
"""
