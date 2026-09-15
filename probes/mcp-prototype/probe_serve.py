#!/usr/bin/env python3
"""M0 probe server: will Google AI Edge Gallery talk to a loopback MCP server?

This is a THROWAWAY probe, not `pocketkit`. Its only job is to answer validation
item V2 (and V4) from the design spec with evidence. It implements just enough of
MCP Streamable HTTP to be a real server, and logs every byte it receives so that a
failure can be diagnosed rather than guessed at.

The single most useful thing it produces is `probe-requests.log`. If Gallery fails
to connect and that file is EMPTY, the request never left the app -- client-side URL
validation or Android's cleartext-traffic policy. If it has entries, Gallery reached
us and disagreed about the protocol, which is a different and far more fixable
problem.

Usage:
    python3 probe_serve.py                 # bind 127.0.0.1:8765, generate a token
    python3 probe_serve.py --port 9000
    python3 probe_serve.py --host 0.0.0.0  # only for the tunnel diagnostic (step 5)
    python3 probe_serve.py --token abc123  # reuse a specific token

Standard library only. Python >= 3.11.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture"
LOG_PATH = HERE / "probe-requests.log"
TOKEN_PATH = HERE / ".probe-token"

# Revisions we are willing to speak. 2026-07-28 removed the GET stream endpoint and
# protocol-level sessions, which matches this server's stateless shape; the design
# spec (section 7.4) predates it and lists only the first three.
SUPPORTED_PROTOCOL_VERSIONS = [
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
    "2026-07-28",
]
NEWEST_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[-1]

SERVER_INFO = {"name": "pocketkit-probe", "version": "0.0.1-m0"}

INSTRUCTIONS = (
    "You are working inside the Obsidian vault 'PocketBrain'. "
    "Folders: 00-Inbox (human notes), 10-Drafts (your output), 20-Sources (read-only), "
    "30-Tasks, 40-Personas (read-only), 50-Skills (read-only), 99-Templates (read-only). "
    "Rules: read before you write; create new files only in 10-Drafts; edit only the section "
    "you were asked to change; stop after at most 6 tool calls and summarise what you changed. "
    "NOTE: this is the M0 probe server -- only vault_guide and vault_read exist, and both are "
    "read-only."
)

TOOLS = [
    {
        "name": "vault_guide",
        "description": (
            "Return the vault folder map and the rules governing where notes may be "
            "created and edited. Call this first, before any other vault tool."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "vault_read",
        "description": (
            "Read a note from the vault. Paths are relative to the vault root, "
            "for example '00-Inbox/idea-local-ai-lunch-and-learn.md'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Vault-relative path to the note, e.g. 'README.md'.",
                }
            },
            "required": ["path"],
        },
    },
]

_log_lock = threading.Lock()


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def log_event(kind: str, **fields) -> None:
    """Append one JSON line to probe-requests.log and echo a readable line to stdout."""
    record = {"time": _now(), "kind": kind, **fields}
    line = json.dumps(record, ensure_ascii=False)
    with _log_lock:
        try:
            with LOG_PATH.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError as exc:  # logging must never take the server down
            print("[warn] could not write log: {}".format(exc), file=sys.stderr)
    print("[{}] {}: {}".format(record["time"], kind, json.dumps(fields, ensure_ascii=False)[:600]),
          flush=True)


# --------------------------------------------------------------------------- tools


def _read_fixture(rel_path: str) -> str:
    """Read a file from the fixture vault, refusing anything outside it (spec rule P1)."""
    root = FIXTURE.resolve()
    target = (root / rel_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("path escapes the vault: {!r}".format(rel_path))
    if not target.is_file():
        raise FileNotFoundError("no such note: {}".format(rel_path))
    return target.read_text(encoding="utf-8")


def call_tool(name: str, arguments: dict) -> str:
    if name == "vault_guide":
        folders = sorted(p.name for p in FIXTURE.iterdir()) if FIXTURE.is_dir() else []
        return (
            "Vault: PocketBrain (M0 fixture)\n"
            "Folders: {}\n".format(", ".join(folders) or "(fixture missing)")
            + "Rules: AI creates only in 10-Drafts; 20-Sources, 40-Personas, 50-Skills and "
            "99-Templates are read-only; a human promotes drafts.\n"
            "This probe server is read-only: no note can be created or changed through it."
        )
    if name == "vault_read":
        path = arguments.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("vault_read requires a 'path' string argument")
        text = _read_fixture(path.strip())
        if len(text) > 4000:  # spec section 7.3, limits.read_chars
            text = text[:4000] + "\n\n[truncated at 4000 characters]"
        return text
    raise KeyError(name)


# ---------------------------------------------------------------------- dispatching


def rpc_error(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def rpc_result(req_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def negotiate(requested) -> str:
    """Echo the client's protocol version when we support it, else offer our newest."""
    if isinstance(requested, str) and requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return NEWEST_PROTOCOL_VERSION


