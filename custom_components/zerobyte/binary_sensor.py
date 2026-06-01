from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZerobyteCoordinator
from .entity import ZerobyteEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZerobyteCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ZerobyteVolumeMountedSensor(coordinator, volume)
        for volume in coordinator.data.get("volumes", [])
        if volume.get("shortId")
    )


class ZerobyteVolumeMountedSensor(ZerobyteEntity, BinarySensorEntity):
    """True when the volume status is 'mounted'."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:harddisk"

    def __init__(
        self, coordinator: ZerobyteCoordinator, volume_data: dict
    ) -> None:
        self._short_id: str = volume_data["shortId"]
        volume_name: str = volume_data.get("name", self._short_id)
        super().__init__(
            coordinator,
            device_id=f"{coordinator.entry_id}_volume_{self._short_id}",
            device_name=volume_name,
            device_model="Volume",
        )
        self._attr_unique_id = (
            f"{coordinator.entry_id}_volume_{self._short_id}_mounted"
        )
        self._attr_name = "Mounted"

    def _get_volume(self) -> dict | None:
        if not self.coordinator.data:
            return None
        return next(
            (v for v in self.coordinator.data.get("volumes", [])
             if v.get("shortId") == self._short_id),
            None,
        )

    @property
    def available(self) -> bool:
        return super().available and self._get_volume() is not None

    @property
    def is_on(self) -> bool:
        vol = self._get_volume()
        return vol.get("status") == "mounted" if vol else False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        vol = self._get_volume()
        if not vol:
            return {}
        attrs: dict[str, Any] = {
            "backend": vol.get("type", ""),
            "status": vol.get("status", ""),
        }
        if path := vol.get("path"):
            attrs["path"] = path
        if error := vol.get("lastError"):
            attrs["last_error"] = error
        if (ts := vol.get("lastHealthCheck")) is not None:
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            attrs["last_health_check"] = dt.isoformat()
        return attrs
