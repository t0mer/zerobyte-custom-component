from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    entities: list[ButtonEntity] = []

    for schedule in coordinator.data.get("schedules", []):
        if schedule.get("id") is None:
            continue
        entities += [
            ZerobyteScheduleRunButton(coordinator, schedule),
            ZerobyteScheduleStopButton(coordinator, schedule),
            ZerobyteScheduleForgetButton(coordinator, schedule),
        ]

    for volume in coordinator.data.get("volumes", []):
        if not volume.get("shortId"):
            continue
        entities += [
            ZerobyteVolumeMountButton(coordinator, volume),
            ZerobyteVolumeUnmountButton(coordinator, volume),
        ]

    async_add_entities(entities)


class _ZerobyteButton(ZerobyteEntity, ButtonEntity):
    def __init__(
        self,
        coordinator: ZerobyteCoordinator,
        device_id: str,
        device_name: str,
        device_model: str,
        unique_id: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, device_id, device_name, device_model)
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_icon = icon


# --------------------------------------------------------------------------- #
# Schedule buttons — identified by integer id                                  #
# --------------------------------------------------------------------------- #

class ZerobyteScheduleRunButton(_ZerobyteButton):
    def __init__(
        self, coordinator: ZerobyteCoordinator, schedule_data: dict
    ) -> None:
        schedule_id: int = schedule_data["id"]
        schedule_name: str = schedule_data.get("name", str(schedule_id))
        super().__init__(
            coordinator,
            device_id=f"{coordinator.entry_id}_schedule_{schedule_id}",
            device_name=schedule_name,
            device_model="Backup Schedule",
            unique_id=f"{coordinator.entry_id}_schedule_{schedule_id}_run",
            name="Run Backup",
            icon="mdi:play",
        )
        self._schedule_id = schedule_id

    async def async_press(self) -> None:
        await self.coordinator.async_run_backup(self._schedule_id)


class ZerobyteScheduleStopButton(_ZerobyteButton):
    def __init__(
        self, coordinator: ZerobyteCoordinator, schedule_data: dict
    ) -> None:
        schedule_id: int = schedule_data["id"]
        schedule_name: str = schedule_data.get("name", str(schedule_id))
        super().__init__(
            coordinator,
            device_id=f"{coordinator.entry_id}_schedule_{schedule_id}",
            device_name=schedule_name,
            device_model="Backup Schedule",
            unique_id=f"{coordinator.entry_id}_schedule_{schedule_id}_stop",
            name="Stop Backup",
            icon="mdi:stop",
        )
        self._schedule_id = schedule_id

    async def async_press(self) -> None:
        await self.coordinator.async_stop_backup(self._schedule_id)


class ZerobyteScheduleForgetButton(_ZerobyteButton):
    def __init__(
        self, coordinator: ZerobyteCoordinator, schedule_data: dict
    ) -> None:
        schedule_id: int = schedule_data["id"]
        schedule_name: str = schedule_data.get("name", str(schedule_id))
        super().__init__(
            coordinator,
            device_id=f"{coordinator.entry_id}_schedule_{schedule_id}",
            device_name=schedule_name,
            device_model="Backup Schedule",
            unique_id=f"{coordinator.entry_id}_schedule_{schedule_id}_forget",
            name="Run Retention",
            icon="mdi:delete-clock",
        )
        self._schedule_id = schedule_id

    async def async_press(self) -> None:
        await self.coordinator.async_run_forget(self._schedule_id)


# --------------------------------------------------------------------------- #
# Volume buttons — identified by string shortId                                #
# --------------------------------------------------------------------------- #

class ZerobyteVolumeMountButton(_ZerobyteButton):
    def __init__(
        self, coordinator: ZerobyteCoordinator, volume_data: dict
    ) -> None:
        short_id: str = volume_data["shortId"]
        volume_name: str = volume_data.get("name", short_id)
        super().__init__(
            coordinator,
            device_id=f"{coordinator.entry_id}_volume_{short_id}",
            device_name=volume_name,
            device_model="Volume",
            unique_id=f"{coordinator.entry_id}_volume_{short_id}_mount",
            name="Mount",
            icon="mdi:link",
        )
        self._short_id = short_id

    async def async_press(self) -> None:
        await self.coordinator.async_mount_volume(self._short_id)


class ZerobyteVolumeUnmountButton(_ZerobyteButton):
    def __init__(
        self, coordinator: ZerobyteCoordinator, volume_data: dict
    ) -> None:
        short_id: str = volume_data["shortId"]
        volume_name: str = volume_data.get("name", short_id)
        super().__init__(
            coordinator,
            device_id=f"{coordinator.entry_id}_volume_{short_id}",
            device_name=volume_name,
            device_model="Volume",
            unique_id=f"{coordinator.entry_id}_volume_{short_id}_unmount",
            name="Unmount",
            icon="mdi:link-off",
        )
        self._short_id = short_id

    async def async_press(self) -> None:
        await self.coordinator.async_unmount_volume(self._short_id)
