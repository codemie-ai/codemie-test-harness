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

# The five analytics clients `proxy status` lists, in its order, and the machine parts the cases install.
CLAUDE_CODE = "claude-code"
VSCODE_CLAUDE_CODE = "vscode-claude-code"
CLAUDE_DESKTOP = "claude-desktop"
COPILOT_CHAT = "copilot-chat"
COPILOT_CLI = "copilot-cli"
VSCODE = "vscode"
VSCODE_INSIDERS = "vscode-insiders"
ANALYTICS_CLIENTS = [
    CLAUDE_CODE,
    VSCODE_CLAUDE_CODE,
    CLAUDE_DESKTOP,
    COPILOT_CHAT,
    COPILOT_CLI,
]
ANALYTICS_LABELS = {
    CLAUDE_CODE: "Claude Code",
    VSCODE_CLAUDE_CODE: "VS Code Claude Code extension",
    CLAUDE_DESKTOP: "Claude Desktop",
    COPILOT_CHAT: "Copilot Chat",
    COPILOT_CLI: "Copilot CLI",
}
COPILOT_CONNECTOR_IDS = {
    COPILOT_CHAT: "copilot-chat-otlp",
    COPILOT_CLI: "copilot-cli-otlp",
}
CLAUDE_HOOK_MARKER = "hook --agent claude-code-otlp"
PROJECT_FILTER_ENV = "CODEMIE_ANALYTICS_PROJECT_FILTER"
OTHER_PROFILE_NAME = "other-profile"
# Daemon state fields that differ between two runs of the same commands.
DAEMON_STATE_VOLATILE_FIELDS = {
    "pid",
    "port",
    "url",
    "targetUrl",
    "syncCodeMieUrl",
    "startedAt",
    "lastHealthyAt",
}

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

    def __init__(
        self,
        root: Path,
        stub: StubUpstream,
        signed_in: bool = True,
        isolated_path: bool = False,
    ):
        located = shutil.which("codemie")
        if located is None:
            raise AssertionError(
                "`codemie` is not on PATH: install @codemieai/code first"
            )
        self.codemie_bin = located
        # With `isolated_path` the CLI sees only `node` and the system tools plus the binaries
        # a case installs with `install_binary`, so no client of the machine running the tests is found.
        self.isolated_path = isolated_path
        self.tools_dir = root / "tools-bin"
        # Extra variables for every command the env runs (e.g. CODEMIE_COPILOT_BIN).
        self.extra_env: Dict[str, str] = {}
        if isolated_path:
            self.tools_dir.mkdir(parents=True, exist_ok=True)
            node = shutil.which("node")
            if node is None:
                raise AssertionError("`node` is not on PATH")
            (self.tools_dir / "node").symlink_to(node)
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
        path = (
            os.pathsep.join(
                [str(self.tools_dir), "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
            )
            if self.isolated_path
            else os.environ.get("PATH", "")
        )
        return {
            "PATH": f"{path_prepend}{os.pathsep}{path}" if path_prepend else path,
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "CODEMIE_HOME": str(self.codemie_home),
            "CODEMIE_NO_PROMPTS": "1",
            "CODEMIE_AUTO_UPDATE": "false",
            "TERM": "dumb",
            "NO_COLOR": "1",
            **self.extra_env,
        }

    def install_binary(self, name: str) -> Path:
        """A stand-in executable `name` on the isolated PATH; the CLI only looks it up, it is never run."""
        binary = self.tools_dir / name
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
        return binary

    def remove_binary(self, name: str) -> None:
        (self.tools_dir / name).unlink()

    def make_executable(self, path: Path) -> Path:
        """An executable file at `path` (parents created), e.g. the target of CODEMIE_COPILOT_BIN."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
        return path

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

    def versionless_daemon(self) -> dict:
        """A running daemon whose state names no CLI version, as a daemon of a CLI before versions were recorded does."""
        self.start_daemon()
        return self.write_state(version=None)

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

    # ---- analytics clients: install, read back, compare -----------------------------

    def install_desktop_app(self) -> None:
        """Claude Desktop is installed: on macOS the CLI looks for `~/Applications/Claude.app` too."""
        if _is_macos():
            (self.home / "Applications" / "Claude.app").mkdir(
                parents=True, exist_ok=True
            )

    def install_clients(self, *clients: str) -> None:
        """Put the named client applications on the isolated machine (the names of `ANALYTICS_CLIENTS`)."""
        installers = {
            CLAUDE_CODE: lambda: self.install_binary("claude"),
            VSCODE: self.make_vscode_user_dir,
            VSCODE_INSIDERS: lambda: self.make_vscode_user_dir(insiders=True),
            CLAUDE_DESKTOP: self.install_desktop_app,
            COPILOT_CLI: lambda: self.install_binary("copilot"),
        }
        for client in clients:
            installers[client]()

    def change_machine(self, *changes: str) -> None:
        """Remove something from the machine after a connect, by the name the cases use."""
        actions = {
            "remove vscode": self.remove_vscode_user_dir,
            "remove claude binary": lambda: self.remove_binary("claude"),
            "remove copilot binary": lambda: self.remove_binary("copilot"),
            "remove desktop gateway": self.remove_desktop_gateway,
            "remove desktop app": lambda: shutil.rmtree(
                self.home / "Applications", ignore_errors=True
            ),
            "disconnect copilot cli": lambda: self.cli(
                "proxy", "disconnect", "--copilot-cli-otlp"
            ),
            "disconnect copilot chat": lambda: self.cli(
                "proxy", "disconnect", "--copilot-chat-otlp"
            ),
            "remove claude hooks": self.claude_settings_path.unlink,
        }
        for change in changes:
            actions[change]()

    @property
    def claude_settings_path(self) -> Path:
        return self.home / ".claude" / "settings.json"

    def claude_settings(self) -> dict:
        try:
            return json.loads(self.claude_settings_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def write_claude_settings(self, settings: dict) -> None:
        self.claude_settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.claude_settings_path.write_text(json.dumps(settings, indent=2))

    def claude_hooks_present(self) -> bool:
        return CLAUDE_HOOK_MARKER in json.dumps(self.claude_settings().get("hooks", {}))

    def set_tracked_projects(self, paths: List[str]) -> None:
        """Replace the stored list of tracked projects of Claude Code analytics."""
        settings = self.claude_settings()
        settings.setdefault("env", {})[PROJECT_FILTER_ENV] = json.dumps(paths)
        self.write_claude_settings(settings)

    def claude_project_filter(self) -> Optional[str]:
        """The stored list of tracked projects of Claude Code analytics, as the settings hold it (a JSON string)."""
        return self.claude_settings().get("env", {}).get(PROJECT_FILTER_ENV)

    def desktop_applied_config(self) -> Optional[dict]:
        """Claude Desktop's applied config (the file `_meta.json` names), or None."""
        try:
            applied = json.loads(
                (self.desktop_config_dir / "_meta.json").read_text()
            ).get("appliedId")
            return json.loads((self.desktop_config_dir / f"{applied}.json").read_text())
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            return None

    def vscode_settings_path(self, insiders: bool = False) -> Path:
        return self._vscode_user_dir(insiders) / "settings.json"

    def vscode_route(self, insiders: bool = False) -> Optional[dict]:
        """The extension's CodeMie route in an edition's settings.json: `{"url", "token"}`, or None."""
        try:
            settings = json.loads(self.vscode_settings_path(insiders).read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        variables = {
            entry.get("name"): entry.get("value")
            for entry in settings.get("claudeCode.environmentVariables", [])
        }
        if "ANTHROPIC_BASE_URL" not in variables:
            return None
        return {
            "url": variables["ANTHROPIC_BASE_URL"],
            "token": variables.get("ANTHROPIC_AUTH_TOKEN"),
        }

    def copilot_hook_file(self, client: str) -> Path:
        return {
            COPILOT_CHAT: self.codemie_home / "hooks" / "copilot-chat-hooks.json",
            COPILOT_CLI: self.home
            / ".copilot"
            / "hooks"
            / "codemie-copilot-cli-hooks.json",
        }[client]

    def copilot_scope(self, client: str) -> Optional[dict]:
        """The project scope record the CLI keeps for Copilot Chat or Copilot CLI, or None."""
        try:
            connectors = json.loads(
                (self.codemie_home / "copilot-connectors.json").read_text()
            )["connectors"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None
        return connectors.get(COPILOT_CONNECTOR_IDS[client])

    def configured_clients(self) -> List[str]:
        """The analytics clients whose config is on the machine, read from the files (not from `proxy status`)."""
        configured = {
            CLAUDE_CODE: self.claude_hooks_present(),
            VSCODE_CLAUDE_CODE: any(
                self.vscode_route(insiders) is not None for insiders in (False, True)
            ),
            CLAUDE_DESKTOP: (self.desktop_applied_config() or {}).get(
                "inferenceGatewayBaseUrl"
            )
            is not None,
            COPILOT_CHAT: self.copilot_hook_file(COPILOT_CHAT).exists(),
            COPILOT_CLI: self.copilot_hook_file(COPILOT_CLI).exists(),
        }
        return [client for client in ANALYTICS_CLIENTS if configured[client]]

    def connect_analytics(self, *flags: str) -> None:
        """`proxy connect <flags> --silent`, which must succeed; with no flag only a daemon is started."""
        if not flags:
            self.start_daemon()
            return
        result = self.cli("proxy", "connect", *flags, "--silent")
        if result.returncode != 0:
            raise AssertionError(
                f"proxy connect {' '.join(flags)} failed:\n{result.stdout}\n{result.stderr}"
            )

    def status_json(self) -> dict:
        """`proxy status --json` as a dict, whatever the CLI printed before the JSON."""
        output = self.cli("proxy", "status", "--json", timeout=60).stdout
        start = re.search(r"^\{", output, re.MULTILINE)
        return json.JSONDecoder().raw_decode(output[start.start() :])[0]

    def analytics_rows(self, status_text: str) -> List[str]:
        """The five client rows under `Analytics clients:` in `proxy status` text, trailing blanks removed."""
        lines = [line.rstrip() for line in status_text.splitlines()]
        start = lines.index("Analytics clients:")
        return lines[start + 1 : start + 1 + len(ANALYTICS_CLIENTS)]

    def tracked_projects(self, client: str) -> List[str]:
        """The named projects an analytics client tracks; an empty list means all projects."""
        if client == CLAUDE_CODE:
            return json.loads(self.claude_project_filter() or "[]")
        scope = self.copilot_scope(client) or {}
        return scope.get("paths", []) if scope.get("scope") == "project" else []

    def arrange(self, *kinds: str) -> None:
        """Set the machine up for a case, by the names the cases use: a member that fails, or a second profile."""
        arrangements = {
            "second profile": lambda: self.add_profile(OTHER_PROFILE_NAME),
            "claude conflict": lambda: self.write_claude_settings(
                {"env": {"OTEL_EXPORTER_OTLP_PROTOCOL": "grpc"}}
            ),
            "invalid project filter": lambda: self.write_claude_settings(
                {"env": {PROJECT_FILTER_ENV: "not-a-json-list"}}
            ),
            "desktop without url": self.remove_codemie_url,
            "copilot chat settings": lambda: self.vscode_settings_path().write_text(
                "{ not json"
            ),
        }
        for kind in kinds:
            arrangements[kind]()

    def remove_codemie_url(self) -> None:
        """A profile with no CodeMie URL: Claude Desktop cannot be configured under it."""
        path = self.codemie_home / "codemie-cli.config.json"
        config = json.loads(path.read_text())
        config["workspace"].pop("codeMieUrl")
        path.write_text(json.dumps(config))

    def point_copilot_bin_at(self, kind: str) -> None:
        """Set CODEMIE_COPILOT_BIN for every command of this env, by the kind of path the cases use."""
        custom = self.home / "custom"
        paths = {
            "existing absolute": lambda: str(self.make_executable(custom / "copilot")),
            "existing relative": lambda: (
                self.make_executable(custom / "copilot") and "./custom/copilot"
            ),
            "missing absolute": lambda: str(custom / "missing-copilot"),
            "missing relative": lambda: "./custom/missing-copilot",
        }
        self.extra_env["CODEMIE_COPILOT_BIN"] = paths[kind]()

    def config_snapshot(self) -> dict:
        """What the connect commands left of the analytics clients, with this env's ports, home, ids and times masked."""
        files = {
            "claude settings": self.claude_settings_path,
            "vscode settings": self.vscode_settings_path(),
            "vscode insiders settings": self.vscode_settings_path(insiders=True),
            "copilot connectors": self.codemie_home / "copilot-connectors.json",
            "copilot chat hooks": self.copilot_hook_file(COPILOT_CHAT),
            "copilot cli hooks": self.copilot_hook_file(COPILOT_CLI),
            "connection record": self.record_file,
        }
        snapshot = {
            name: self.mask(path.read_text()) if path.exists() else None
            for name, path in files.items()
        }
        desktop = self.desktop_applied_config()
        snapshot["desktop applied config"] = (
            self.mask(json.dumps(desktop, sort_keys=True)) if desktop else None
        )
        state = self.state() or {}
        snapshot["daemon state"] = {
            key: self.mask(json.dumps(value))
            for key, value in state.items()
            if key not in DAEMON_STATE_VOLATILE_FIELDS
        }
        return snapshot

    def mask(self, text: str) -> str:
        """`text` with this env's home, ports, ids and times replaced by placeholders, so two envs' output compares."""
        text = text.replace(str(self.home), "<home>")
        text = re.sub(r"127\.0\.0\.1:\d+", "127.0.0.1:<port>", text)
        text = re.sub(r'("port": )\d+', r"\1<port>", text)
        text = re.sub(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", "<uuid>", text)
        return re.sub(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z", "<time>", text)

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

    def remove_vscode_user_dir(self, insiders: bool = False) -> None:
        """VS Code (or Insiders) is gone from the machine: its whole user-data directory."""
        shutil.rmtree(self._vscode_user_dir(insiders).parent, ignore_errors=True)

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


def output_of(result: subprocess.CompletedProcess) -> str:
    """What a command printed, both streams: the CLI prints its failure lines to either."""
    return f"{result.stdout}\n{result.stderr}"


def lines_of(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines()]


def one_line(text: str) -> str:
    """`text` with every run of whitespace, line breaks included, as one space: help output wraps at its own width."""
    return " ".join(text.split())


def line_starting_with(text: str, prefix: str) -> str:
    """The first line of `text` that starts with `prefix`; fails naming the prefix when there is none."""
    for line in text.splitlines():
        if line.startswith(prefix):
            return line
    raise AssertionError(f"No line starts with: {prefix}")


def row_values(rows: List[str]) -> Dict[str, str]:
    """`{label: value}` of client rows of `proxy status`."""
    split = [row.strip().split(":", 1) for row in rows]
    return {label: value.strip() for label, value in split}


def status_row(label: str, value: str) -> str:
    """A client row of `proxy status` as printed: two spaces, the label and colon padded to 32 columns, then the value."""
    return f"  {label + ':':<32}{value}"


def command_named_by(row_value: str) -> List[str]:
    """The `codemie proxy connect ...` arguments a status row names, without the leading `codemie`."""
    match = re.search(r"(?:Run|run): (codemie proxy connect .+)$", row_value)
    if match is None:
        raise AssertionError(f"No command is named in: {row_value}")
    return match.group(1).split()[1:]


def nearest_heading(text: str, needle: str, prefix: str = "### ") -> Optional[str]:
    """The last `prefix` heading above the first line of `text` that holds `needle`."""
    heading = None
    for line in text.splitlines():
        if line.startswith(prefix):
            heading = line
        if needle in line:
            return heading
    return None


def desktop_app_can_be_absent() -> bool:
    """Whether a case can leave Claude Desktop uninstalled: only macOS looks for the app, in two fixed places."""
    return _is_macos() and not Path("/Applications/Claude.app").exists()


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
