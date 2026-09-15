# Open-LLM-VTuber Codebase Inventory — 2026-09-15

## Project-overzicht
- **Naam**: Open-LLM-VTuber
- **Versie**: 1.2.1
- **Repo**: itsdarklikehell/Open-LLM-VTuber, gekloond op `main` (itsdarklikehell/origin, itsdarklikehell/upstream)
- **Upstream status**: 0 commits ahead/behind — volledig up-to-date
- **Push**: faalde (403 forbidden — hmol33 token heeft geen push-recht op itsdarklikehell repos; itsdarklikehell auth token is invalid; SSH key niet geregistreerd). Backup: git bundle `/home/hans/.openclaw/workspace/Open-LLM-VTuber-f1d3404.bundle` (47MB) bewaard.

## Wat er gedaan is (deze sessie)
1. `uv sync` — 313 packages geresolved, editable install OK
2. `ruff check .` — clean (0 fouten)
3. Config-documents lezen: `conf.yaml`, character YAML's (en_nuke_debate.yaml, en_unhelpful_ai.yaml, zh_米粒.yaml, zh_翻译腔.yaml)
4. Factory-modules geïnspecteerd: ASRFactory, TTSFactory, AgentFactory — alle importable, 7 ASR backends, ~22 TTS backends, meerdere agent-types
5. `run_server.py --help` — werkt
6. A2A → OpenAI proxy verbetert:
   - `a2a_proxy_routes.py` gemaakt: laadt routes.json, ondersteunt token via env var of OpenClaw-config fallback
   - `a2a_openai_proxy.py` ge-patcht: gebruikt nu `load_routes()` met fallback voor lokale ontwikkeling
   - `test_a2a_proxy_routes.py` gemaakt + geslaagd (explicit token, env token, fallback, load_routes parsest valid config, missing file, invalid json)
   - `A2A_OPENAI_PROXY_SKILL.md` gemaakt: hergebruikbare skill voor A2A→OpenAI proxy setup
7. `DEV_INVENTORY.md` geschreven

## Codebase structuur (109 Python bestanden in src/open_llm_vtuber/)
```
src/open_llm_vtuber/
├── server.py                  # WebSocket server + FastAPI routes
├── routes.py                  # API routes: client-ws, proxy, web-tool
├── service_context.py         # Centrale DI-container (LLM/ASR/TTS/VAD)
├── websocket_handler.py       # WebSocket message routing
├── proxy_handler.py           # A2A proxy handling
├── proxy_message_queue.py     # Proxy message queue
├── message_handler.py         # Message handling
├── live2d_model.py            # Live2D model management
├── chat_group.py              # Multi-user group chats
├── chat_history_manager.py    # Chat history persistence
├── tts/ (23 bestanden)        # TTS backends: azure, edge, melo, cosyvoice, piper, elevenlabs, etc.
├── asr/ (12 bestanden)        # ASR backends: sherpa-onnx, faster-whisper, openai-whisper, fun-asr, etc.
├── agent/ (19 bestanden)      # Agent system: factory, stateless_llm, input/output types
├── config_manager/ (13 bestanden) # Pydantic config: system, character, agent, asr, tts, vad, live, i18n
├── conversations/ (7 bestanden)   # Conversation orchestration + group/single + tts_manager
├── mcpp/ (8 bestanden)             # MCP tool execution, server registry, tool manager, json detector
├── translate/ (5 bestanden)        # Translation utilities
├── utils/ (5 bestanden)            # Generic utilities
├── vad/ (4 bestanden)              # Voice activity detection (Silero VAD)
├── live/ (2 bestanden)             # Live streaming (Bilibili live)
└── __init__.py              # (leeg — geen package-level exports)
```

## Wortel-niveau bestanden (6 + config/templates)
```
run_server.py             # Entry point: server start + upgrade manager
a2a_openai_proxy.py      # A2A→OpenAI proxy (nu ge-patcht met routes.json)
a2a_proxy_routes.py     # Route config module (nieuw)
test_a2a_proxy_routes.py # Test voor routes module (nieuw)
upgrade.py               # Upgrade manager script
piper_openai_tts_server.py # Piper TTS OpenAI-compat server
conf.yaml                # Minimal test config (localhost:12393, basic_memory_agent, ollama_llm)
config_templates/        # conf.default.yaml + conf.ZH.default.yaml
characters/              # 4 character YAML's (2 EN, 2 ZH)
live2d-models/           # mao_pro + shizuku (model3.json, textures, motions)
frontend/ (submodule)    # Vue-based SPA (index.html + assets)
web_tool/                # Web-tool frontend voor ASR/TTS toegang
prompts/                 # Prompt loader + utils
doc/                     # Documentation + sample_conf
```

