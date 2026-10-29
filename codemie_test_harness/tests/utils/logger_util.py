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

import logging
import sys


class _SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that drops a record instead of dumping a traceback
    when the underlying stream is already closed.

    Under pytest-xdist, a worker's pytest_sessionfinish cleanup can still be
    logging after the gateway back to the master has been torn down, which
    closes this handler's (redirected) stdout. The base StreamHandler.emit()
    would otherwise raise ValueError/OSError on every such call, each
    printed as a "Logging error" block.
    """

    def emit(self, record):
        stream = self.stream
        if getattr(stream, "closed", False):
            return
        try:
            super().emit(record)
        except (ValueError, OSError):
            # Stream closed/broken between the check above and the write.
            pass


def setup_logger(name=None, level=logging.INFO):
    """
    Sets up a logger with a consistent configuration.
    If no name is specified, it returns the root logger.
    """
    logger = logging.getLogger(name)  # Use specific module name

    if not logger.handlers:  # Prevent adding duplicate handlers
        logger.setLevel(level)

        # Create a console handler
        console_handler = _SafeStreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Create a formatter and attach it to the handler
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(console_handler)

    return logger
