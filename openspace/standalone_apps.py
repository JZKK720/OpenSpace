from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "openspace" / "config" / "standalone_apps.json"


def load_standalone_apps() -> List[Dict[str, Any]]:
    config_path = Path(os.environ.get("OPENSPACE_STANDALONE_APPS_CONFIG", DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        return []

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    apps = raw.get("apps") if isinstance(raw, dict) else None
    if not isinstance(apps, list):
        return []

    resolved_apps: List[Dict[str, Any]] = []
    for item in apps:
        if not isinstance(item, dict):
            continue

        app_id = str(item.get("id") or "").strip()
        if not app_id:
            continue

        public_url = _resolve_url(item, "public_url")
        internal_url = _resolve_url(item, "internal_url") or public_url
        health_url = _resolve_url(item, "health_url") or internal_url or public_url
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []

        resolved_apps.append(
            {
                "id": app_id,
                "name": str(item.get("name") or app_id.replace("-", " ").title()),
                "description": str(item.get("description") or ""),
                "kind": str(item.get("kind") or "agent-app"),
                "icon": str(item.get("icon") or "grid"),
                "tags": [str(tag) for tag in tags if str(tag).strip()],
                "publicUrl": public_url,
                "internalUrl": internal_url,
                "healthUrl": health_url,
            }
        )

    return resolved_apps


def get_standalone_apps_status(timeout: float = 1.5) -> List[Dict[str, Any]]:
    statuses: List[Dict[str, Any]] = []
    for app in load_standalone_apps():
        probe_url = app.get("healthUrl") or app.get("internalUrl") or app.get("publicUrl")
        probe = _probe_url(str(probe_url or ""), timeout=timeout)
        statuses.append(
            {
                **app,
                "available": probe["available"],
                "status": "up" if probe["available"] else "down",
                "statusCode": probe["statusCode"],
                "latencyMs": probe["latencyMs"],
                "error": probe["error"],
            }
        )
    return statuses


def get_standalone_app(app_id: str) -> Dict[str, Any] | None:
    lookup_id = str(app_id or "").strip().lower()
    if not lookup_id:
        return None

    for app in load_standalone_apps():
        if str(app.get("id") or "").strip().lower() == lookup_id:
            return app
    return None


def get_standalone_app_status(app_id: str, timeout: float = 1.5) -> Dict[str, Any] | None:
    app = get_standalone_app(app_id)
    if not app:
        return None

    probe_url = app.get("healthUrl") or app.get("internalUrl") or app.get("publicUrl")
    probe = _probe_url(str(probe_url or ""), timeout=timeout)
    return {
        **app,
        "available": probe["available"],
        "status": "up" if probe["available"] else "down",
        "statusCode": probe["statusCode"],
        "latencyMs": probe["latencyMs"],
        "error": probe["error"],
    }


def _resolve_url(item: Dict[str, Any], key: str) -> str:
    env_key = str(item.get(f"{key}_env") or "").strip()
    if env_key:
        env_value = os.environ.get(env_key, "").strip()
        if env_value:
            return env_value
    return str(item.get(key) or "").strip()


def _probe_url(url: str, timeout: float) -> Dict[str, Any]:
    if not url:
        return {
            "available": False,
            "statusCode": 0,
            "latencyMs": None,
            "error": "No probe URL configured",
        }

    head_result = _probe_once(url, method="HEAD", timeout=timeout)
    if head_result["available"] or head_result["statusCode"] not in {405, 501}:
        return head_result
    return _probe_once(url, method="GET", timeout=timeout)


def _probe_once(url: str, *, method: str, timeout: float) -> Dict[str, Any]:
    request = Request(url, method=method, headers={"User-Agent": "OpenSpaceDashboard/1.0"})
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = int(getattr(response, "status", 200))
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "available": 200 <= status_code < 500,
                "statusCode": status_code,
                "latencyMs": latency_ms,
                "error": None,
            }
    except HTTPError as exc:
        status_code = int(getattr(exc, "code", 0) or 0)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "available": 200 <= status_code < 500,
            "statusCode": status_code,
            "latencyMs": latency_ms,
            "error": None if 200 <= status_code < 500 else str(exc.reason),
        }
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return {
            "available": False,
            "statusCode": 0,
            "latencyMs": int(timeout * 1000),
            "error": str(exc),
        }