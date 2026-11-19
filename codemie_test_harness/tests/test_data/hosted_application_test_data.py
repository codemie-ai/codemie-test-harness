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

"""Test data for the hosted application tests: artifacts built in memory, and the rejection table.

Nothing here touches the network. A test uploads what a builder returns and asserts what the
platform made of it.
"""

import hashlib
import io
import stat
import zipfile
from dataclasses import dataclass
from typing import Callable

from codemie_test_harness.tests.utils.base_utils import get_random_name

# The platform's own error code of a version that did not pass validation, and of an
# application that may not be opened.
HIDDEN_FROM_READER = 404
ACCOUNT_REFUSAL_CODE = "ACCOUNT_NOT_SUPPORTED"
SESSION_ENDED_STATUS = 401
APPLICATION_LIMIT_CODE = "APPLICATION_LIMIT"
UPLOAD_CONCURRENCY_LIMIT_CODE = "UPLOAD_CONCURRENCY_LIMIT"
CONFIGURATION_CONFLICT_CODE = "CONFIGURATION_CONFLICT"
INDEPENDENT_REVIEW_CODE = "INDEPENDENT_REVIEW_REQUIRED"
NOT_SUSPENDED_CODE = "NOT_SUSPENDED"
# What the content host answers for a path the version does not hold.
CONTENT_UNAVAILABLE_BODY = b"Application unavailable"
# The platform allows 4 open uploads and 500 applications per person.
MAX_OPEN_UPLOADS = 4
MAX_APPLICATIONS = 500


@dataclass(frozen=True)
class HostedArtifact:
    """A file to upload as a version: an HTML page or a ZIP."""

    filename: str
    kind: str
    content: bytes
    marker: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


def html_page(marker: str, body: str = "") -> str:
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>{marker}</title></head>"
        f'<body><h1 id="marker">{marker}</h1>{body}</body></html>'
    )


def html_artifact(marker: str | None = None, filename: str = "index.html"):
    """A single valid HTML page whose text carries a unique marker."""
    marker = marker or get_random_name()
    return HostedArtifact(filename, "html", html_page(marker).encode(), marker)


