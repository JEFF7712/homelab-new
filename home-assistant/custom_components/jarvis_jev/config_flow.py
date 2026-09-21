from __future__ import annotations

import os
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import ConversationAgentSelector

from .const import CONF_FALLBACK_AGENT, DOMAIN


class JarvisJevConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not os.environ.get("TYPESAFE_API_KEY"):
                errors["base"] = "missing_api_key"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Jarvis Jev Router", data=user_input
                )

        schema = vol.Schema(
            {vol.Required(CONF_FALLBACK_AGENT): ConversationAgentSelector()}
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