def handle_message(msg: dict):
    """Return a JSON-RPC response dict, or None for a notification."""
    req_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}
    is_notification = "id" not in msg

    if not isinstance(method, str):
        return None if is_notification else rpc_error(req_id, -32600, "missing 'method'")

    if method == "initialize":
        requested = params.get("protocolVersion")
        agreed = negotiate(requested)
        log_event(
            "initialize",
            client_requested_version=requested,
            agreed_version=agreed,
            client_info=params.get("clientInfo"),
            client_capabilities=params.get("capabilities"),
        )
        return rpc_result(
            req_id,
            {
                "protocolVersion": agreed,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": INSTRUCTIONS,
            },
        )

    if method == "notifications/initialized":
        log_event("initialized_notification")
        return None

    if method.startswith("notifications/"):
        log_event("notification", method=method)
        return None

    if method == "ping":
        return rpc_result(req_id, {})

    if method == "tools/list":
        log_event("tools_list")
        return rpc_result(req_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        log_event("tools_call", tool=name, arguments=arguments)
        if not isinstance(name, str):
            return rpc_error(req_id, -32602, "tools/call requires a 'name'")
        try:
            text = call_tool(name, arguments)
        except KeyError:
            return rpc_error(req_id, -32602, "unknown tool: {}".format(name))
        except (ValueError, FileNotFoundError) as exc:
            # Tool-level failures are results with isError, not JSON-RPC errors --
            # the model is supposed to see and recover from them.
            return rpc_result(
                req_id,
                {"content": [{"type": "text", "text": str(exc)}], "isError": True},
            )
        except OSError as exc:
            return rpc_error(req_id, -32603, "internal error: {}".format(exc))
        return rpc_result(
            req_id,
            {"content": [{"type": "text", "text": text}], "isError": False},
        )

    return None if is_notification else rpc_error(req_id, -32601, "unknown method: {}".format(method))


# ------------------------------------------------------------------------- HTTP


class ProbeHandler(BaseHTTPRequestHandler):
    server_version = "pocketkit-probe/0.0.1"
    protocol_version = "HTTP/1.1"
    token = ""  # set on the class by main()

    def log_message(self, fmt, *args):  # quieter default access log; we do our own
        return

    # -- helpers ---------------------------------------------------------------

    def _send_json(self, status: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _authorised(self) -> bool:
        header = self.headers.get("Authorization", "")
        expected = "Bearer {}".format(self.token)
        # Constant-time compare: this token guards a vault.
        return secrets.compare_digest(header, expected)

    def _log_request_headers(self, verb: str, body=None) -> None:
        log_event(
            "http_request",
            verb=verb,
            path=self.path,
            client=self.client_address[0],
            headers=dict(self.headers.items()),
            body=body,
        )

    # -- verbs -----------------------------------------------------------------

    def do_GET(self):
        # Section 7.4: no SSE stream. 2026-07-28 removed the GET endpoint outright.
        self._log_request_headers("GET")
        self.send_response(405)
        self.send_header("Allow", "POST")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self):
        self._log_request_headers("DELETE")
        self._send_empty(405)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
        self._log_request_headers("POST", body=raw)

        if self.path.rstrip("/") not in ("/mcp", ""):
            self._send_json(404, {"error": "not found; the MCP endpoint is /mcp"})
            return

        if not self._authorised():
            log_event("auth_rejected", authorization=self.headers.get("Authorization"))
            self._send_json(
                401, rpc_error(None, -32600, "missing or invalid Authorization bearer token")
            )
            return

        if not raw.strip():
            self._send_json(400, rpc_error(None, -32700, "empty request body"))
            return

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._send_json(400, rpc_error(None, -32700, "parse error: {}".format(exc)))
            return

        # A batch is a JSON array; a single message is an object.
        if isinstance(msg, list):
            responses = [r for r in (handle_message(m) for m in msg) if r is not None]
            if not responses:
                self._send_empty(202)
            else:
                self._send_json(200, responses)
            return

        if not isinstance(msg, dict):
            self._send_json(400, rpc_error(None, -32600, "expected a JSON-RPC object"))
            return

        response = handle_message(msg)
        if response is None:
            self._send_empty(202)  # notification: accepted, no body
        else:
            self._send_json(200, response)


# ------------------------------------------------------------------------- main


def load_or_create_token(explicit) -> str:
    if explicit:
        return explicit
    if TOKEN_PATH.is_file():
        existing = TOKEN_PATH.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    token = secrets.token_hex(16)
    try:
        TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    except OSError:
        pass  # a non-persisted token still works for this run
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description="M0 MCP loopback probe server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    if not FIXTURE.is_dir():
        print("[warn] fixture vault missing at {}".format(FIXTURE), file=sys.stderr)

    ProbeHandler.token = load_or_create_token(args.token)
    httpd = ThreadingHTTPServer((args.host, args.port), ProbeHandler)

    url = "http://{}:{}/mcp".format(args.host, args.port)
    bar = "=" * 68
    print(bar)
    print("  M0 MCP probe server")
    print(bar)
    print("  URL     : {}".format(url))
    print("  Header  : Authorization: Bearer {}".format(ProbeHandler.token))
    print("  Log     : {}".format(LOG_PATH))
    print("  Speaks  : {}".format(", ".join(SUPPORTED_PROTOCOL_VERSIONS)))
    print("-" * 68)
    print("  In Gallery: Agent Chat > MCP > Add MCP server")
    print("    URL          {}".format(url))
    print("    Header name  Authorization")
    print("    Header value Bearer {}".format(ProbeHandler.token))
    print("-" * 68)
    print("  Ctrl-C to stop. Every request is logged above and to the log file.")
    print("  If Gallery fails AND the log stays empty, the request never left the app.")
    print(bar, flush=True)
    log_event("server_start", url=url, host=args.host, port=args.port)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping", flush=True)
        log_event("server_stop")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