def build_zip(entries: list[tuple[zipfile.ZipInfo | str, bytes]]) -> bytes:
    """A ZIP with the given entries, in order; a name or a ready ``ZipInfo`` each."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        for entry, data in entries:
            bundle.writestr(entry, data)
    return buffer.getvalue()


def zip_artifact(
    entries: list[tuple[zipfile.ZipInfo | str, bytes]],
    marker: str | None = None,
    filename: str = "site.zip",
) -> HostedArtifact:
    return HostedArtifact(
        filename, "zip", build_zip(entries), marker or get_random_name()
    )


@dataclass(frozen=True)
class SpaBundle:
    """The file layout of a prebuilt single-page application."""

    id: str
    asset_paths: tuple[str, ...]
    script_tag: str


SPA_BUNDLES = [
    SpaBundle(
        id="vite-style",
        asset_paths=("assets/index-4f2a9c1e.js", "assets/index-7b1d3e8a.css"),
        script_tag='<script type="module" src="/assets/index-4f2a9c1e.js"></script>',
    ),
    SpaBundle(
        id="angular-style",
        asset_paths=("main.js", "styles.css"),
        script_tag='<script src="main.js" defer></script>',
    ),
]
# A page route of the application: no file extension, not a file of the bundle.
SPA_CLIENT_ROUTE = "/dashboard/settings"
SPA_MISSING_ASSET = "/assets/missing-chunk.js"


def spa_artifact(bundle: SpaBundle) -> HostedArtifact:
    marker = get_random_name()
    entries: list[tuple[zipfile.ZipInfo | str, bytes]] = [
        ("index.html", html_page(marker, bundle.script_tag).encode())
    ]
    for path in bundle.asset_paths:
        entries.append(
            (
                path,
                b"/* bundle file */"
                if path.endswith(".js")
                else b"body { margin: 0; }",
            )
        )
    return zip_artifact(entries, marker)


def two_root_zip() -> HostedArtifact:
    """A ZIP holding two sites: the owner has to choose which one is the application."""
    marker = get_random_name()
    return zip_artifact(
        [
            ("site-a/index.html", html_page(marker + "-a").encode()),
            ("site-b/index.html", html_page(marker + "-b").encode()),
        ],
        marker,
    )


def eicar_text() -> bytes:
    """The standard anti-malware test string, assembled at run time so no scanner flags the repository."""
    return (
        "X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + "EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    ).encode()


def _access_key_text() -> bytes:
    """A string shaped like a cloud access key id, assembled at run time."""
    return ("const key = '" + "AK" + "IA" + "QWERTYUIOPASDFGH" + "';").encode()


def malware_zip() -> HostedArtifact:
    return zip_artifact(
        [
            ("index.html", html_page("clean-page").encode()),
            ("assets/probe.js", eicar_text()),
        ]
    )


def secret_zip() -> HostedArtifact:
    return zip_artifact(
        [
            ("index.html", html_page("secret-page").encode()),
            ("config.js", _access_key_text()),
        ]
    )


def secret_value() -> str:
    """The credential-shaped value inside ``secret_zip`` that no report may repeat."""
    return _access_key_text().decode().split("'")[1]


def symlink_zip() -> HostedArtifact:
    link = zipfile.ZipInfo("link.html")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    return zip_artifact(
        [("index.html", html_page("link-page").encode()), (link, b"index.html")]
    )


def case_collision_zip() -> HostedArtifact:
    return zip_artifact(
        [
            ("Index.html", html_page("upper").encode()),
            ("index.html", html_page("lower").encode()),
        ]
    )


def unsafe_path_zip() -> HostedArtifact:
    return zip_artifact(
        [
            ("index.html", html_page("path-page").encode()),
            ("../outside.html", html_page("outside").encode()),
        ]
    )


def zip_bomb_zip() -> HostedArtifact:
    """A page plus one script that unpacks to far more than 100 times its packed size."""
    return zip_artifact(
        [
            ("index.html", html_page("bomb-page").encode()),
            ("assets/padding.js", b"a" * (8 * 1024 * 1024)),
        ]
    )


def server_code_zip() -> HostedArtifact:
    return zip_artifact(
        [
            ("index.html", html_page("server-page").encode()),
            ("server.py", b"print('not a browser file')"),
        ]
    )


@dataclass(frozen=True)
class InvalidUpload:
    id: str
    build: Callable[[], HostedArtifact]
    code: str


# Each code is the one the validator raises for that input; the guidance text of a code is fixed
# and never quotes the upload. An unsafe path is INVALID_ARCHIVE_PATH and an inflating archive is
# ARCHIVE_EXPANSION_LIMIT in the validator (the vocabulary also lists INVALID_PATH and ZIP_BOMB,
# which it does not raise for these inputs).
INVALID_UPLOADS = [
    InvalidUpload("malware", malware_zip, "MALWARE_DETECTED"),
    InvalidUpload("secret", secret_zip, "SECRET_DETECTED"),
    InvalidUpload("symlink-entry", symlink_zip, "UNSUPPORTED_ARCHIVE"),
    InvalidUpload("case-collision", case_collision_zip, "ARCHIVE_PATH_COLLISION"),
    InvalidUpload("unsafe-path", unsafe_path_zip, "INVALID_ARCHIVE_PATH"),
    InvalidUpload("inflating-archive", zip_bomb_zip, "ARCHIVE_EXPANSION_LIMIT"),
    InvalidUpload("server-code", server_code_zip, "UNSUPPORTED_ARTIFACT"),
]

PROBE_RESULT_ID = "probe-result"
STORAGE_KEY = "foreign-storage-key"


def probe_artifact(management_url: str) -> HostedArtifact:
    """A page whose script tries to reach out of its sandbox and writes each outcome into its own page."""
    marker = get_random_name()
    script = f"""
