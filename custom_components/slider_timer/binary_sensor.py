"""Whether the timer is active (running or paused)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import KEY_ACTIVE, STATE_IDLE
from .entity import SliderTimerEntity
from .timer import SliderTimer


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    timer: SliderTimer = entry.runtime_data
    async_add_entities([SliderTimerActiveBinarySensor(timer)])


class SliderTimerActiveBinarySensor(SliderTimerEntity, BinarySensorEntity):
    """On: running or paused. Off: idle."""

    _attr_translation_key = KEY_ACTIVE
    _attr_icon = "mdi:timer-sand"

    def __init__(self, timer: SliderTimer) -> None:
        super().__init__(timer, KEY_ACTIVE)

    @property
    def is_on(self) -> bool:
        return self.timer.state != STATE_IDLE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"status": self.timer.state}
