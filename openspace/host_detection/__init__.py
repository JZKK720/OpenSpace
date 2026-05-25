"""Host-agent config auto-detection.

Public API consumed by other OpenSpace subsystems (cloud, mcp_server, …):

  - ``build_llm_kwargs``          — resolve LLM credentials
  - ``build_grounding_config_path`` — resolve grounding config
  - ``read_host_mcp_env``         — host-agnostic skill env reader
  - ``get_openai_api_key``        — OpenAI key resolution (multi-host)

Internal / legacy re-exports (prefer the generic names above):

  - ``read_nanobot_mcp_env``      — nanobot-specific, kept for backward compat
  - ``try_read_nanobot_config``

Supported host agents:

  - **nanobot** — ``~/.nanobot/config.json``  (``tools.mcpServers.openspace.env``)
"""

import logging
from typing import Dict, Optional

from openspace.host_detection.resolver import (
    build_grounding_config_path,
    build_llm_kwargs,
    load_runtime_env,
)
from openspace.host_detection.nanobot import (
    get_openai_api_key as _nanobot_get_openai_api_key,
    read_nanobot_mcp_env,
    try_read_nanobot_config,
)

logger = logging.getLogger("openspace.host_detection")


def read_host_mcp_env() -> Dict[str, str]:
    """Read the OpenSpace env block from the current host agent config.

    Resolution order:
      1. nanobot — ``tools.mcpServers.openspace.env``
      2. Empty dict (no host detected)

    Callers (e.g. ``cloud.auth``) use this single entry point and never
    need to know which host agent is active.
    """
    env = read_nanobot_mcp_env()
    if env:
        return env

    return {}


def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key for embedding generation (multi-host).

    Resolution:
      1. ``OPENAI_API_KEY`` env var  (checked inside nanobot reader)
      2. nanobot config ``providers.openai.apiKey``
      3. None
    """
    return _nanobot_get_openai_api_key()


__all__ = [
    "build_llm_kwargs",
    "build_grounding_config_path",
    "load_runtime_env",
    "get_openai_api_key",
    "read_host_mcp_env",
    "read_nanobot_mcp_env",
    "try_read_nanobot_config",
]
