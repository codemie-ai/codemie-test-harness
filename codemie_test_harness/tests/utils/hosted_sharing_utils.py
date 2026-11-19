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

"""The people around a hosted application and the roles that decide who may share it.

An application's sharing managers are its creator, the admins of its project, platform admins and
maintainers; everyone else who can read it is a non-manager. ``SharingWorld`` builds one live
application of a plain user in a fresh shared project and creates each person in a role only when a
test asks for them, from the ``users`` and ``user_projects`` rows the sharing rule reads.
"""

import logging
from contextlib import ExitStack
from typing import Any, Optional

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    ACTIVITY_DOMAIN,
    ACTIVITY_WAIT_SECONDS,
    html_artifact,
)
from codemie_test_harness.tests.utils.activity_utils import ActivityUtils
from codemie_test_harness.tests.utils.base_utils import get_random_name, poll_until
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.hosted_application_utils import (
    HostedApplicationUtils,
    HostedUser,
)
from codemie_test_harness.tests.utils.user_lifecycle_utils import (
    new_logged_in_user,
    new_user,
    user_email,
)
from codemie_test_harness.tests.utils.user_utils import UserUtils

logger = logging.getLogger(__name__)


def _cleanup_applications(user: HostedUser) -> None:
    try:
        user.apps.cleanup()
    except Exception as error:
        logger.warning(f"Failed to clean up applications of {user.email}: {error}")


class HostedPeople:
    """Users and shared projects of one test, removed after it in a safe order.

    Every user is a fresh account and keeps its password, so a browser can sign in as them. The
    applications of a user go before the user; a project, and the applications of its users, go
    before the users, because an application in a project blocks the project's deletion.
    """

    def __init__(
        self, cleanup: ExitStack, user_lifecycle, admin_utils, user_utils, project_utils
    ):
        self._cleanup = cleanup
        self._user_lifecycle = user_lifecycle
        self._admin_utils = admin_utils
        self._user_utils = user_utils
        self._project_utils = project_utils
        self._project_users: dict[str, list[HostedUser]] = {}

    def user(self, admin: bool = False) -> HostedUser:
        """A plain user, or with ``admin`` an account the auth server makes an administrator."""
        logged_in = self._cleanup.enter_context(
            new_logged_in_user(self._user_lifecycle, user_email("hosted"), admin=admin)
        )
        user = HostedUser(
            email=logged_in.email,
            user_id=logged_in.user_id,
            client=logged_in.client,
            apps=HostedApplicationUtils(logged_in.client),
            password=logged_in.password,
        )
        # Registered after the user, so it runs before the user is deleted.
        self._cleanup.callback(_cleanup_applications, user)
        return user

    def platform_admin(self) -> HostedUser:
        """A user whose ``users`` row says platform admin, once the role is active on every replica."""
        user = self.user(admin=True)
        self._user_utils.update_admin_user(user.user_id, is_admin=True)
        UserUtils(user.client).wait_until_user_management_effective()
        return user

    def maintainer(self) -> HostedUser:
        """A user with the maintainer flag only, once the role is active on every replica."""
        user = self.user()
        self._user_utils.update_admin_user(user.user_id, is_maintainer=True)
        UserUtils(user.client).wait_until_user_management_effective()
        return user

    def external_account_id(self) -> str:
        """Id of a fresh external account, a user the platform never lets anyone share with."""
        email = user_email("external")
        password = self._cleanup.enter_context(
            new_user(self._user_lifecycle, email, admin=False, external=True)
        )
        return get_client(username=email, password=password).users.about_me().user_id

    def project(self, *members: HostedUser, admins: tuple = ()) -> str:
        """A new project with ``members`` as plain members and ``admins`` as its project admins."""
        name = get_random_name()
        self._admin_utils.create_project(name)
        self._project_users[name] = []
        # The project goes before the users it was built with, whose own callbacks were registered
        # earlier. A user who joins later is tracked in ``_project_users``, so the teardown removes
        # the applications of every member before the project, which an application would block.
        self._cleanup.callback(self._remove_project, name)
        for member in members:
            self._user_utils.assign_user_to_project(member.user_id, name)
            self._track(name, member)
        for admin in admins:
            self.make_project_admin(admin, name)
        return name

    def _track(self, project: str, user: HostedUser) -> None:
        if user not in self._project_users[project]:
            self._project_users[project].append(user)

    def make_project_admin(self, user: HostedUser, project: str) -> None:
        self._user_utils.assign_user_to_project(
            user.user_id, project, is_project_admin=True
        )
        self._track(project, user)

    def add_member(self, user: HostedUser, project: str) -> None:
        self._user_utils.assign_user_to_project(user.user_id, project)
        self._track(project, user)

    def _remove_project(self, name: str) -> None:
        for user in self._project_users.pop(name, []):
            _cleanup_applications(user)
        try:
            self._project_utils.delete_project_with_all_members(name)
        except Exception as error:
            logger.warning(f"Failed to delete project {name}: {error}")


