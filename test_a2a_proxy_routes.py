#!/usr/bin/env python3
"""Quick smoke test for a2a_proxy_routes.py.
"""
import json
import os
from pathlib import Path

import a2a_proxy_routes as routes_mod

HERE = Path(__file__).resolve().parent


def test_load_token_explicit():
    route = {"url": "http://x", "token": "secret123"}
    assert routes_mod.load_token(route) == "secret123"
    print("[ok] explicit token")


def test_load_token_env():
    os.environ["PROXY_TEST_TOKEN"] = "env_secret"
    route = {"url": "http://x", "token_env": "PROXY_TEST_TOKEN"}
    assert routes_mod.load_token(route) == "env_secret"
    print("[ok] env token")
    os.environ.pop("PROXY_TEST_TOKEN", None)


def test_load_token_fallback():
    route = {"url": "http://x"}
    token = routes_mod.load_token(route)
    print(f"[ok] fallback token = {token!r} (length {len(token)})")


def test_load_routes(tmp_path):
    cfg = tmp_path / "routes.json"
    cfg.write_text(json.dumps({
        "glados": {"url": "http://hermes:9900/a2a/jsonrpc", "token_env": "HERMES_A2A_TOKEN"},
        "wheatley": {"url": "http://wheatley:18800/a2a/jsonrpc", "token": "static"},
        "bad": {"url": ""},
    }))
    routes = routes_mod.load_routes(cfg)
    assert set(routes) == {"glados", "wheatley"}
    assert routes["glados"]["url"] == "http://hermes:9900/a2a/jsonrpc"
    assert routes["wheatley"]["url"] == "http://wheatley:18800/a2a/jsonrpc"
    assert routes["wheatley"]["token"] == "static"
    print("[ok] load_routes parses valid config")


def test_load_routes_missing():
    routes = routes_mod.load_routes(HERE / "nonexistent.json")
    assert routes == {}
    print("[ok] load_routes handles missing file")


def test_load_routes_invalid():
    bad = HERE / "a2a_proxy_routes.py"
    routes = routes_mod.load_routes(bad)
    assert routes == {}
    print("[ok] load_routes handles invalid json")


if __name__ == "__main__":
    test_load_token_explicit()
    test_load_token_env()
    test_load_token_fallback()
    tmp_path = Path("/tmp/a2a_proxy_routes_test")
    tmp_path.mkdir(exist_ok=True)
    try:
        test_load_routes(tmp_path)
        test_load_routes_missing()
        test_load_routes_invalid()
    finally:
        for p in tmp_path.glob("*"):
            p.unlink()
        tmp_path.rmdir()
    print("\n✓ alle tests geslaagd")
