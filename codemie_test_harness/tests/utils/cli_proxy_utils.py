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
Helpers for tests of the CodeMie CLI proxy daemon.

A test gets an isolated HOME / CODEMIE_HOME, a stub upstream that records what the
daemon forwards, and thin wrappers over the installed `codemie` command. Nothing here
touches the real home of the user running the tests or the daemon on the default port.
"""

import concurrent.futures
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional

import requests

from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)

DEFAULT_GATEWAY_KEY = "codemie-proxy"
PROFILE_NAME = "daemon-autotest"
PROJECT_NAME = "daemon-autotest-project"
PROFILE_MODEL = "gpt-5.2"
STREAM_PART_ONE = 'data: {"part":1}\n\n'
STREAM_PART_TWO = 'data: {"part":2}\n\n'
STREAM_ANSWER = STREAM_PART_ONE + STREAM_PART_TWO
MODEL_CATALOG = [
    {"deployment_name": "gpt-5-2-2026-01-15", "enabled": True},
    {"deployment_name": "claude-opus-4-5-20251101", "enabled": True},
]
MODEL_REQUEST_PATHS = ("/v1/messages", "/v1/responses", "/responses")

# Stores an SSO login for a URL with the CLI's own credential helpers, so the file
# store holds exactly what `codemie profile login` would leave there.
STORE_CREDENTIALS_SCRIPT = """
import { join } from 'node:path';
import { mkdirSync, writeFileSync } from 'node:fs';
const [pkg, codemieHome, url] = process.argv.slice(1);
const crypto = await import(join(pkg, 'dist/utils/credential-crypto.js'));
const credentials = { cookies: { codemie_access_token: 'daemon-autotest-cookie' }, apiUrl: url, expiresAt: 4102444800000 };
mkdirSync(join(codemieHome, 'credentials'), { recursive: true });
writeFileSync(
  join(codemieHome, 'credentials', crypto.deriveUrlStorageKey(url) + '.enc'),
  crypto.encryptWithKey(JSON.stringify(credentials), crypto.deriveMachineEncryptionKey())
);
"""

# What a Claude Code hook runs first: the daemon cold start, in a process of its own.
COLD_START_SCRIPT = """
const [pkg, agent, event] = process.argv.slice(1);
const { ensureOtlpProxy } = await import(pkg + '/dist/cli/commands/proxy/otlp-cold-start.js');
const { readState } = await import(pkg + '/dist/cli/commands/proxy/daemon-manager.js');
await ensureOtlpProxy(agent, event || undefined);
process.stdout.write('\\npid=' + (await readState()).pid + '\\n');
process.exit(0);
"""


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@dataclass
class RecordedRequest:
    method: str
    path: str
    headers: Dict[str, str]
    body: bytes

    @property
    def json(self):
        return json.loads(self.body.decode("utf-8")) if self.body else None

    @property
    def client(self) -> Optional[str]:
        return self.headers.get("x-codemie-client")


Responder = Callable[[RecordedRequest], Optional[tuple]]


class StubUpstream:
    """A local stand-in for the CodeMie API a profile's `baseUrl` points at."""

    def __init__(
        self,
        stream: bool = False,
        release_after_arrivals: int = 0,
        responder: Optional[Responder] = None,
    ):
        self.stream = stream
        self.release_after_arrivals = release_after_arrivals
        self.responder = responder
        self.requests: List[RecordedRequest] = []
        self.all_arrived = threading.Event()
        self.release = threading.Event()
        self.release.set()
        self._lock = threading.Lock()
        self._arrivals = 0
        self._open = 0
        self.peak_open = 0
        stub = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def _handle(self):
                length = int(self.headers.get("content-length") or 0)
                body = self.rfile.read(length) if length else b""
                request = RecordedRequest(
                    self.command,
                    self.path,
                    {k.lower(): v for k, v in self.headers.items()},
                    body,
                )
                with stub._lock:
                    stub.requests.append(request)
                if self.command == "GET" and self.path.startswith("/v1/llm_models"):
                    return self._send(200, json.dumps(MODEL_CATALOG).encode())
                answer = stub.responder(request) if stub.responder else None
                if answer:
                    return self._send(*answer)
                if (
                    stub.stream
                    and self.command == "POST"
                    and request.path in MODEL_REQUEST_PATHS
                ):
                    return self._stream()
                return self._send(200, b'{"ok":true}')

            def _send(
                self,
                status: int,
                payload: bytes,
                content_type: str = "application/json",
            ):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _chunk(self, text: str):
                data = text.encode()
                self.wfile.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
                self.wfile.flush()

            def _stream(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                self._chunk(STREAM_PART_ONE)
                with stub._lock:
                    stub._open += 1
                    stub.peak_open = max(stub.peak_open, stub._open)
                    stub._arrivals += 1
                    if (
                        stub.release_after_arrivals
                        and stub._arrivals >= stub.release_after_arrivals
                    ):
                        stub.all_arrived.set()
                if stub.release_after_arrivals:
                    stub.all_arrived.wait(15)
                stub.release.wait(60)
                with stub._lock:
                    stub._open -= 1
                self._chunk(STREAM_PART_TWO)
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()

            do_GET = do_POST = do_PUT = do_DELETE = _handle

        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def hold_streams(self) -> None:
        """Keep every stream open after its first part until `release_streams()`."""
        self.release.clear()

    def release_streams(self) -> None:
        self.release.set()

    def start(self) -> "StubUpstream":
        self._thread.start()
        return self

    def stop(self) -> None:
        self.release.set()
        self.all_arrived.set()
        self._server.shutdown()
        self._server.server_close()

    def model_requests(self, path: Optional[str] = None) -> List[RecordedRequest]:
        return [
            request
            for request in list(self.requests)
            if request.method == "POST"
            and request.path in MODEL_REQUEST_PATHS
            and (path is None or request.path == path)
        ]

    def wait_for_model_requests(self, count: int, timeout: float = 30) -> None:
        wait_until(
            lambda: len(self.model_requests()) >= count,
            timeout,
            f"{count} model request(s) at the stub",
        )


def completed_response_stream(request: "RecordedRequest") -> Optional[tuple]:
    """A finished Responses API stream for a model request, as the upstream of a Codex run answers it."""
    if request.method == "POST" and request.path.endswith("/responses"):
        event = {
            "type": "response.completed",
            "response": {
                "id": "resp-autotest",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "hello"}],
                    }
                ],
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            },
        }
        return (
            200,
            f"event: response.completed\ndata: {json.dumps(event)}\n\n".encode(),
            "text/event-stream",
        )
    return None


