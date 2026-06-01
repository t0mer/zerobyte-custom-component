from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import ZerobyteCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = ZerobyteCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Zerobyte ({entry.data[CONF_URL]})",
        manufacturer="Zerobyte",
        model="Backup Server",
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry whenever the user saves new options (e.g. scan interval).
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