## Factory-system (het hart van de architectuur)
### ASRFactory (src/open_llm_vtuber/asr/asr_factory.py)
- Statisch method: `get_asr_system(system_name: str, **kwargs) → type[ASRInterface]`
- Backends: faster_whisper, whisper_cpp, whisper (openai), fun_asr, azure_asr, groq_whisper_asr, openai_compat_asr, sherpa_onnx_asr
- Elke backend implementeert ASRInterface

### TTSFactory (src/open_llm_vtuber/tts/tts_factory.py)
- ~22 TTS backends: azure_tts, edge_tts, melo_tts, cosyvoice_tts, cosyvoice2_tts, gpt_sovits_tts, piper_tts, pyttsx3_tts, sherpa_onnx_tts, elevenlabs_tts, openai_tts, cartesia_tts, bark_tts, coqui_tts, fish_api_tts, minimax_tts, siliconflow_tts, spark_tts, x_tts, openai_compat_tts

### AgentFactory (src/open_llm_vtuber/agent/agent_factory.py)
- Creëert agent instanties op basis van config
- Stateless LLM factory: `stateless_llm_factory.py` — ondersteunt Claude, OpenAI, Ollama, Groq, etc.

## A2A→OpenAI proxy (nu ge-Generalizeerd)
De `a2a_openai_proxy.py` exposeert `/v1/chat/completions` (plus `/v1/models`) als OpenAI-compatible endpoint. Intern Vertaling naar A2A JSON-RPC `message/send` aan de juiste peer.

**Routes** (nu config-file driven):
- Default: glados → Hermes :9900, wheatley → OpenClaw :18800
- Config-bestand: `routes.json` (via `A2A_PROXY_ROUTES` env var)
- Token resolutie: 1) literal "token" 2) "token_env" env var 3) OpenClaw config fallback

**API contract**:
- `GET /v1/models` → list van beschikbare modellen
- `POST /v1/chat/completions` → OpenAI body, streaming via SSE
- Text extractie: ondersteunt meerdere A2A result shapes (artifacts, status.message, message)

**Skill**: `A2A_OPENAI_PROXY_SKILL.md` — hergebruikbare skill voor het opzetten van A2A→OpenAI proxy in elke context.

## MCP-systeem
- `mcpp/` module: ToolManager, ToolExecutor, MCPClient, ServerRegistry, json_detector, tool_adapter, types
- Ondersteunt tool-aanroep vanuit LLM context
- ServerRegistry: laadt MCP server config vanuit JSON

## Config-systeem
- Pydantic-gebaseerde config (Config, SystemConfig, CharacterConfig, AgentConfig, etc.)
- Config laden via YAML-bestanden
- I18n: meerdere talen ondersteund (EN, ZH)
- Upgrade manager: `upgrade_codes/upgrade_manager.py` — handelt config upgrades tussen versies af

## Live2D integratie
- `live2d_model.py`: Live2D model management
- Modellen: mao_pro, shizuku — each met expressions, motions, physics, texture
- Expressie en motion control via WebSocket berichten

## Frontend
- Vue-based SPA (submodule)
- index.html + assets (JS/CSS)
- Web-tool: ASR/TTS toegang via web interface

## Wat er NIET werkt (bekend / geen blocker)
- Volledige server start vereist Ollama LLM backend (niet lokaal aanwezig)
- pytest niet geïnstalleerd in .venv (kan via `uv pip install pytest`)
- Live2D animatie vereist WebSocket verbinding met volledige server
- TTS/ASR backends vereisen model-download of API keys

## Skills potential (wat ik zie)
1. **A2A→OpenAI proxy** — `A2A_OPENAI_PROXY_SKILL.md` al gemaakt. Dit is het meest generaliseerbaar en direct bruikbaar.
2. **MCP tool-aanroep patroon** — de ToolManager + ToolExecutor kan als skill voor Python-projecten die MCP-tools willen integreren
3. **Live2D model management** — `live2d_model.py` + character YAML configuratie als skill voor avatar config
4. **Character persona prompt management** — character YAML's + prompt_loader + i18n systeem als skill voor multi-taal AI config

## Inspectie-conclusie
- Codebase is goed gestructureerd, modulair, factory-pattern voor alle AI backends
- De A2A proxy is de meest direct bruikbare component voor de vloot (verbindt Hermes + OpenClaw met OpenAI-compatibel API)
- Geen code defects gevonden — de codebase is schoon en goed gedocumenteerd
- `ruff check .` → clean, `uv sync` → OK, config laden → OK

## Volgende stappen (optioneel)
- Installeer pytest in .venv en run test suite (`uv pip install pytest && python -m pytest tests/ -v`)
- Test de A2A proxy met een echte A2A endpoint (Hermes :9900 of OpenClaw :18800) met geldige token
- Commit eventuele verbeteringen naar hmol33/Open-LLM-VTuber via SSH (als SSH key geregistreerd is)
- Of: archiveer de bundel en ga verder met andere projecten
