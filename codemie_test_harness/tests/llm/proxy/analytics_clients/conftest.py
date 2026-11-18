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

"""Fixtures of the analytics-flag tests: isolated machines whose only clients are the ones a test installs."""

import shutil

import pytest

from codemie_test_harness.tests.utils.cli_proxy_utils import (
    CliProxyEnv,
    StubUpstream,
    new_env_dir,
)


@pytest.fixture
def analytics_env_factory():
    """Builds isolated machines with the named clients installed; each one's daemon, stub and home are removed after the test."""
    created = []

    def make(*installed: str, signed_in: bool = True) -> CliProxyEnv:
        stub = StubUpstream().start()
        env = CliProxyEnv(new_env_dir(), stub, signed_in=signed_in, isolated_path=True)
        env.install_clients(*installed)
        created.append(env)
        return env

    yield make

    for env in created:
        env.cleanup()
        env.stub.stop()
        shutil.rmtree(env.home, ignore_errors=True)
