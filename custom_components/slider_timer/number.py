"""Hours / Minutes / Seconds – setting the default duration.

These entities replace the input_number helpers of the YAML solution. The timer
object is the single source of the value, so the `set` service updates them too,
and the values survive a restart.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    KEY_HOURS,
    KEY_MINUTES,
    KEY_SECONDS,
    MAX_HOURS,
    MAX_MINUTES,
    MAX_SECONDS,
)
from .entity import SliderTimerEntity
from .timer import SliderTimer

# (entity key = translation key, attribute of the timer, service key, maximum).
# The displayed name comes from translations/*.json.
NUMBERS: tuple[tuple[str, str, str, int], ...] = (
    (KEY_HOURS, "default_hours", "hours", MAX_HOURS),
    (KEY_MINUTES, "default_minutes", "minutes", MAX_MINUTES),
    (KEY_SECONDS, "default_seconds", "seconds", MAX_SECONDS),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    timer: SliderTimer = entry.runtime_data
    async_add_entities(
        SliderTimerNumber(timer, key, attribute, service_key, maximum)
        for key, attribute, service_key, maximum in NUMBERS
    )


class SliderTimerNumber(SliderTimerEntity, NumberEntity):
    """One component of the default duration."""

    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer-cog-outline"

    def __init__(
        self,
        timer: SliderTimer,
        key: str,
        attribute: str,
        service_key: str,
        maximum: int,
    ) -> None:
        super().__init__(timer, key)
        self._attr_translation_key = key
        self._attr_native_max_value = maximum
        self._attribute = attribute
        self._service_key = service_key

    @property
    def native_value(self) -> float:
        return float(getattr(self.timer, self._attribute))

    async def async_set_native_value(self, value: float) -> None:
        self.timer.set_default(**{self._service_key: int(value)})
