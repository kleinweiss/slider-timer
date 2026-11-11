"""Shared entity base for the Timer integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .timer import SliderTimer


class SliderTimerEntity(Entity):
    """An entity that belongs to one timer.

    Every entity belongs to the same device (`entry_id`) and updates as a
    listener of the `timer` object.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, timer: SliderTimer, key: str) -> None:
        self.timer = timer
        self._attr_unique_id = f"{timer.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, timer.entry_id)},
            name=timer.name,
            manufacturer="Timer",
            model="Countdown timer",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to the changes of the timer."""
        await super().async_added_to_hass()
        self.async_on_remove(self.timer.async_add_listener(self.async_write_ha_state))