class SharingWorld:
    """A live application of a plain user in a fresh shared project, and the people around it.

    ``shared`` is the "Shared with project" switch; ``published`` puts the application on the
    marketplace. ``person(role)`` creates the person in that role on first use and returns the same
    person afterwards. Roles: ``creator``, the managers ``project_admin``, ``platform_admin`` and
    ``maintainer``, and the non-managers ``project_member``, ``named_grantee``,
    ``marketplace_viewer`` and ``admin_of_other_project``.
    """

    def __init__(
        self, people: HostedPeople, shared: bool = True, published: bool = False
    ):
        self.people = people
        self.creator = people.user()
        self.project = people.project(self.creator)
        self.artifact = html_artifact()
        app = self.creator.apps.create_app(self.project, shared=shared)
        self.creator.apps.go_live(app.id, self.artifact)
        if published:
            self.creator.apps.publish(app.id)
        self.app_id = app.id
        self.app_name = app.name
        self._people: dict[str, HostedUser] = {"creator": self.creator}

    def person(self, role: str) -> HostedUser:
        if role not in self._people:
            self._people[role] = getattr(self, f"_new_{role}")()
        return self._people[role]

    def _new_project_admin(self) -> HostedUser:
        user = self.people.user()
        self.people.make_project_admin(user, self.project)
        return user

    def _new_platform_admin(self) -> HostedUser:
        return self.people.platform_admin()

    def _new_maintainer(self) -> HostedUser:
        return self.people.maintainer()

    def _new_project_member(self) -> HostedUser:
        user = self.people.user()
        self.people.add_member(user, self.project)
        return user

    def _new_named_grantee(self) -> HostedUser:
        user = self.people.user()
        self.creator.service.share_with_users(self.app_id, [user.user_id])
        return user

    def _new_marketplace_viewer(self) -> HostedUser:
        # Reads the application only when the world was built with ``published``.
        return self.people.user()

    def _new_admin_of_other_project(self) -> HostedUser:
        user = self.people.user()
        self.people.project(admins=(user,))
        return user

    def shared_with_ids(self) -> list[str]:
        """Ids of the people the application is shared with by name, as its creator reads them."""
        return [
            item["id"]
            for item in self.creator.service.shared_with(self.app_id).shared_with
        ]

    def live_link_token(self) -> Optional[str]:
        link = self.creator.service.get_share_link(self.app_id).link
        return link.token if link else None


def shared_ids(answer: Any) -> list[str]:
    """User ids of a ``{"shared_with": [...]}`` answer."""
    return [item["id"] for item in answer.shared_with]


def activity_event(
    activity: ActivityUtils, app_id: str, event_type: str, **attributes: Any
):
    """The newest ``event_type`` event of the application whose attributes hold ``attributes``.

    Activity events are written asynchronously, so this polls; it returns None when no such
    event arrived in time.
    """

    def matching(page) -> list:
        return [
            event
            for event in page.data
            if all(
                (event.attributes or {}).get(key) == value
                for key, value in attributes.items()
            )
        ]

    page = poll_until(
        lambda: activity.list_activity_events(
            entity_id=app_id,
            event_type=[event_type],
            domain=[ACTIVITY_DOMAIN],
            sort_dir="desc",
        ),
        lambda listed: bool(matching(listed)),
        timeout=ACTIVITY_WAIT_SECONDS,
        interval=2.0,
    )
    found = matching(page)
    return found[0] if found else None
