"""
Smoke test for OpenSpace MCP streamable-http integration.

Level 1: Direct MCP protocol (initialize + tools/list + tools/call search_skills)
Level 2: Via IronClaw extension status check

Usage:
    python smoke_test_mcp.py
    python smoke_test_mcp.py --level 2 --ironclaw-token <token>
"""

import argparse
import json
import sys

import httpx

MCP_URL = "http://127.0.0.1:8789/mcp"
IC_URL = "http://127.0.0.1:3231"

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"


def _parse_mcp_response(resp: httpx.Response) -> dict:
    ct = resp.headers.get("content-type", "")
    if "text/event-stream" in ct:
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return {"raw": resp.text[:500]}
    return resp.json()


def _extract_tool_error_text(response: dict) -> str | None:
    if "error" in response:
        error = response["error"]
        if isinstance(error, dict):
            return json.dumps(error)
        return str(error)

    content = response.get("result", {}).get("content", [])
    if not content:
        return None

    text = content[0].get("text", "")
    if not text:
        return None

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    error = payload.get("error")
    if error is None:
        return None
    if isinstance(error, str):
        return error
    return json.dumps(error)


def mcp_rpc(client: httpx.Client, method: str, params: dict | None = None, id: int = 1, session_id: str | None = None) -> tuple[dict, str | None]:
    body: dict = {"jsonrpc": "2.0", "id": id, "method": method}
    if params:
        body["params"] = params
    headers = dict(MCP_HEADERS)
    if session_id:
        headers["mcp-session-id"] = session_id
    resp = client.post(MCP_URL, json=body, headers=headers)
    resp.raise_for_status()
    new_session_id = resp.headers.get("mcp-session-id", session_id)
    return _parse_mcp_response(resp), new_session_id


def run_level1():
    ok = True
    session_id: str | None = None
    print("\n=== Level 1: Direct MCP protocol ===")

    with httpx.Client(timeout=15) as client:
        # ── initialize ───────────────────────────────────────────────────────
        try:
            r, session_id = mcp_rpc(client, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke-test", "version": "1.0"},
            })
            server_name = r.get("result", {}).get("serverInfo", {}).get("name", "?")
            proto = r.get("result", {}).get("protocolVersion", "?")
            print(f"  {PASS} initialize  server={server_name!r}  protocolVersion={proto!r}  session={session_id!r}")
        except Exception as e:
            print(f"  {FAIL} initialize failed: {e}")
            return False

        # ── tools/list ───────────────────────────────────────────────────────
        try:
            r2, _ = mcp_rpc(client, "tools/list", id=2, session_id=session_id)
            tools = r2.get("result", {}).get("tools", [])
            names = [t["name"] for t in tools]
            print(f"  {PASS} tools/list  count={len(tools)}")
            for n in names:
                print(f"         • {n}")
            if not names:
                print(f"  {FAIL} No tools returned")
                ok = False
        except Exception as e:
            print(f"  {FAIL} tools/list failed: {e}")
            ok = False

        # ── tools/call  search_skills (tools on the server use un-prefixed names) ──
        try:
            r3, _ = mcp_rpc(client, "tools/call", {
                "name": "search_skills",
                "arguments": {"query": "smoke test", "source": "local"},
            }, id=3, session_id=session_id)
            error_text = _extract_tool_error_text(r3)
            content = r3.get("result", {}).get("content", [])
            text = content[0].get("text", "") if content else ""
            short = text[:120].replace("\n", " ")
            if error_text:
                print(f"  {FAIL} tools/call search_skills returned tool error: {error_text}")
                ok = False
            else:
                print(f"  {PASS} tools/call search_skills → {short!r}…")
        except Exception as e:
            print(f"  {FAIL} tools/call search_skills failed: {e}")
            ok = False

    return ok


def run_level2(token: str):
    ok = True
    print("\n=== Level 2: IronClaw extension status ===")
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=10) as client:
        try:
            r = client.get(f"{IC_URL}/api/extensions", headers=headers)
            r.raise_for_status()
            exts = r.json().get("extensions", [])
            openspace = next((e for e in exts if e.get("name") == "openspace"), None)
            if not openspace:
                print(f"  {FAIL} openspace extension not found in IronClaw")
                return False
            active = openspace.get("active", False)
            tools = openspace.get("tools", [])
            url = openspace.get("url", "")
            status = PASS if active else FAIL
            print(f"  {status} openspace  active={active}  url={url}")
            print(f"  {PASS if tools else FAIL} tools  count={len(tools)}")
            for t in tools:
                print(f"         • {t}")
        except Exception as e:
            print(f"  {FAIL} IronClaw extensions API failed: {e}")
            ok = False

    return ok


def main():
    parser = argparse.ArgumentParser(description="OpenSpace MCP smoke test")
    parser.add_argument("--level", type=int, choices=[1, 2], default=1)
    parser.add_argument("--ironclaw-token", default=None, help="IronClaw auth token for level 2")
    args = parser.parse_args()

    passed = True
    passed = run_level1() and passed
    if args.level >= 2:
        if not args.ironclaw_token:
            print("\n[!] Pass --ironclaw-token for level 2")
        else:
            passed = run_level2(args.ironclaw_token) and passed

    print()
    if passed:
        print(f"{PASS} All checks passed")
        sys.exit(0)
    else:
        print(f"{FAIL} Some checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
