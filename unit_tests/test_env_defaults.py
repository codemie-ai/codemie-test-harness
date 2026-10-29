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

import os

import pytest

from codemie_test_harness.tests.utils.env_utils import (
    AWS_CREDENTIAL_VARS,
    load_env_file,
)

TEMPLATE = "AUTH_USERNAME=admin@codemie.ai\nVERIFY_SSL=False\n"


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    # Work on a copy so values load_dotenv writes never leak into other tests.
    # Importing the harness package already loaded the template, so drop its keys.
    dropped = (
        *AWS_CREDENTIAL_VARS,
        "CODEMIE_API_DOMAIN",
        "AUTH_USERNAME",
        "VERIFY_SSL",
    )
    env = {k: v for k, v in os.environ.items() if k not in dropped}
    monkeypatch.setattr(os, "environ", env)
    (tmp_path / ".env.template").write_text(TEMPLATE)
    return tmp_path / ".env"


@pytest.mark.parametrize(
    "domain",
    [
        None,
        "http://localhost:8080",
        "localhost:8080",
        "http://[::1]:8080",
        "0.0.0.0:80",
    ],
)
def test_template_loaded_for_local_stack(env_file, domain):
    if domain:
        os.environ["CODEMIE_API_DOMAIN"] = domain
    load_env_file(env_file)
    assert os.environ["AUTH_USERNAME"] == "admin@codemie.ai"


@pytest.mark.parametrize("aws_var", AWS_CREDENTIAL_VARS)
def test_template_skipped_with_aws_credentials(env_file, aws_var):
    os.environ[aws_var] = "x"
    load_env_file(env_file)
    assert "AUTH_USERNAME" not in os.environ


def test_template_skipped_for_remote_domain(env_file):
    os.environ["CODEMIE_API_DOMAIN"] = "https://codemie.example.com"
    load_env_file(env_file)
    assert "AUTH_USERNAME" not in os.environ


def test_env_file_wins_over_template(env_file):
    env_file.write_text("AUTH_USERNAME=me\n")
    load_env_file(env_file)
    assert os.environ["AUTH_USERNAME"] == "me"
    assert "VERIFY_SSL" not in os.environ
