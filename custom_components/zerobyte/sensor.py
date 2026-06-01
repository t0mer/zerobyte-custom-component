from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZerobyteCoordinator
from .entity import ZerobyteEntity


# --------------------------------------------------------------------------- #
# Helpers                                                                       #
# --------------------------------------------------------------------------- #

def _ms_to_dt(ms: int | None) -> datetime | None:
    """Convert a millisecond Unix timestamp to an aware datetime."""
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def _iso_to_dt(ts: str | None) -> datetime | None:
    """Parse a restic ISO-8601 timestamp string (may have nanosecond precision)."""
    if not ts:
        return None
    try:
        # Truncate sub-microsecond digits and normalise Z suffix
        ts = re.sub(r"(\.\d{6})\d+", r"\1", ts).replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Platform setup                                                                #
# --------------------------------------------------------------------------- #

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZerobyteCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for volume in coordinator.data.get("volumes", []):
        if not volume.get("shortId"):
            continue
        entities += [
            ZerobyteVolumeTotalSensor(coordinator, volume),
            ZerobyteVolumeUsedSensor(coordinator, volume),
            ZerobyteVolumeFreeSensor(coordinator, volume),
        ]

    for repo in coordinator.data.get("repositories", []):
        if not repo.get("shortId"):
            continue
        entities += [
            ZerobyteRepositoryStatusSensor(coordinator, repo),
            ZerobyteRepositoryLastCheckedSensor(coordinator, repo),
            ZerobyteRepositorySnapshotCountSensor(coordinator, repo),
            ZerobyteRepositoryLatestSnapshotSensor(coordinator, repo),
        ]

    for schedule in coordinator.data.get("schedules", []):
        if schedule.get("id") is None:
            continue
        entities += [
            ZerobyteScheduleLastBackupStatusSensor(coordinator, schedule),
            ZerobyteScheduleLastBackupSensor(coordinator, schedule),
            ZerobyteScheduleNextBackupSensor(coordinator, schedule),
        ]

    async_add_entities(entities)


# --------------------------------------------------------------------------- #
# Volume sensors                                                                #
# --------------------------------------------------------------------------- #

_GiB = 1024 ** 3


