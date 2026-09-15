---
name: a2a-openai-proxy
description: Run and configure an A2A-to-OpenAI-compatible proxy that lets any OpenAI SDK client talk to A2A JSON-RPC agents (Hermes, OpenClaw, etc.) via /v1/chat/completions + SSE streaming. Use when bridging an OpenAI-compatible LLM client to an A2A peer, wiring Open-LLM-VTuber's openai_compat_llm backend to Hermes/Wheatley, or standing up a local proxy for an offline voice-AI pipeline.
---

# A2A → OpenAI-Compatible Proxy

Standalone, stdlib-only HTTP server that exposes an OpenAI-compatible `/v1/chat/completions` endpoint (plus `/v1/models`). Internally it translates each request into an A2A JSON-RPC `message/send` to the matching peer and streams the reply back as SSE.

## Quick start

```bash
python3 a2a_openai_proxy.py
# listens on 127.0.0.1:8890 by default
```

Then point any OpenAI SDK client at `http://localhost:8890/v1` with `model="glados"` (or `"wheatley"`).

## Routing

The proxy routes by **model name** to an A2A peer. Defaults:

| Model      | A2A endpoint                         |
|------------|--------------------------------------|
| `glados`   | `http://localhost:9900/a2a/jsonrpc` |
| `wheatley` | `http://localhost:18800/a2a/jsonrpc`|

Override per-peer via env:

```
HERMES_A2A_URL=http://hermes:9900/a2a/jsonrpc
OPENCLAW_A2A_URL=http://wheatley:18800/a2a/jsonrpc
A2A_PROXY_PORT=8890
A2A_PROXY_CONTEXT_PREFIX=ollvtuber
```

## Auth

The proxy reads its bearer token from `~/.openclaw/openclaw.json` (the a2a-gateway security token) by default, and falls back silently when missing (dev-mode, never ship that). Per-route token override: `HERMES_A2A_TOKEN`. Always configure a real token; unauthenticated A2A is a LAN-only dev shortcut.

## API contract

- `GET /v1/models` → `{"object":"list","data":[{"id":"glados"},{"id":"wheatley"}]}`
- `POST /v1/chat/completions` → standard OpenAI body; `model` must be a known route (or fuzzy-matched on `gla`/`wheat`).
  - Non-streaming: single JSON response.
  - Streaming: SSE with chunked deltas + `[DONE]`.

## Text extraction

The proxy handles several A2A result shapes: `artifacts[].parts[].text`, `status.message.parts[].text`, and `message.parts[].text`. This is the canonical extraction helper; keep it in sync with any new A2A result shape you encounter. Missing text → poll `tasks/get` by `result.id` every 3s until COMPLETED/FAILED or timeout.

## Configuration file

For more than two peers or environment-driven routing, drop a JSON config next to the proxy and point `A2A_PROXY_ROUTES` at it:

```json
{
  "glados": {"url": "http://localhost:9900/a2a/jsonrpc", "token_env": "HERMES_A2A_TOKEN"},
  "wheatley": {"url": "http://localhost:18800/a2a/jsonrpc", "token_env": "WHEATLEY_A2A_TOKEN"},
  "my-peer": {"url": "http://peer:8700/a2a/jsonrpc", "token": "REPLACE_ME"}
}
```

Token resolution order: `token` literal > `token_env` env var > OpenClaw config fallback.

## Testing locally

Without a real A2A peer, you can smoke-test the HTTP contract with curl:

```bash
# models
curl -s http://localhost:8890/v1/models | python3 -m json.tool

# non-streaming chat (will error without a live peer — that's fine, proves routing + error path)
curl -s -X POST http://localhost:8890/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"glados","messages":[{"role":"user","content":"hello"}],"stream":false}' | python3 -m json.tool
```

For a real round-trip, run the proxy against Hermes (:9900) or OpenClaw (:18800) with a valid token and confirm chat completions + SSE streaming behave.

## Implementation notes

- Stdlib only (`http.server`, `urllib`, `json`). No pip deps.
- ThreadingHTTPServer, so concurrent OpenAI SDK requests are safe.
- CORS headers on every route (`Access-Control-Allow-Origin: *`).
- `call_agent` does sync-first, async-poll fallback: it tries a direct text extract, then polls `tasks/get` for up to `timeout` seconds.
- Never hardcode tokens in the proxy source; load from env or config.
