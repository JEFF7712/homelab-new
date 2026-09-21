DOMAIN = "jarvis_jev"
CONF_FALLBACK_AGENT = "fallback_agent"
# Phase 0: no local LLM. Qwen/Ollama was removed to free the T1000 GPU;
# the cloud fallback is the Google AI conversation agent (tools enabled,
# assist-only exposure). Entity-id form resolves via conversation.get_entity.
OLLAMA_FALLBACK_AGENT = "conversation.google_ai_conversation"

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
REQUEST_TIMEOUT_SECONDS = 1.5
SHADOW_URL = "http://local-decision.voice.svc.cluster.local:8080/v1/systemone"
SHADOW_TIMEOUT_SECONDS = 15.0

LIGHT_THRESHOLD = 0.95
CLIMATE_THRESHOLD = 0.98
CLARIFY_THRESHOLD = 0.75