class _ZerobyteVolumeStorageSensor(ZerobyteEntity, SensorEntity):
    """Base class for volume statfs sensors."""

    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfInformation.GIBIBYTES
    _attr_suggested_display_precision = 2
    _stat_key: str  # "total" | "used" | "free"

    def __init__(self, coordinator: ZerobyteCoordinator, volume_data: dict) -> None:
        self._short_id: str = volume_data["shortId"]
        volume_name: str = volume_data.get("name", self._short_id)
        super().__init__(
            coordinator,
            device_id=f"{coordinator.entry_id}_volume_{self._short_id}",
            device_name=volume_name,
            device_model="Volume",
        )
        label = self._stat_key.capitalize()
        self._attr_unique_id = (
            f"{coordinator.entry_id}_volume_{self._short_id}_storage_{self._stat_key}"
        )
        self._attr_name = f"Storage {label}"

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
        vol = self._get_volume()
        return super().available and vol is not None and bool(vol.get("statfs"))

    @property
    def native_value(self) -> float | None:
        vol = self._get_volume()
        if not vol:
            return None
        raw = vol.get("statfs", {}).get(self._stat_key)
        if raw is None:
            return None
        return round(raw / _GiB, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        vol = self._get_volume()
        if not vol:
            return {}
        attrs: dict[str, Any] = {"backend": vol.get("type", "")}
        if path := vol.get("path"):
            attrs["path"] = path
        return attrs


class ZerobyteVolumeTotalSensor(_ZerobyteVolumeStorageSensor):
    _stat_key = "total"
    _attr_icon = "mdi:harddisk"


class ZerobyteVolumeUsedSensor(_ZerobyteVolumeStorageSensor):
    _stat_key = "used"
    _attr_icon = "mdi:harddisk-remove"


class ZerobyteVolumeFreeSensor(_ZerobyteVolumeStorageSensor):
    _stat_key = "free"
    _attr_icon = "mdi:harddisk-plus"


# --------------------------------------------------------------------------- #
# Repository sensors                                                            #
# --------------------------------------------------------------------------- #

class _ZerobyteRepoBase(ZerobyteEntity, SensorEntity):
    """Common repo lookup helper."""

    def __init__(self, coordinator: ZerobyteCoordinator, repo_data: dict) -> None:
        self._short_id: str = repo_data["shortId"]
        repo_name: str = repo_data.get("name", self._short_id)
        super().__init__(
            coordinator,
            device_id=f"{coordinator.entry_id}_repo_{self._short_id}",
            device_name=repo_name,
            device_model="Repository",
        )

    def _get_repo(self) -> dict | None:
        if not self.coordinator.data:
            return None
        return next(
            (r for r in self.coordinator.data.get("repositories", [])
             if r.get("shortId") == self._short_id),
            None,
        )

    @property
    def available(self) -> bool:
        return super().available and self._get_repo() is not None


class ZerobyteRepositoryStatusSensor(_ZerobyteRepoBase):
    _attr_icon = "mdi:database-check"

    def __init__(self, coordinator: ZerobyteCoordinator, repo_data: dict) -> None:
        super().__init__(coordinator, repo_data)
        self._attr_unique_id = (
            f"{coordinator.entry_id}_repo_{self._short_id}_status"
        )
        self._attr_name = "Status"

    @property
    def native_value(self) -> str | None:
        repo = self._get_repo()
        return repo.get("status") if repo else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        repo = self._get_repo()
        if not repo:
            return {}
        attrs: dict[str, Any] = {
            "backend": repo.get("type", ""),
            "compression_mode": repo.get("compressionMode", ""),
        }
        if created := repo.get("createdAt"):
            dt = _ms_to_dt(created)
            attrs["created_at"] = dt.isoformat() if dt else None
        if error := repo.get("lastError"):
            attrs["last_error"] = error
        config = repo.get("config", {})
        if path := config.get("path"):
            attrs["path"] = path
        elif bucket := config.get("bucket"):
            attrs["bucket"] = bucket
        elif remote := config.get("remote"):
            attrs["remote"] = remote
        return attrs


class ZerobyteRepositoryLastCheckedSensor(_ZerobyteRepoBase):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:database-clock"

    def __init__(self, coordinator: ZerobyteCoordinator, repo_data: dict) -> None:
        super().__init__(coordinator, repo_data)
        self._attr_unique_id = (
            f"{coordinator.entry_id}_repo_{self._short_id}_last_checked"
        )
        self._attr_name = "Last Checked"

    @property
    def native_value(self) -> datetime | None:
        repo = self._get_repo()
        if not repo:
            return None
        return _ms_to_dt(repo.get("lastChecked"))


class ZerobyteRepositorySnapshotCountSensor(_ZerobyteRepoBase):
    _attr_icon = "mdi:camera-burst"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "snapshots"

    def __init__(self, coordinator: ZerobyteCoordinator, repo_data: dict) -> None:
        super().__init__(coordinator, repo_data)
        self._attr_unique_id = (
            f"{coordinator.entry_id}_repo_{self._short_id}_snapshots"
        )
        self._attr_name = "Snapshot Count"

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 0
        return len(
            self.coordinator.data.get("snapshots", {}).get(self._short_id, [])
        )


class ZerobyteRepositoryLatestSnapshotSensor(_ZerobyteRepoBase):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:camera"

    def __init__(self, coordinator: ZerobyteCoordinator, repo_data: dict) -> None:
        super().__init__(coordinator, repo_data)
        self._attr_unique_id = (
            f"{coordinator.entry_id}_repo_{self._short_id}_latest_snapshot"
        )
        self._attr_name = "Latest Snapshot"

    @property
    def native_value(self) -> datetime | None:
        if not self.coordinator.data:
            return None
        snaps = self.coordinator.data.get("snapshots", {}).get(self._short_id, [])
        if not snaps:
            return None
        latest = max(snaps, key=lambda s: s.get("time", ""), default=None)
        if not latest:
            return None
        return _iso_to_dt(latest.get("time"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        snaps = self.coordinator.data.get("snapshots", {}).get(self._short_id, [])
        if not snaps:
            return {}
        latest = max(snaps, key=lambda s: s.get("time", ""), default=None)
        if not latest:
            return {}
        attrs: dict[str, Any] = {}
        if sid := latest.get("short_id"):
            attrs["snapshot_id"] = sid
        if hostname := latest.get("hostname"):
            attrs["hostname"] = hostname
        if paths := latest.get("paths"):
            attrs["paths"] = paths
        if tags := latest.get("tags"):
            attrs["tags"] = tags
        return attrs


# --------------------------------------------------------------------------- #
# Backup schedule sensors                                                       #
# --------------------------------------------------------------------------- #

class _ZerobyteScheduleBase(ZerobyteEntity, SensorEntity):
    """Common schedule lookup helper. Schedules use integer id, not shortId."""

    def __init__(self, coordinator: ZerobyteCoordinator, schedule_data: dict) -> None:
        self._schedule_id: int = schedule_data["id"]
        schedule_name: str = schedule_data.get("name", str(self._schedule_id))
        super().__init__(
            coordinator,
            device_id=f"{coordinator.entry_id}_schedule_{self._schedule_id}",
            device_name=schedule_name,
            device_model="Backup Schedule",
        )

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


class ZerobyteScheduleLastBackupStatusSensor(_ZerobyteScheduleBase):
    _attr_icon = "mdi:backup-restore"

    def __init__(self, coordinator: ZerobyteCoordinator, schedule_data: dict) -> None:
        super().__init__(coordinator, schedule_data)
        self._attr_unique_id = (
            f"{coordinator.entry_id}_schedule_{self._schedule_id}_last_backup_status"
        )
        self._attr_name = "Last Backup Status"

    @property
    def native_value(self) -> str | None:
        schedule = self._get_schedule()
        return schedule.get("lastBackupStatus") if schedule else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        schedule = self._get_schedule()
        if not schedule:
            return {}
        attrs: dict[str, Any] = {"cron_expression": schedule.get("cronExpression", "")}
        if err := schedule.get("lastBackupError"):
            attrs["last_backup_error"] = err
        return attrs


class ZerobyteScheduleLastBackupSensor(_ZerobyteScheduleBase):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check"

    def __init__(self, coordinator: ZerobyteCoordinator, schedule_data: dict) -> None:
        super().__init__(coordinator, schedule_data)
        self._attr_unique_id = (
            f"{coordinator.entry_id}_schedule_{self._schedule_id}_last_backup"
        )
        self._attr_name = "Last Backup"

    @property
    def native_value(self) -> datetime | None:
        schedule = self._get_schedule()
        if not schedule:
            return None
        return _ms_to_dt(schedule.get("lastBackupAt"))


class ZerobyteScheduleNextBackupSensor(_ZerobyteScheduleBase):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-fast"

    def __init__(self, coordinator: ZerobyteCoordinator, schedule_data: dict) -> None:
        super().__init__(coordinator, schedule_data)
        self._attr_unique_id = (
            f"{coordinator.entry_id}_schedule_{self._schedule_id}_next_backup"
        )
        self._attr_name = "Next Backup"

    @property
    def native_value(self) -> datetime | None:
        schedule = self._get_schedule()
        if not schedule:
            return None
        return _ms_to_dt(schedule.get("nextBackupAt"))