(function () {{
  var out = document.getElementById('{PROBE_RESULT_ID}');
  function report(name, value) {{ out.textContent += name + '=' + value + '\\n'; }}
  try {{ void window.parent.document.title; report('parent', 'reachable'); }}
  catch (e) {{ report('parent', 'blocked'); }}
  try {{ void window.top.document.title; report('top', 'reachable'); }}
  catch (e) {{ report('top', 'blocked'); }}
  report('cookie', document.cookie === '' ? 'none' : 'visible');
  try {{
    var seen = window.localStorage.getItem('{STORAGE_KEY}');
    report('foreign_storage', seen === null ? 'none' : 'visible');
  }} catch (e) {{ report('foreign_storage', 'none'); }}
  fetch('{management_url}')
    .then(function () {{ report('management_api', 'reachable'); }})
    .catch(function () {{ report('management_api', 'blocked'); }});
}})();
"""
    body = f'<pre id="{PROBE_RESULT_ID}"></pre><script>{script}</script>'
    return HostedArtifact(
        "probe.html", "html", html_page(marker, body).encode(), marker
    )


def storage_holder_artifact() -> HostedArtifact:
    """A page that keeps a value in its own local storage and says so."""
    marker = get_random_name()
    script = (
        f"window.localStorage.setItem('{STORAGE_KEY}', 'held');"
        "document.getElementById('holder-state').textContent = 'storage written';"
    )
    body = f'<p id="holder-state"></p><script>{script}</script>'
    return HostedArtifact(
        "holder.html", "html", html_page(marker, body).encode(), marker
    )


@dataclass(frozen=True)
class ReaderRequest:
    """One way a user without access tries to reach an application."""

    id: str
    call: Callable[[object, str], object]


# Each takes the hosted-application service of the user and the application id.
HIDDEN_REQUESTS = [
    ReaderRequest("metadata", lambda service, app_id: service.get_application(app_id)),
    ReaderRequest("thumbnail", lambda service, app_id: service.get_thumbnail(app_id)),
    ReaderRequest(
        "view-launch", lambda service, app_id: service.launch(app_id, "published_view")
    ),
    ReaderRequest(
        "preview-launch",
        lambda service, app_id: service.launch(app_id, "owner_preview"),
    ),
]
NOT_FOUND_CODE = "NOT_FOUND"


@dataclass(frozen=True)
class Revocation:
    """A way the owner takes access away from a recipient who already holds a viewing session.

    ``grant`` gives the recipient access, ``revoke`` takes it away; both take the owner, the
    recipient (both ``HostedUser``) and the application id.
    """

    id: str
    grant: Callable[[object, object, str], object]
    revoke: Callable[[object, object, str], object]


def _share_with(owner, recipient, app_id):
    return owner.service.share_with_users(app_id, [recipient.user_id])


REVOCATIONS = [
    Revocation(
        "unpublish",
        lambda owner, recipient, app_id: owner.apps.publish(app_id),
        lambda owner, recipient, app_id: owner.apps.unpublish(app_id),
    ),
    Revocation(
        "unshare",
        _share_with,
        lambda owner, recipient, app_id: owner.service.unshare(
            app_id, [recipient.user_id]
        ),
    ),
    Revocation(
        "delete",
        _share_with,
        lambda owner, recipient, app_id: owner.apps.delete_app(app_id),
    ),
]


@dataclass(frozen=True)
class PersonalLimit:
    """A per-person limit: the helper method that fills it, the refusal code and a part of its message."""

    id: str
    reach: str
    code: str
    message_part: str


PERSONAL_LIMITS = [
    PersonalLimit(
        "applications",
        "reach_application_limit",
        APPLICATION_LIMIT_CODE,
        f"{MAX_APPLICATIONS} applications",
    ),
    PersonalLimit(
        "open-uploads",
        "reach_upload_limit",
        UPLOAD_CONCURRENCY_LIMIT_CODE,
        f"{MAX_OPEN_UPLOADS} uploads in progress",
    ),
]


@dataclass(frozen=True)
class ScopeView:
    """What a user with only a named grant sees in one catalog scope: the suffixes of the names listed."""

    id: str
    scope: str
    visible: tuple[str, ...]


# The grantee sees the shared application only under "shared"; the private one nowhere.
GRANTEE_SCOPE_VIEWS = [
    ScopeView("mine", "mine", ()),
    ScopeView("project", "project", ()),
    ScopeView("marketplace", "marketplace", ()),
    ScopeView("shared", "shared", ("shared",)),
]


@dataclass(frozen=True)
class ContentRequest:
    """A kind of content request and the status its answer has."""

    id: str
    path: str
    method: str
    page: bool
    status: int


CONTENT_REQUESTS = [
    ContentRequest("entry-page", "/", "GET", True, 200),
    ContentRequest("missing-path", "/no-such-file.js", "GET", False, 404),
    ContentRequest("head-request", "/", "HEAD", True, 200),
]
CSP_DIRECTIVES = (
    "default-src 'none'",
    "connect-src 'self'",
    "frame-ancestors",
    "sandbox",
)
DENIED_FEATURES = (
    "camera=()",
    "microphone=()",
    "geolocation=()",
    "payment=()",
    "usb=()",
)
# The content origin may present itself full screen.
FULLSCREEN_DELEGATION = "fullscreen=(self)"
FIXED_CONTENT_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}
