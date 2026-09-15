#!/usr/bin/env python3
"""
Route configuration for the A2A → OpenAI proxy.

Drop this file next to a2a_openai_proxy.py and set:
    A2A_PROXY_ROUTES=routes.json

Each key is a model name; each value configures how to reach that A2A peer.

Token resolution per route (first match wins):
  1. "token" literal in the route object
  2. "token_env" env var name — resolved at startup
  3. OpenClaw config fallback (reads ~/.openclaw/openclaw.json a2a-gateway token)

example.json:
{
  "glados": {"url": "http://hermes:9900/a2a/jsonrpc", "token_env": "HERMES_A2A_TOKEN"},
  "wheatley": {"url": "http://wheatley:18800/a2a/jsonrpc"},
  "pwnagotchi4b": {"url": "http://pwnagotchi.local:8700/a2a/jsonrpc", "token": "REPLACE_ME"}
}
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_ROUTES_PATH = Path(__file__).with_name("routes.json")
OPENCLAW_CONFIG_DEFAULT = os.environ.get(
    "OPENCLAW_CONFIG", str(Path.home() / ".openclaw" / "openclaw.json")
)


def load_token(route: dict[str, Any]) -> str:
    """Resolve the bearer token for one route."""
    if "token" in route and route["token"]:
        return str(route["token"])
    token_env = route.get("token_env")
    if token_env:
        env_val = os.environ.get(token_env, "")
        if env_val:
            return env_val
    return _load_openclaw_token()


def _load_openclaw_token() -> str:
    """Fallback: read the a2a-gateway token from OpenClaw config."""
    cfg_path = Path(os.environ.get("OPENCLAW_CONFIG", OPENCLAW_CONFIG_DEFAULT))
    if not cfg_path.is_file():
        return ""
    try:
        with cfg_path.open() as f:
            oc = json.load(f)
        return str(
            oc.get("plugins", {})
            .get("entries", {})
            .get("a2a-gateway", {})
            .get("config", {})
            .get("security", {})
            .get("token", "")
        )
    except (OSError, KeyError, json.JSONDecodeError):
        return ""


def load_routes(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load route table from a JSON config file.

    Falls back to an empty dict when the file is missing or unparseable, so
    callers can decide to discover peers dynamically instead.
    """
    path = path or DEFAULT_ROUTES_PATH
    if not path.is_file():
        return {}
    try:
        with path.open() as f:
            raw: dict[str, Any] = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    routes: dict[str, dict[str, Any]] = {}
    for model, cfg in raw.items():
        if not isinstance(cfg, dict):
            continue
        url = cfg.get("url", "").strip()
        if not url:
            continue
        routes[model.lower().strip()] = {
            "url": url,
            "token": load_token(cfg),
        }
    return routes