REPLAYED_REASONING_REJECTION = json.dumps(
    {"error": {"code": "invalid_encrypted_content", "message": "could not be verified"}}
).encode()


def reject_replayed_reasoning_once(client: str) -> Responder:
    """An upstream that rejects the first /v1/responses request of `client` as carrying reasoning it cannot decrypt."""
    seen: List[str] = []

    def responder(request: RecordedRequest) -> Optional[tuple]:
        if request.path == "/v1/responses" and request.client == client and not seen:
            seen.append(client)
            return 400, REPLAYED_REASONING_REJECTION
        return None

    return responder


def reported_pid(result: subprocess.CompletedProcess) -> Optional[int]:
    """The daemon pid a hook cold start printed on its own `pid=<n>` line."""
    match = re.search(r"^pid=(\d+)$", result.stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def wait_until(
    condition: Callable[[], bool], timeout: float, what: str, interval: float = 0.5
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(interval)
    raise AssertionError(f"Timed out after {timeout}s waiting for {what}")


def stays_true(
    condition: Callable[[], bool], duration: float, what: str, interval: float = 1.0
) -> None:
    """Assert `condition` holds at every check for `duration` seconds (a bounded observation, not a sleep)."""
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        if not condition():
            raise AssertionError(f"{what} did not hold for {duration}s")
        time.sleep(interval)


class CliProxyEnv:
    """An isolated CODEMIE_HOME and HOME with the installed `codemie` CLI and a stub upstream."""

    def __init__(self, root: Path, stub: StubUpstream, signed_in: bool = True):
        located = shutil.which("codemie")
        if located is None:
            raise AssertionError(
                "`codemie` is not on PATH: install @codemieai/code first"
            )
        self.codemie_bin = located
        self.package_dir = Path(os.path.realpath(located)).parent.parent
        self.home = root
        self.codemie_home = root / ".codemie"
        self.stub = stub
        self.port = free_port()
        self.profile = PROFILE_NAME
        self.project = PROJECT_NAME
        self.state_file = self.codemie_home / "proxy-daemon.json"
        self.record_file = self.codemie_home / "proxy-connection.json"
        self.codemie_home.mkdir(parents=True, exist_ok=True)
        self.write_config()
        self.write_record()
        if signed_in:
            self.store_credentials(stub.url)

    # ---- environment and commands -------------------------------------------------

    def env(self, path_prepend: Optional[Path] = None) -> Dict[str, str]:
        path = os.environ.get("PATH", "")
        return {
            "PATH": f"{path_prepend}{os.pathsep}{path}" if path_prepend else path,
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "CODEMIE_HOME": str(self.codemie_home),
            "CODEMIE_NO_PROMPTS": "1",
            "CODEMIE_AUTO_UPDATE": "false",
            "TERM": "dumb",
            "NO_COLOR": "1",
        }

    def popen(
        self, *args: str, path_prepend: Optional[Path] = None
    ) -> subprocess.Popen:
        return subprocess.Popen(
            list(args),
            cwd=self.home,
            env=self.env(path_prepend),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    def run(
        self, *args: str, timeout: int = 120, path_prepend: Optional[Path] = None
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            list(args),
            cwd=self.home,
            env=self.env(path_prepend),
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )

    def cli(
        self, *args: str, timeout: int = 120, path_prepend: Optional[Path] = None
    ) -> subprocess.CompletedProcess:
        return self.run(
            self.codemie_bin, *args, timeout=timeout, path_prepend=path_prepend
        )

    def node(
        self, script: str, *args: str, timeout: int = 120
    ) -> subprocess.CompletedProcess:
        return self.run(
            "node", "--input-type=module", "-e", script, "--", *args, timeout=timeout
        )

    def cold_start_args(
        self, event: str = "PostToolUse", agent: str = "claude-code-otlp"
    ) -> List[str]:
        return [
            "node",
            "--input-type=module",
            "-e",
            COLD_START_SCRIPT,
            "--",
            str(self.package_dir),
            agent,
            event,
        ]

    def cold_start(
        self, event: str = "PostToolUse", agent: str = "claude-code-otlp"
    ) -> subprocess.CompletedProcess:
        """What a Claude Code hook does first: bring the daemon up (or adopt it)."""
        return self.run(*self.cold_start_args(event, agent), timeout=90)

    def run_concurrently(
        self, *command_names: str
    ) -> List[subprocess.CompletedProcess]:
        """The named start commands launched at the same moment."""
        with concurrent.futures.ThreadPoolExecutor(len(command_names)) as pool:
            futures = [
                pool.submit(self.run_start_command, name) for name in command_names
            ]
            return [future.result() for future in futures]

    def post_in_background(
        self, path: str, bearer: str, body=None
    ) -> "concurrent.futures.Future":
        """A request left in flight; `.result()` is its response."""
        pool = concurrent.futures.ThreadPoolExecutor(1)
        future = pool.submit(self.post, path, bearer, body)
        pool.shutdown(wait=False)
        return future

    def post_concurrently(self, *calls: tuple) -> List[requests.Response]:
        """`(path, bearer, body)` requests sent at the same moment; the responses in the same order."""
        with concurrent.futures.ThreadPoolExecutor(len(calls)) as pool:
            futures = [pool.submit(self.post, *call) for call in calls]
            return [future.result() for future in futures]

    def prepare_daemon(self, before: str) -> Optional[dict]:
        """The daemon a case starts from: `none`, `running` (this CLI) or `older` (an older CLI's state)."""
        prepare = {
            "none": lambda: None,
            "running": self.start_daemon,
            "older": self.older_daemon,
        }
        return prepare[before]()

    def version(self) -> str:
        return self.cli("--version").stdout.strip().splitlines()[-1].strip()

    # ---- configuration -----------------------------------------------------------

    def write_config(
        self,
        project: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: str = "ai-run-sso",
        model: str = PROFILE_MODEL,
    ):
        url = base_url or self.stub.url
        config = {
            "version": 2,
            "activeProfile": self.profile,
            "profiles": {
                self.profile: {
                    "name": self.profile,
                    "provider": provider,
                    "authMethod": "sso",
                    "baseUrl": url,
                    "model": model,
                }
            },
            "codemieSkills": [],
            "codemieAssistants": [],
            "workspace": {"codeMieUrl": url, "codeMieProject": project or self.project},
        }
        (self.codemie_home / "codemie-cli.config.json").write_text(json.dumps(config))

    def add_profile(self, name: str) -> None:
        """A second profile on the same upstream, to name with `--profile`."""
        path = self.codemie_home / "codemie-cli.config.json"
        config = json.loads(path.read_text())
        config["profiles"][name] = {**config["profiles"][self.profile], "name": name}
        path.write_text(json.dumps(config))

    def write_record(self, **extra):
        """The connection record `proxy connect` leaves; `extra` carries an older CLI's identity fields."""
        record = {
            "version": 1,
            "profile": self.profile,
            "port": self.port,
            "updatedAt": "2026-01-01T00:00:00.000Z",
        }
        record.update(extra)
        self.record_file.write_text(json.dumps(record))

    def read_record(self) -> dict:
        return json.loads(self.record_file.read_text())

    def store_credentials(self, url: str) -> None:
        stored = self.node(
            STORE_CREDENTIALS_SCRIPT, str(self.package_dir), str(self.codemie_home), url
        )
        if stored.returncode != 0:
            raise AssertionError(f"Could not store credentials: {stored.stderr}")

    def write_sign_in_lock(self) -> None:
        """A browser sign-in already in progress, so no daemon request opens one."""
        (self.codemie_home / "sso-login.lock").write_text(
            json.dumps({"pid": os.getpid(), "startedAt": int(time.time() * 1000)})
        )

    # ---- daemon ------------------------------------------------------------------

    def state(self) -> Optional[dict]:
        try:
            return json.loads(self.state_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def write_state(self, **changes) -> dict:
        state = self.state()
        for key, value in changes.items():
            if value is None:
                state.pop(key, None)
            else:
                state[key] = value
        self.state_file.write_text(json.dumps(state, indent=2))
        return state

    def wait_for_state(
        self, condition: Callable[[dict], bool], timeout: float, what: str
    ) -> dict:
        wait_until(
            lambda: self.state() is not None and condition(self.state()), timeout, what
        )
        return self.state()

    def daemon_pids(self) -> List[str]:
        found = subprocess.run(
            ["pgrep", "-f", str(self.state_file)], capture_output=True, text=True
        )
        return [pid for pid in found.stdout.split() if pid]

    @property
    def gateway_key(self) -> str:
        return (self.state() or {}).get("gatewayKey", DEFAULT_GATEWAY_KEY)

    def bearer(self, client: Optional[str] = None) -> str:
        return self.gateway_key if client is None else f"{self.gateway_key}.{client}"

    def connect_omp(self, *extra: str) -> subprocess.CompletedProcess:
        return self.cli("proxy", "connect", "--omp", *extra)

    def start_daemon(self) -> dict:
        """A daemon of this CLI on the recorded port, started by `proxy connect` (which passes the profile model)."""
        result = self.connect_omp()
        if result.returncode != 0:
            raise AssertionError(
                f"proxy connect failed:\n{result.stdout}\n{result.stderr}"
            )
        return self.state()

    def older_daemon(self, **state_changes) -> dict:
        """A running daemon whose state names an older CLI, as one started before the upgrade does."""
        self.start_daemon()
        return self.write_state(version="0.0.1", **state_changes)

    def kill_daemon(self) -> None:
        pid = (self.state() or {}).get("pid")
        if pid:
            os.kill(pid, signal.SIGKILL)
            wait_until(lambda: not _alive(pid), 15, f"daemon {pid} to die")

    def run_start_command(self, command: str) -> subprocess.CompletedProcess:
        """One of the commands that can start or replace the daemon, by the name the cases use."""
        commands = {
            "hook": lambda: self.cold_start(),
            "hook cold start": lambda: self.cold_start(),
            "proxy start": lambda: self.cli("proxy", "start"),
            "proxy restart": lambda: self.cli("proxy", "restart"),
            "proxy connect": lambda: self.connect_omp(),
        }
        return commands[command]()

    def start_with_differing(self, differs: str) -> subprocess.CompletedProcess:
        """`proxy start` run after one thing was changed from what the running daemon was started with."""
        args = ["proxy", "start"]
        if differs == "profile":
            self.add_profile("other-profile")
            args += ["--profile", "other-profile"]
        elif differs == "project":
            self.write_config(project="other-project")
        elif differs == "provider":
            self.write_config(provider="bearer-auth")
        elif differs == "target URL":
            other_url = f"http://127.0.0.1:{free_port()}"
            self.write_config(base_url=other_url)
            self.store_credentials(other_url)
        elif differs == "port":
            args += ["--port", str(free_port())]
        return self.cli(*args)

    def make_git_repository(self) -> None:
        """Codex runs only inside a trusted (git) directory."""
        subprocess.run(
            ["git", "init", "-q", str(self.home)], check=True, capture_output=True
        )

    def cleanup(self) -> None:
        for pid in {(self.state() or {}).get("pid"), *map(int, self.daemon_pids())}:
            try:
                if pid:
                    os.kill(int(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

    # ---- requests ----------------------------------------------------------------

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def post(
        self,
        path: str,
        bearer: str,
        body=None,
        headers: Optional[dict] = None,
        timeout: int = 60,
    ):
        all_headers = {
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
            **(headers or {}),
        }
        return requests.post(
            self.url(path),
            data=json.dumps(body if body is not None else {}),
            headers=all_headers,
            timeout=timeout,
        )

    def status_output(self) -> str:
        return self.cli("proxy", "status", timeout=60).stdout

    # ---- client configs the daemon and `proxy status` read ------------------------

    def _vscode_user_dir(self, insiders: bool = False) -> Path:
        product = "Code - Insiders" if insiders else "Code"
        base = (
            self.home / "Library" / "Application Support"
            if _is_macos()
            else self.home / ".config"
        )
        return base / product / "User"

    def write_vscode_claude_code(
        self, port: int, key: str, insiders: bool = False
    ) -> Path:
        path = self._vscode_user_dir(insiders) / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "claudeCode.disableLoginPrompt": True,
                    "claudeCode.environmentVariables": [
                        {
                            "name": "ANTHROPIC_BASE_URL",
                            "value": f"http://127.0.0.1:{port}",
                        },
                        {"name": "ANTHROPIC_AUTH_TOKEN", "value": key},
                    ],
                },
                indent=2,
            )
        )
        return path

    def make_vscode_user_dir(self, insiders: bool = False) -> None:
        self._vscode_user_dir(insiders).mkdir(parents=True, exist_ok=True)

    def write_codex_config(self, port: int, key: str) -> Path:
        path = self.home / ".codex" / "config.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "# >>> codemie proxy connect (codex-desktop) header - managed block, do not edit",
                    'model_provider = "codemie"',
                    f'model = "{PROFILE_MODEL}"',
                    "# <<< codemie proxy connect (codex-desktop) header",
                    "",
                    "# >>> codemie proxy connect (codex-desktop) provider - managed block, do not edit",
                    "[model_providers.codemie]",
                    'name = "CodeMie"',
                    f'base_url = "http://127.0.0.1:{port}/v1"',
                    'wire_api = "responses"',
                    "[model_providers.codemie.http_headers]",
                    f'Authorization = "Bearer {key}"',
                    "# <<< codemie proxy connect (codex-desktop) provider",
                    "",
                ]
            )
        )
        return path

    @property
    def desktop_config_dir(self) -> Path:
        base = (
            self.home / "Library" / "Application Support"
            if _is_macos()
            else self.home / ".config"
        )
        return base / "Claude-3p" / "configLibrary"

    def write_desktop_gateway(self, port: int, key: str) -> None:
        """Claude Desktop's applied config, as the daemon reads it: configLibrary/_meta.json and <appliedId>.json."""
        applied_id = str(uuid.uuid4())
        self.desktop_config_dir.mkdir(parents=True, exist_ok=True)
        (self.desktop_config_dir / "_meta.json").write_text(
            json.dumps({"appliedId": applied_id, "entries": []})
        )
        (self.desktop_config_dir / f"{applied_id}.json").write_text(
            json.dumps(
                {
                    "inferenceProvider": "gateway",
                    "inferenceGatewayBaseUrl": f"http://127.0.0.1:{port}",
                    "inferenceGatewayApiKey": key,
                }
            )
        )

    def remove_desktop_gateway(self) -> None:
        shutil.rmtree(self.desktop_config_dir, ignore_errors=True)

    def write_cowork_session(self, cli_session_id: str, working_dir: Path) -> None:
        """Desktop's metadata file of a Cowork session, under its local-agent-mode root."""
        root = (
            self.desktop_config_dir.parent
            / "local-agent-mode-sessions"
            / "account"
            / "workspace"
        )
        root.mkdir(parents=True, exist_ok=True)
        now = int(time.time() * 1000)
        (root / f"local_{uuid.uuid4()}.json").write_text(
            json.dumps(
                {
                    "sessionId": f"local_{uuid.uuid4()}",
                    "cliSessionId": cli_session_id,
                    "cwd": str(working_dir),
                    "originCwd": str(working_dir),
                    "createdAt": now,
                    "lastActivityAt": now,
                }
            )
        )

    def write_desktop_session(
        self, short_id: str, cli_session_id: str, last_activity_ms: int, created_ms: int
    ) -> None:
        """A Claude Desktop (Cowork) session in the store: metadata, its audit transcript and the inner transcript."""
        base = (
            self.desktop_config_dir.parent
            / "local-agent-mode-sessions"
            / "account"
            / "workspace"
        )
        base.mkdir(parents=True, exist_ok=True)
        metadata = base / f"local_{short_id}-1111-4222-8333-444455556666.json"
        metadata.write_text(
            json.dumps(
                {
                    "sessionId": metadata.stem,
                    "cliSessionId": cli_session_id,
                    "createdAt": created_ms,
                    "lastActivityAt": last_activity_ms,
                    "model": "claude-opus-5",
                    "isArchived": False,
                }
            )
        )
        session_dir = base / short_id
        session_dir.mkdir(exist_ok=True)
        stamp = _seconds_ago
        (session_dir / "audit.jsonl").write_text(
            json.dumps(
                {
                    "type": "system",
                    "subtype": "init",
                    "session_id": cli_session_id,
                    "uuid": str(uuid.uuid4()),
                    "_audit_timestamp": stamp(60),
                }
            )
            + "\n"
        )
        inner = session_dir / ".claude" / "projects" / "session"
        inner.mkdir(parents=True, exist_ok=True)
        common = {
            "isSidechain": False,
            "sessionId": cli_session_id,
            "cwd": "/sessions/synthetic",
            "gitBranch": "HEAD",
            "entrypoint": "local-agent",
            "version": "2.1.317",
            "userType": "external",
        }
        lines = [
            {
                **common,
                "parentUuid": None,
                "uuid": str(uuid.uuid4()),
                "timestamp": stamp(60),
                "type": "user",
                "promptId": "p1",
                "message": {"role": "user", "content": "Draft a notes file"},
            },
            {
                **common,
                "parentUuid": None,
                "uuid": str(uuid.uuid4()),
                "timestamp": stamp(58),
                "type": "assistant",
                "message": {
                    "id": f"msg_{short_id}",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-opus-5",
                    "content": [{"type": "text", "text": "Done."}],
                    "stop_reason": "end_turn",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 40,
                        "cache_read_input_tokens": 1000,
                        "cache_creation_input_tokens": 200,
                        "cache_creation": {
                            "ephemeral_5m_input_tokens": 0,
                            "ephemeral_1h_input_tokens": 200,
                        },
                        "service_tier": "standard",
                    },
                },
            },
        ]
        (inner / f"{cli_session_id}.jsonl").write_text(
            "\n".join(json.dumps(line) for line in lines) + "\n"
        )

    def collected_session_dirs(self) -> List[str]:
        """The Desktop sessions the daemon has recorded, by the session directory each record names."""
        sessions = self.codemie_home / "sessions"
        found = []
        for record in sessions.glob("*.json") if sessions.exists() else []:
            try:
                found.append(json.loads(record.read_text()).get("workingDirectory", ""))
            except json.JSONDecodeError:
                continue
        return found

    def session_record(self, short_id: str) -> Optional[dict]:
        """The daemon's record of a collected Desktop session, or None."""
        sessions = self.codemie_home / "sessions"
        for record in sessions.glob("*.json") if sessions.exists() else []:
            try:
                data = json.loads(record.read_text())
            except json.JSONDecodeError:
                continue
            if f"local_{short_id}" in data.get("workingDirectory", ""):
                return data
        return None

    def is_session_collected(self, short_id: str) -> bool:
        return any(
            f"/{short_id}" in f"{directory}/" or f"local_{short_id}" in directory
            for directory in self.collected_session_dirs()
        )

    def append_desktop_session_message(
        self, cli_session_id: str, message_id: str
    ) -> None:
        """One more assistant line at the end of a Desktop session's inner transcript."""
        transcript = next(
            (self.desktop_config_dir.parent / "local-agent-mode-sessions").rglob(
                f"{cli_session_id}.jsonl"
            )
        )
        line = {
            "parentUuid": None,
            "isSidechain": False,
            "sessionId": cli_session_id,
            "cwd": "/sessions/synthetic",
            "gitBranch": "HEAD",
            "entrypoint": "local-agent",
            "version": "2.1.317",
            "userType": "external",
            "uuid": str(uuid.uuid4()),
            "timestamp": _seconds_ago(0),
            "type": "assistant",
            "message": {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5",
                "content": [{"type": "text", "text": "tail"}],
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": 7,
                    "output_tokens": 9,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "service_tier": "standard",
                },
            },
        }
        with transcript.open("a") as handle:
            handle.write(json.dumps(line) + "\n")

    def cowork_spool_text(self, cli_session_id: str) -> str:
        path = (
            self.codemie_home
            / "proxy"
            / "otlp-spool"
            / f"{cli_session_id}.hooks.ndjson"
        )
        return path.read_text() if path.exists() else ""

    def cowork_spool_sessions(self) -> List[str]:
        """The Cowork sessions that have events in the daemon's spool."""
        spool = self.codemie_home / "proxy" / "otlp-spool"
        return (
            sorted(path.name.split(".")[0] for path in spool.glob("*.hooks.ndjson"))
            if spool.exists()
            else []
        )

    def cowork_served_mark(self, cli_session_id: str) -> Path:
        return (
            self.codemie_home
            / "analytics"
            / "state"
            / f"{cli_session_id}.cowork-served"
        )

    def make_other_install(self, name: str, version: str) -> Path:
        """An install of @codemieai/code of another version: a package with a bin/codemie.js; returns its bin dir."""
        package = self.home / name / "node_modules" / "@codemieai" / "code"
        (package / "bin").mkdir(parents=True)
        (package / "package.json").write_text(
            json.dumps({"name": "@codemieai/code", "version": version})
        )
        script = package / "bin" / "codemie.js"
        script.write_text("#!/usr/bin/env node\n")
        script.chmod(0o755)
        bin_dir = self.home / name / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "codemie").symlink_to(script)
        return bin_dir

    def write_copilot_cli_hooks(self, script: Path) -> None:
        path = self.home / ".copilot" / "hooks" / "codemie-copilot-cli-hooks.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "exec": "node",
            "args": [
                str(script),
                "hook",
                "--agent",
                "copilot-cli-otlp",
                "--event",
                "sessionStart",
            ],
            "timeoutSec": 30,
        }
        path.write_text(json.dumps({"version": 1, "hooks": {"sessionStart": [entry]}}))


def _seconds_ago(offset: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() - offset))


def new_env_dir() -> Path:
    return Path(os.path.realpath(tempfile.mkdtemp(prefix="codemie_daemon_")))


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def is_alive(pid: int) -> bool:
    return _alive(pid)


def _is_macos() -> bool:
    return os.uname().sysname == "Darwin"
