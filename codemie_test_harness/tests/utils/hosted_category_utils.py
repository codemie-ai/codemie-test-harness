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

"""Applications with known categories in each catalog scope, for the category filter tests."""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from codemie_sdk.models.hosted_application import HostedApplication

from codemie_test_harness.tests.test_data.hosted_application_category_test_data import (
    CATEGORY_APP_LABELS,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.hosted_application_utils import HostedUser


@dataclass
class CategoryWorld:
    """Applications of one catalog scope, each named after what it carries, and who lists them.

    Every name starts with ``token``, so a name search finds this world's applications on a
    stand that holds many others. ``unfiltered`` are the labels the viewer lists when no
    category is selected.
    """

    scope: str
    viewer: HostedUser
    token: str
    apps: dict[str, HostedApplication]
    unfiltered: tuple[str, ...]

    def ids(self, *labels: str) -> list[str]:
        return [self.apps[label].id for label in labels]

    def listed(self, q: Optional[str] = None, **filters: Any) -> list[str]:
        """Ids the viewer lists in the scope, narrowed by a name search and the given filters."""
        return self.viewer.apps.all_app_ids(
            self.scope, q=self.token if q is None else q, **filters
        )

    def name_of(self, label: str) -> str:
        return f"{self.token} {label}"


def _create_all(
    owner: HostedUser,
    project: str,
    token: str,
    categories: list[Any],
    labels: tuple[str, ...],
    shared: bool = False,
) -> dict[str, HostedApplication]:
    return {
        label: owner.apps.create_app(
            project,
            shared=shared,
            name=f"{token} {label}",
            categories=[categories[index].id for index in CATEGORY_APP_LABELS[label]],
        )
        for label in labels
    }


def _mine(owner, reader, projects, categories) -> CategoryWorld:
    token = get_random_name()
    labels = tuple(CATEGORY_APP_LABELS)
    apps = _create_all(owner, owner.personal_project, token, categories, labels)
    return CategoryWorld("mine", owner, token, apps, labels)


def _project(owner, reader, projects, categories) -> CategoryWorld:
    token = get_random_name()
    labels = tuple(CATEGORY_APP_LABELS)
    project = projects(owner, reader)
    apps = _create_all(owner, project, token, categories, labels, shared=True)
    return CategoryWorld("project", reader, token, apps, labels)


def _shared(owner, reader, projects, categories) -> CategoryWorld:
    token = get_random_name()
    labels = tuple(CATEGORY_APP_LABELS)
    apps = _create_all(owner, owner.personal_project, token, categories, labels)
    for app in apps.values():
        owner.service.share_with_users(app.id, [reader.user_id])
    return CategoryWorld("shared", reader, token, apps, labels)


def _marketplace(owner, reader, projects, categories) -> CategoryWorld:
    """Publishing needs a category, so the application without one stays private and unlisted."""
    token = get_random_name()
    labels = tuple(CATEGORY_APP_LABELS)
    apps = _create_all(owner, owner.personal_project, token, categories, labels)
    published = tuple(label for label in labels if CATEGORY_APP_LABELS[label])
    for label in published:
        owner.apps.publish(apps[label].id, [c.id for c in apps[label].categories])
    return CategoryWorld("marketplace", reader, token, apps, published)


WORLD_BUILDERS: dict[str, Callable[..., CategoryWorld]] = {
    "mine": _mine,
    "project": _project,
    "marketplace": _marketplace,
    "shared": _shared,
}
