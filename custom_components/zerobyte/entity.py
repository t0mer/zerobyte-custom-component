from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZerobyteCoordinator


class ZerobyteEntity(CoordinatorEntity[ZerobyteCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZerobyteCoordinator,
        device_id: str,
        device_name: str,
        device_model: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            model=device_model,
            manufacturer="Zerobyte",
            via_device=(DOMAIN, coordinator.entry_id),
        )
