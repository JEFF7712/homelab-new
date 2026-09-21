from __future__ import annotations

import os
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_FALLBACK_AGENT, DOMAIN

FALLBACK_AGENT = "conversation.jarvis"


class JarvisJevConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if not os.environ.get("TYPESAFE_API_KEY"):
            return self.async_abort(reason="missing_api_key")
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="Jarvis Jev Router",
            data={CONF_FALLBACK_AGENT: FALLBACK_AGENT},
        )
