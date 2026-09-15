#!/usr/bin/env python3
"""Tests for the M0 MCP probe server.

Standard library only, so this runs anywhere the probe itself runs -- Windows,
Termux, a-Shell. The point is to prove the protocol is correct BEFORE it meets
the phone, so that a Gallery failure can be blamed on Gallery.

    python3 test_probe_serve.py          # or: python3 -m unittest -v
"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import probe_serve as ps

TOKEN = "test-token-0123456789"


def rpc(method: str, params=None, req_id=1):
    msg = {"jsonrpc": "2.0", "method": method}
    if req_id is not None:
        msg["id"] = req_id
    if params is not None:
        msg["params"] = params
    return msg


class TestNegotiation(unittest.TestCase):
    def test_echoes_every_supported_version(self):
        for version in ps.SUPPORTED_PROTOCOL_VERSIONS:
            with self.subTest(version=version):
                self.assertEqual(ps.negotiate(version), version)

    def test_includes_the_2026_revision(self):
        # The design spec (7.4) predates it; the probe must not.
        self.assertIn("2026-07-28", ps.SUPPORTED_PROTOCOL_VERSIONS)

    def test_unknown_version_falls_back_to_newest(self):
        for bad in ["1999-01-01", "", None, 7, {"a": 1}]:
            with self.subTest(bad=bad):
                self.assertEqual(ps.negotiate(bad), ps.NEWEST_PROTOCOL_VERSION)


class TestDispatch(unittest.TestCase):
    def test_initialize_returns_capabilities_and_instructions(self):
        res = ps.handle_message(rpc("initialize", {"protocolVersion": "2025-06-18"}))
        result = res["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertIn("tools", result["capabilities"])
        self.assertIn("10-Drafts", result["instructions"])
        self.assertEqual(result["serverInfo"]["name"], "pocketkit-probe")

    def test_initialized_notification_has_no_response(self):
        msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self.assertIsNone(ps.handle_message(msg))

    def test_ping(self):
        self.assertEqual(ps.handle_message(rpc("ping"))["result"], {})

    def test_tools_list_shape(self):
        tools = ps.handle_message(rpc("tools/list"))["result"]["tools"]
        self.assertEqual({t["name"] for t in tools}, {"vault_guide", "vault_read"})
        for tool in tools:
            with self.subTest(tool=tool["name"]):
                self.assertTrue(tool["description"])
                self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_unknown_method_is_an_error(self):
        res = ps.handle_message(rpc("does/not/exist"))
        self.assertEqual(res["error"]["code"], -32601)

    def test_unknown_notification_is_swallowed(self):
        msg = {"jsonrpc": "2.0", "method": "notifications/cancelled"}
        self.assertIsNone(ps.handle_message(msg))


class TestToolCalls(unittest.TestCase):
    def _call(self, name, arguments=None):
        return ps.handle_message(
            rpc("tools/call", {"name": name, "arguments": arguments or {}})
        )

    def test_vault_guide(self):
        result = self._call("vault_guide")["result"]
        self.assertFalse(result["isError"])
        self.assertIn("10-Drafts", result["content"][0]["text"])

    def test_vault_read(self):
        result = self._call("vault_read", {"path": "README.md"})["result"]
        self.assertFalse(result["isError"])
        self.assertIn("PocketBrain", result["content"][0]["text"])

    def test_vault_read_nested_path(self):
        result = self._call(
            "vault_read", {"path": "00-Inbox/idea-local-ai-lunch-and-learn.md"}
        )["result"]
        self.assertFalse(result["isError"])
        self.assertIn("lunch-and-learn", result["content"][0]["text"].lower())

    def test_missing_file_is_a_tool_error_not_a_protocol_error(self):
        # The model needs to see this and recover, so it must be isError, not a
        # JSON-RPC error object.
        res = self._call("vault_read", {"path": "00-Inbox/nope.md"})
        self.assertNotIn("error", res)
        self.assertTrue(res["result"]["isError"])

    def test_path_traversal_is_refused(self):
        for bad in ["../probe_serve.py", "../../README.md", "00-Inbox/../../probe_serve.py"]:
            with self.subTest(path=bad):
                res = self._call("vault_read", {"path": bad})
                self.assertTrue(res["result"]["isError"], "traversal not refused: " + bad)

    def test_missing_path_argument(self):
        self.assertTrue(self._call("vault_read")["result"]["isError"])

    def test_unknown_tool(self):
        res = self._call("vault_create", {"title": "x"})
        self.assertEqual(res["error"]["code"], -32602)


class TestHttp(unittest.TestCase):
    """Exercise the real socket path: auth, verbs, status codes."""

    @classmethod
    def setUpClass(cls):
        ps.ProbeHandler.token = TOKEN
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), ps.ProbeHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def url(self, path="/mcp"):
        return "http://127.0.0.1:{}{}".format(self.port, path)

    def post(self, payload, token=TOKEN, path="/mcp"):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url(path), data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if token is not None:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, (json.loads(body) if body else None)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            return exc.code, (json.loads(body) if body else None)

    def test_full_lifecycle(self):
        status, res = self.post(rpc("initialize", {"protocolVersion": "2025-11-25"}))
        self.assertEqual(status, 200)
        self.assertEqual(res["result"]["protocolVersion"], "2025-11-25")

        status, body = self.post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertEqual(status, 202)
        self.assertIsNone(body)

        status, res = self.post(rpc("tools/list", req_id=2))
        self.assertEqual(status, 200)
        self.assertEqual(len(res["result"]["tools"]), 2)

        status, res = self.post(
            rpc("tools/call", {"name": "vault_guide", "arguments": {}}, req_id=3)
        )
        self.assertEqual(status, 200)
        self.assertEqual(res["id"], 3)
        self.assertFalse(res["result"]["isError"])

    def test_missing_token_is_401(self):
        status, _ = self.post(rpc("ping"), token=None)
        self.assertEqual(status, 401)

    def test_wrong_token_is_401(self):
        status, _ = self.post(rpc("ping"), token="not-the-token")
        self.assertEqual(status, 401)

    def test_wrong_path_is_404(self):
        status, _ = self.post(rpc("ping"), path="/nope")
        self.assertEqual(status, 404)

    def test_get_is_405_with_allow_header(self):
        req = urllib.request.Request(self.url(), method="GET")
        req.add_header("Authorization", "Bearer " + TOKEN)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(ctx.exception.code, 405)
        self.assertEqual(ctx.exception.headers.get("Allow"), "POST")

    def test_malformed_json_is_a_parse_error(self):
        req = urllib.request.Request(self.url(), data=b"{not json", method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "Bearer " + TOKEN)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(ctx.exception.code, 400)
        self.assertEqual(json.loads(ctx.exception.read())["error"]["code"], -32700)

    def test_batch_request(self):
        status, res = self.post([rpc("ping", req_id=10), rpc("tools/list", req_id=11)])
        self.assertEqual(status, 200)
        self.assertEqual({r["id"] for r in res}, {10, 11})


if __name__ == "__main__":
    unittest.main(verbosity=2)
