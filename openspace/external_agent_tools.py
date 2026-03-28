from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List

from openspace.external_agent_gateway import (
    ExternalAgentGatewayError,
    get_external_agent_history,
    handoff_external_agent,
)
from openspace.external_agents import get_external_agent, get_external_agents_status
from openspace.grounding.core.tool.local_tool import LocalTool
from openspace.grounding.core.types import BackendType


ACTIVE_EXTERNAL_STATES = {
    "accepted",
    "pending",
    "queued",
    "processing",
    "running",
    "in_progress",
}


class ListExternalAgentsTool(LocalTool):
    _name = "list_external_agents"
    _description = (
        "List configured external agents, their availability, protocol, and delegation "
        "capabilities. Use this before delegating if you do not know the agent id."
    )
    backend_type = BackendType.SYSTEM

    async def _arun(self, available_only: bool = False, require_handoff: bool = False) -> str:
        items = await asyncio.to_thread(get_external_agents_status)
        if require_handoff:
            items = [item for item in items if item.get("supportsHandoff")]
        if available_only:
            items = [item for item in items if item.get("available")]

        payload = {
            "count": len(items),
            "items": items,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


class DelegateExternalAgentTool(LocalTool):
    _name = "delegate_external_agent"
    _description = (
        "Delegate a subtask to a configured external agent. Provide the configured agent_id "
        "and a self-contained prompt. Optionally wait for the delegated run to finish and "
        "return the latest response."
    )
    backend_type = BackendType.SYSTEM

    async def _arun(
        self,
        agent_id: str,
        prompt: str,
        thread_id: str = "",
        timezone: str = "UTC",
        wait_for_completion: bool = True,
        history_limit: int = 10,
        poll_interval_seconds: float = 4.0,
        timeout_seconds: float = 90.0,
    ) -> str:
        agent = get_external_agent(agent_id)
        if not agent:
            raise ValueError(f"Unknown external agent: {agent_id}")

        try:
            result = await asyncio.to_thread(
                handoff_external_agent,
                agent,
                prompt=prompt,
                thread_id=thread_id or None,
                timezone=timezone,
                history_limit=history_limit,
            )
        except ExternalAgentGatewayError as exc:
            raise ValueError(str(exc)) from exc

        payload = dict(result)
        payload["protocol"] = agent.get("protocol")
        payload["capabilities"] = agent.get("capabilities", [])
        payload["completed"] = not _response_is_active(payload)
        payload["timedOut"] = False
        payload["pollCount"] = 0
        payload["latestResponse"] = _extract_latest_response(payload)

        if wait_for_completion and agent.get("supportsHistory") and _response_is_active(payload):
            start = time.monotonic()
            while (time.monotonic() - start) < max(timeout_seconds, 1.0):
                await asyncio.sleep(max(poll_interval_seconds, 0.5))
                refreshed = await asyncio.to_thread(
                    get_external_agent_history,
                    agent,
                    thread_id=str(payload.get("threadId") or ""),
                    limit=history_limit,
                )
                payload.update(refreshed)
                payload["pollCount"] = int(payload.get("pollCount", 0)) + 1
                payload["latestResponse"] = _extract_latest_response(payload)
                if not _response_is_active(payload):
                    payload["completed"] = True
                    break
            else:
                payload["completed"] = False
                payload["timedOut"] = True
        elif wait_for_completion and not agent.get("supportsHistory"):
            payload["warning"] = (
                f"External agent '{agent_id}' does not support history polling; "
                "returning the initial handoff result only."
            )

        return json.dumps(payload, ensure_ascii=False, indent=2)


class GetExternalAgentHistoryTool(LocalTool):
    _name = "get_external_agent_history"
    _description = (
        "Refresh the state and recent history for an external-agent thread. Use this when a "
        "delegated run is still pending or when you want the latest response for a thread id."
    )
    backend_type = BackendType.SYSTEM

    async def _arun(self, agent_id: str, thread_id: str, limit: int = 10) -> str:
        agent = get_external_agent(agent_id)
        if not agent:
            raise ValueError(f"Unknown external agent: {agent_id}")

        try:
            result = await asyncio.to_thread(
                get_external_agent_history,
                agent,
                thread_id=thread_id,
                limit=limit,
            )
        except ExternalAgentGatewayError as exc:
            raise ValueError(str(exc)) from exc

        payload = dict(result)
        payload["protocol"] = agent.get("protocol")
        payload["capabilities"] = agent.get("capabilities", [])
        payload["completed"] = not _response_is_active(payload)
        payload["latestResponse"] = _extract_latest_response(payload)
        return json.dumps(payload, ensure_ascii=False, indent=2)


def _response_is_active(payload: Dict[str, Any]) -> bool:
    latest_turn = payload.get("latestTurn")
    if isinstance(latest_turn, dict):
        state = str(latest_turn.get("state") or "").strip().lower()
        if state:
            return state in ACTIVE_EXTERNAL_STATES

    status = str(payload.get("status") or "").strip().lower()
    return status in ACTIVE_EXTERNAL_STATES


def _extract_latest_response(payload: Dict[str, Any]) -> str:
    latest_turn = payload.get("latestTurn")
    if isinstance(latest_turn, dict):
        response = latest_turn.get("response")
        if isinstance(response, str):
            return response.strip()
    return ""