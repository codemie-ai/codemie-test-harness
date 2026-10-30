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

"""
UI Test Suite for Attaching Skills to Assistants

This test suite implements UI automated tests for attaching skills to assistants
following Page Object Model (POM) best practices.

Test Coverage:
- AC#4: Attach skills to assistants
"""

import pytest
from hamcrest import assert_that, has_item, not_

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.pageobject.skills.create_edit_skill_page import (
    CreateEditSkillPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    get_minimal_assistant_data,
)
from codemie_test_harness.tests.ui.test_data.skill_test_data import (
    get_minimal_skill_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_assistant_create_page_has_skills_section(page):
    """
    Test #22: Create Assistant page has Skills attachment section.

    AC#4: Attach skills - Verify Skills section exists.
    """
    create_assistant_page = CreateEditAssistantPage(page)
    create_assistant_page.navigate_to()

    # Verify Skills section is visible with all required elements
    create_assistant_page.should_have_skills_section_visible()


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_attach_skill_to_assistant(page):
    """
    Test #23: Attach a skill to assistant during creation.

    AC#4: Attach skills - Attach a skill to assistant during creation.
    """
    # First create a private skill
    skill_data = get_minimal_skill_data()
    create_skill_page = CreateEditSkillPage(page)
    create_skill_page.navigate_to()
    create_skill_page.create_skill(
        name=skill_data.name,
        description=skill_data.description,
        instructions=skill_data.instructions,
        shared=False,
    )

    # Now create assistant and attach the skill
    assistant_data = get_minimal_assistant_data()
    create_assistant_page = CreateEditAssistantPage(page)
    create_assistant_page.navigate_to()

    # Fill basic assistant info
    create_assistant_page.fill_name(assistant_data.name)
    create_assistant_page.fill_description(assistant_data.description)
    create_assistant_page.fill_system_prompt(assistant_data.system_prompt)

    # Attach the private skill
    create_assistant_page.attach_skill(skill_data.name)

    # Save assistant
    create_assistant_page.click_create()

    # Verify successful creation
    assistants_page = AssistantsPage(page)
    assistant_details_page = assistants_page.open_assistant_details(assistant_data.name)
    assistant_details_page.should_have_attached_skill(skill_data.name)


@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_attach_marketplace_skill_to_assistant(page):
    """
    Test #25: Attach a marketplace skill to assistant.

    AC#4: Attach skills - Attach marketplace skill.
    """
    from codemie_test_harness.tests.ui.pageobject.skills.skills_page import SkillsPage
    from codemie_test_harness.tests.ui.test_data.skill_test_data import (
        get_full_skill_data,
    )

    # Navigate to skills list
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Create a private skill
    skill_data = get_full_skill_data()
    create_skill_page = CreateEditSkillPage(page)
    create_skill_page.navigate_to()

    create_skill_page.create_skill(
        name=skill_data.name,
        description=skill_data.description,
        instructions=skill_data.instructions,
        categories=skill_data.categories,
        shared=False,
    )

    # Publish skill to marketplace
    skills_page.publish_skill_to_marketplace(skill_data.name)

    # Confirm publish dialog
    skills_page.confirm_publish()

    # Now create assistant and attach the marketplace skill
    assistant_data = get_minimal_assistant_data()
    create_assistant_page = CreateEditAssistantPage(page)
    create_assistant_page.navigate_to()

    create_assistant_page.fill_name(assistant_data.name)
    create_assistant_page.fill_description(assistant_data.description)
    create_assistant_page.fill_system_prompt(assistant_data.system_prompt)

    # Attach marketplace skill
    create_assistant_page.attach_skill(skill_data.name)

    # Save assistant
    create_assistant_page.click_create()

    # Verify successful creation
    assistants_page = AssistantsPage(page)
    assistant_view_page = assistants_page.open_assistant_details(assistant_data.name)

    # Verify marketplace skill is attached
    assistant_view_page.should_have_attached_skill(skill_data.name)


@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_attach_multiple_skills_to_assistant(page):
    """
    Test #26: Attach 2+ skills to single assistant.

    AC#4: Attach skills - Multiple skills attachment.
    """
    # Create two skills
    skill1_data = get_minimal_skill_data()
    skill2_data = get_minimal_skill_data()

    for skill_data in [skill1_data, skill2_data]:
        create_skill_page = CreateEditSkillPage(page)
        create_skill_page.navigate_to()
        create_skill_page.create_skill(
            name=skill_data.name,
            description=skill_data.description,
            instructions=skill_data.instructions,
            shared=False,
        )

    # Create assistant and attach both skills
    assistant_data = get_minimal_assistant_data()
    create_assistant_page = CreateEditAssistantPage(page)
    create_assistant_page.navigate_to()

    create_assistant_page.fill_name(assistant_data.name)
    create_assistant_page.fill_description(assistant_data.description)
    create_assistant_page.fill_system_prompt(assistant_data.system_prompt)

    # Attach first skill
    create_assistant_page.attach_skill(skill1_data.name)

    # Attach second skill
    create_assistant_page.attach_skill(skill2_data.name)

    # Save assistant
    create_assistant_page.click_create()

    # Verify successful creation
    assistants_page = AssistantsPage(page)
    assistant_view_page = assistants_page.open_assistant_details(assistant_data.name)

    # Verify skills are attached
    assistant_view_page.should_have_attached_skill(skill1_data.name)
    assistant_view_page.should_have_attached_skill(skill2_data.name)


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_detach_skill_from_assistant(page):
    """
    Test #27: Remove attached skill from assistant.

    AC#4: Attach skills - Detach skill functionality.
    """
    # Create a skill
    skill_data = get_minimal_skill_data()
    create_skill_page = CreateEditSkillPage(page)
    create_skill_page.navigate_to()
    create_skill_page.create_skill(
        name=skill_data.name,
        description=skill_data.description,
        instructions=skill_data.instructions,
        shared=False,
    )

    # Create assistant with attached skill
    assistant_data = get_minimal_assistant_data()
    create_assistant_page = CreateEditAssistantPage(page)
    create_assistant_page.navigate_to()

    create_assistant_page.fill_name(assistant_data.name)
    create_assistant_page.fill_description(assistant_data.description)
    create_assistant_page.fill_system_prompt(assistant_data.system_prompt)

    # Attach skill
    create_assistant_page.attach_skill(skill_data.name)

    # Save assistant
    create_assistant_page.click_create()

    # Now detach the skill from the assistant
    assistants_page = AssistantsPage(page)
    assistant_edit_page = assistants_page.click_assistant_edit(assistant_data.name)
    assistant_edit_page.detach_skill(skill_data.name)
    assistant_edit_page.click_save()

    # Verify skill is not attached
    assistant_view_page = assistants_page.open_assistant_details(assistant_data.name)
    assistant_view_page.should_not_have_skill_attached(skill_data.name)


@pytest.mark.skill
@pytest.mark.assistant
@pytest.mark.ui
def test_edit_assistant_shows_name_of_skill_missing_from_catalog(
    page, skill_in_other_project, raw_assistant, client
):
    """
    Skill attached to an assistant but absent from the Skills
    catalog (skill belongs to another project, not in marketplace) must be shown
    by its real name on Edit Assistant page, not as "null".

    Steps:
    1. Create a skill in another project (project visibility, not published).
    2. Create an assistant in the default project and attach the skill (API).
    3. Verify via API that the skill is attached to the assistant but is not
       returned by the catalog request the Edit page uses
       (scope=project_with_marketplace, project=[assistant project]).
    4. Open Edit Assistant page and verify the Skills field shows the skill name.
    """
    assistant_name = get_random_name().replace("_", "-")
    assistant_id = raw_assistant(
        name=assistant_name, skill_id=skill_in_other_project.id
    )

    attached_ids = [s.id for s in client.skills.get_assistant_skills(assistant_id)]
    assert_that(attached_ids, has_item(skill_in_other_project.id))
    catalog_ids = [
        s.id
        for s in client.skills.list(
            per_page=100,
            filters={"scope": "project_with_marketplace", "project": [PROJECT]},
        ).skills
    ]
    assert_that(catalog_ids, not_(has_item(skill_in_other_project.id)))

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(assistant_name)
    edit_page = assistants_page.click_assistant_edit(assistant_name)

    edit_page.should_show_selected_skill_name(skill_in_other_project.name)
