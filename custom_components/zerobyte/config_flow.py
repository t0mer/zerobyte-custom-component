from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from py_zerobyte import AuthenticationError, ZerobyteClient, ZerobyteError
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import callback

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MAX_SCAN_INTERVAL, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


def _validate_auth(url: str, username: str, password: str) -> None:
    client = ZerobyteClient(url, username, password)
    client.auth.get_me()


class ZerobyteConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(
                    _validate_auth,
                    user_input[CONF_URL],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ZerobyteError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error connecting to Zerobyte")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_URL])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Zerobyte ({user_input[CONF_URL]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> ZerobyteOptionsFlow:
        return ZerobyteOptionsFlow()


class ZerobyteOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=current_interval
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
        )
