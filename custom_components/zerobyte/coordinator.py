from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from py_zerobyte import AuthenticationError, ZerobyteClient, ZerobyteError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ZerobyteCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        interval_minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval_minutes),
        )
        self.entry_id = entry.entry_id
        self._url: str = entry.data[CONF_URL]
        self._username: str = entry.data[CONF_USERNAME]
        self._password: str = entry.data[CONF_PASSWORD]
        self._client: ZerobyteClient | None = None

    def _create_client(self) -> ZerobyteClient:
        return ZerobyteClient(self._url, self._username, self._password)

    async def _get_client(self) -> ZerobyteClient:
        if self._client is None:
            self._client = await self.hass.async_add_executor_job(self._create_client)
        return self._client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            client = await self._get_client()

            volumes_raw = await self.hass.async_add_executor_job(client.volumes.list)
            repositories = await self.hass.async_add_executor_job(client.repositories.list)
            schedules = await self.hass.async_add_executor_job(client.backup_schedules.list)

            # Enrich each volume with statfs (total/used/free) and computed path.
            # GET /volumes/:shortId returns {volume: {..., path}, statfs: {total, used, free}}.
            volumes: list[dict] = []
            for vol in volumes_raw or []:
                short_id = vol.get("shortId", "")
                enriched: dict = dict(vol)
                if short_id:
                    try:
                        detail = await self.hass.async_add_executor_job(
                            client.volumes.get, short_id
                        )
                        enriched["statfs"] = detail.get("statfs", {})
                        enriched["path"] = detail.get("volume", {}).get("path", "")
                    except ZerobyteError as err:
                        _LOGGER.debug("Could not fetch details for volume %s: %s", short_id, err)
                        enriched.setdefault("statfs", {})
                        enriched.setdefault("path", "")
                volumes.append(enriched)

            # Fetch snapshot lists per repository.
            snapshots: dict[str, list] = {}
            for repo in repositories or []:
                repo_id = repo.get("shortId", "")
                if repo_id:
                    try:
                        snaps = await self.hass.async_add_executor_job(
                            client.snapshots.list, repo_id
                        )
                        snapshots[repo_id] = snaps or []
                    except ZerobyteError as err:
                        _LOGGER.debug("Could not fetch snapshots for repo %s: %s", repo_id, err)
                        snapshots[repo_id] = []

            return {
                "volumes": volumes,
                "repositories": repositories or [],
                "schedules": schedules or [],
                "snapshots": snapshots,
            }
        except AuthenticationError:
            self._client = None
            raise UpdateFailed("Authentication failed — credentials may have changed")
        except ZerobyteError as err:
            raise UpdateFailed(f"Zerobyte API error: {err}") from err

    # ------------------------------------------------------------------ #
    # Schedule actions — schedules are identified by integer id           #
    # ------------------------------------------------------------------ #

    async def async_update_schedule(self, schedule_id: int, data: dict) -> None:
        client = await self._get_client()
        try:
            await self.hass.async_add_executor_job(
                client.backup_schedules.update, schedule_id, data
            )
        except ZerobyteError as err:
            raise HomeAssistantError(f"Failed to update schedule: {err}") from err
        await self.async_request_refresh()

    async def async_run_backup(self, schedule_id: int) -> None:
        client = await self._get_client()
        try:
            await self.hass.async_add_executor_job(
                client.backup_schedules.run_now, schedule_id
            )
        except ZerobyteError as err:
            raise HomeAssistantError(f"Failed to trigger backup: {err}") from err

    async def async_stop_backup(self, schedule_id: int) -> None:
        client = await self._get_client()
        try:
            await self.hass.async_add_executor_job(
                client.backup_schedules.stop_backup, schedule_id
            )
        except ZerobyteError as err:
            raise HomeAssistantError(f"Failed to stop backup: {err}") from err

    async def async_run_forget(self, schedule_id: int) -> None:
        client = await self._get_client()
        try:
            await self.hass.async_add_executor_job(
                client.backup_schedules.run_forget, schedule_id
            )
        except ZerobyteError as err:
            raise HomeAssistantError(f"Failed to run retention policy: {err}") from err

    # ------------------------------------------------------------------ #
    # Volume actions — volumes are identified by string shortId           #
    # ------------------------------------------------------------------ #

    async def async_mount_volume(self, short_id: str) -> None:
        client = await self._get_client()
        try:
            await self.hass.async_add_executor_job(client.volumes.mount, short_id)
        except ZerobyteError as err:
            raise HomeAssistantError(f"Failed to mount volume: {err}") from err
        await self.async_request_refresh()

    async def async_unmount_volume(self, short_id: str) -> None:
        client = await self._get_client()
        try:
            await self.hass.async_add_executor_job(client.volumes.unmount, short_id)
        except ZerobyteError as err:
            raise HomeAssistantError(f"Failed to unmount volume: {err}") from err
        await self.async_request_refresh()
