from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
        ZerobyteScheduleSwitch(coordinator, schedule)
        for schedule in coordinator.data.get("schedules", [])
        if schedule.get("id") is not None
    )


class ZerobyteScheduleSwitch(ZerobyteEntity, SwitchEntity):
    """Toggle a backup schedule on or off."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self, coordinator: ZerobyteCoordinator, schedule_data: dict
    ) -> None:
        # Schedules are identified by integer id, not shortId.
        self._schedule_id: int = schedule_data["id"]
        schedule_name: str = schedule_data.get("name", str(self._schedule_id))
        super().__init__(
            coordinator,
            device_id=f"{coordinator.entry_id}_schedule_{self._schedule_id}",
            device_name=schedule_name,
            device_model="Backup Schedule",
        )
        self._attr_unique_id = (
            f"{coordinator.entry_id}_schedule_{self._schedule_id}_enabled"
        )
        self._attr_name = "Enabled"

    def _get_schedule(self) -> dict | None:
        if not self.coordinator.data:
            return None
        return next(
            (s for s in self.coordinator.data.get("schedules", [])
             if s.get("id") == self._schedule_id),
            None,
        )

    @property
    def available(self) -> bool:
        return super().available and self._get_schedule() is not None

    @property
    def is_on(self) -> bool:
        schedule = self._get_schedule()
        return bool(schedule.get("enabled", False)) if schedule else False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        schedule = self._get_schedule()
        if not schedule:
            return {}
        attrs: dict[str, Any] = {
            "cron_expression": schedule.get("cronExpression", ""),
        }
        if paths := schedule.get("backupPaths"):
            attrs["backup_paths"] = paths
        if patterns := schedule.get("excludePatterns"):
            attrs["exclude_patterns"] = patterns
        if retention := schedule.get("retentionPolicy"):
            attrs["retention_policy"] = retention
        # Embedded volume and repository names for quick reference.
        if vol := schedule.get("volume"):
            attrs["volume"] = vol.get("name", "")
        if repo := schedule.get("repository"):
            attrs["repository"] = repo.get("name", "")
        return attrs

    def _build_update_body(self, enabled: bool) -> dict:
        """Build a valid PATCH body. repositoryId and cronExpression are required by the API."""
        schedule = self._get_schedule() or {}
        return {
            "enabled": enabled,
            "repositoryId": schedule.get("repositoryId", ""),
            "cronExpression": schedule.get("cronExpression", ""),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_update_schedule(
            self._schedule_id, self._build_update_body(True)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_update_schedule(
            self._schedule_id, self._build_update_body(False)
        )
