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

"""Test data for the hosted application UI tests."""

from dataclasses import dataclass

# What the probe page of the sandbox test writes when nothing escapes: one line per attempt, in
# the order the page makes them. The report is compared with whitespace normalised.
PROBE_REPORT_LINES = (
    "parent=blocked",
    "top=blocked",
    "cookie=none",
    "foreign_storage=none",
    "management_api=blocked",
)
PROBE_REPORT = " ".join(PROBE_REPORT_LINES)
# What the page that keeps a value in its own storage says once it has done so.
HOLDER_WRITTEN_TEXT = "storage written"
# The probe page reaches the management API of the stand by this route.
MANAGEMENT_ROUTE = "/v1/hosted-applications/capabilities"

# Sharing by the app's managers. Texts of the share dialog and the details page.
SHARE_MENU_ITEM = "Share"
SUSPEND_MENU_ITEM = "Suspend"
REVOKE_LINK_MENU_ITEM = "Revoke share link"
SEARCH_EMPTY_TEXT = "Type to search users"
SHARING_UPDATED_TOAST = "Application sharing updated."
USER_REMOVED_TOAST = "User removed from application sharing."
LINK_COPIED_TOAST = "Share link copied to clipboard"
# VERIFY: not walked live; texts of the frontend's ShareLinkSection.
LINK_REVOKED_TOAST = "Share link revoked"
REVOKE_LINK_CONFIRMATION = "Revoke the share link?"
# The copied link opens the share route of the Applications area with the link's token.
SHARE_LINK_ROUTE = "/apps/share/"
CLIPBOARD_PERMISSIONS = ["clipboard-read", "clipboard-write"]
NON_MANAGER_HINT = "Only signed-in members of your organization can open it."
CREATOR_PRIVATE_HINT = "Only you can open this link until you share it."
MANAGER_PRIVATE_HINT = (
    "Only people who manage it can open this link until it is shared."
)


@dataclass(frozen=True)
class HostedSharingView:
    """The person the browser signs in as, and the application they look at.

    ``role`` is a ``SharingWorld`` role; ``shared`` is the application's "Shared with project"
    switch; ``collection`` is the Applications tab that lists the application for the person;
    ``hint`` is the access hint the details page shows them.
    """

    id: str
    role: str
    shared: bool = True
    collection: str = "project"
    hint: str = ""


SHARE_MANAGER_VIEWS = [
    HostedSharingView("project_admin", "project_admin"),
    HostedSharingView("platform_admin", "platform_admin"),
]
MODERATOR_VIEWS = [HostedSharingView("platform_admin", "platform_admin")]
SHARE_DIALOG_VIEWS = [HostedSharingView("project_admin", "project_admin")]
NON_MANAGER_VIEWS = [
    HostedSharingView("project_member", "project_member", hint=NON_MANAGER_HINT),
    HostedSharingView(
        "named_grantee",
        "named_grantee",
        shared=False,
        collection="shared",
        hint=NON_MANAGER_HINT,
    ),
]
PRIVATE_APP_HINT_VIEWS = [
    HostedSharingView("creator", "creator", shared=False, hint=CREATOR_PRIVATE_HINT),
    HostedSharingView(
        "project_admin", "project_admin", shared=False, hint=MANAGER_PRIVATE_HINT
    ),
]
