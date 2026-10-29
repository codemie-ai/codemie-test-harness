# Copyright 2026 EPAM Systems, Inc. (“EPAM”)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ReportPortal guard: only wire RP logging when the RP plugin is active.

Importable without the live-platform ``tests/conftest.py``.
"""

from __future__ import annotations

import logging

_LOGGER_NAME = "reportportal_logger"
_rp_loggers: dict[str, logging.Logger] = {}


def rp_enabled(config) -> bool:
    """True when pytest-reportportal reports for this run.

    The plugin decides this in its own ``pytest_configure`` from CLI options,
    ini keys and env vars, and stores the result on the config.
    """
    return bool(getattr(config, "_rp_enabled", False))


def get_rp_logger(config, name: str = _LOGGER_NAME) -> logging.Logger:
    """Return an RP logger when RP reports for this run, otherwise a plain one."""
    if not rp_enabled(config):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        return logger

    if name not in _rp_loggers:
        from reportportal_client import RPLogger, RPLogHandler

        # Built directly, not through setLoggerClass, so no global logging state changes
        logger = RPLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(RPLogHandler())
        _rp_loggers[name] = logger
    return _rp_loggers[name]


def log_with_attachment(logger, msg: str, attachment: dict) -> None:
    """Log msg; pass the attachment only when the logger can consume it."""
    try:
        from reportportal_client import RPLogger
    except ImportError:
        RPLogger = ()
    if isinstance(logger, RPLogger):
        logger.info(msg, attachment=attachment)
    else:
        logger.info(msg)
