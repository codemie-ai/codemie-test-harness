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

"""Fixtures of the CodeMie CLI proxy daemon tests: isolated homes with a stub upstream."""

import shutil

import pytest

from codemie_test_harness.tests.utils.cli_proxy_utils import (
    CliProxyEnv,
    StubUpstream,
    new_env_dir,
)


@pytest.fixture
def cli_proxy_env_factory():
    """Builds isolated daemon environments; each one's daemons, stub and home are removed after the test."""
    created = []

    def make(
        stream=False, release_after_arrivals=0, signed_in=True, responder=None
    ) -> CliProxyEnv:
        stub = StubUpstream(
            stream=stream,
            release_after_arrivals=release_after_arrivals,
            responder=responder,
        ).start()
        env = CliProxyEnv(new_env_dir(), stub, signed_in=signed_in)
        created.append(env)
        return env

    yield make

    for env in created:
        env.cleanup()
        env.stub.stop()
        shutil.rmtree(env.home, ignore_errors=True)


@pytest.fixture
def daemon_env(cli_proxy_env_factory) -> CliProxyEnv:
    """A signed-in environment whose upstream answers every request with a small JSON body."""
    return cli_proxy_env_factory()
