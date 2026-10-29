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

"""UI test for the skill bundle ceiling warning in the skill editor.

The editor warns when an uploaded skill archive holds more files than an assistant workspace receives,
stays silent within the limit, and never blocks saving. The limit is the one the environment applies
(``GET /v1/skills/config``).
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.skills.create_edit_skill_page import (
    CreateEditSkillPage,
)
from codemie_test_harness.tests.ui.pageobject.skills.skills_page import SkillsPage
from codemie_test_harness.tests.ui.test_data.skill_test_data import (
    bundle_file_name,
    build_skill_bundle_archive,
    get_random_skill_name,
)
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


@pytest.fixture
def bundle_file_count_limit(client):
    """The number of bundle files an assistant workspace receives, as the environment applies it."""
    return client.skills.get_config().bundle_seed_max_file_count


@pytest.fixture
def skills_to_delete(skill_utils):
    """Names of skills created through the UI; they are deleted through the API at teardown."""
    names = []
    yield names
    for name in names:
        try:
            created = skill_utils.get_skill_by_name(name)
            skill_utils.delete_skill_by_id(created.id)
        except Exception as error:
            logger.warning(
                f"Could not delete skill '{name}' created by the test: {error}"
            )


@pytest.mark.skill
@pytest.mark.ui
def test_skill_editor_shows_no_bundle_warning_within_the_file_limit(
    page, tmp_path, bundle_file_count_limit
):
    """An archive with exactly the limit of files is read and no warning is shown."""
    archive = build_skill_bundle_archive(tmp_path, bundle_file_count_limit)
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    create_page.upload_skill_file(str(archive))

    create_page.should_list_bundle_file(bundle_file_name(0))
    create_page.should_not_see_bundle_ceiling_warning()


@pytest.mark.skill
@pytest.mark.ui
def test_skill_editor_warns_about_bundle_files_over_the_limit_and_still_saves(
    page, tmp_path, bundle_file_count_limit, skills_to_delete
):
    """An archive one file over the limit shows the count and the limit, and the skill is still saved."""
    archive = build_skill_bundle_archive(tmp_path, bundle_file_count_limit + 1)
    skill_name = get_random_skill_name("bundle-warning")
    skills_to_delete.append(skill_name)
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    create_page.upload_skill_file(str(archive))

    create_page.should_list_bundle_file(bundle_file_name(0))
    create_page.should_see_bundle_file_count_warning(
        bundle_file_count_limit + 1, bundle_file_count_limit
    )

    create_page.fill_name(skill_name)
    create_page.click_save()

    SkillsPage(page).should_see_skill_with_name(skill_name)
