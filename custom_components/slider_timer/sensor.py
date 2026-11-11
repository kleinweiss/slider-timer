"""The sensor showing the remaining time – also the control entity of the timer.

The services (start / pause / resume / cancel / set) target this entity, which
is why the handler methods live on this class.
"""

from __future__ import annotations

from datetime import time as dt_time
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.script import async_validate_actions_config

from .const import (
    ATTR_HOURS,
    ATTR_MINUTES,
    ATTR_SECONDS,
    CONF_ACTIONS,
    CONF_MEDIA_PLAYER,
    CONF_SOUND_AFTER,
    CONF_SOUND_BEFORE,
    CONF_SOUND_FILE,
    DOMAIN,
    KEY_REMAINING,
    MAX_HOURS,
    MAX_MINUTES,
    MAX_SECONDS,
    STATE_IDLE,
)
from .entity import SliderTimerEntity
from .timer import SliderTimer, format_duration

# The service fields that set the duration – all optional.
DURATION_SCHEMA = {
    vol.Optional(ATTR_HOURS): vol.All(vol.Coerce(int), vol.Range(min=0, max=MAX_HOURS)),
    vol.Optional(ATTR_MINUTES): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=MAX_MINUTES)
    ),
    vol.Optional(ATTR_SECONDS): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=MAX_SECONDS)
    ),
}

# The expiry settings the caller (usually the card) may pass at start. All
# optional: whatever is not given falls back to the settings of the config
# entry. Execution happens on the server, so the card may be closed at expiry.
EXPIRY_SCHEMA = {
    vol.Optional(CONF_MEDIA_PLAYER): cv.string,
    vol.Optional(CONF_SOUND_FILE): cv.string,
    vol.Optional(CONF_SOUND_AFTER): vol.Any(None, cv.time),
    vol.Optional(CONF_SOUND_BEFORE): vol.Any(None, cv.time),
    vol.Optional(CONF_ACTIONS): cv.SCRIPT_SCHEMA,
}

# `start` accepts both the duration and the expiry settings.
START_SCHEMA = {**DURATION_SCHEMA, **EXPIRY_SCHEMA}


def _as_actions(value: Any) -> list[dict[str, Any]]:
    """Turn the expiry actions into a list (empty list if there are none)."""
    if isinstance(value, dict):
        return [value] if value else []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict) and item]


def _expiry_payload(
    media_player: str | None,
    sound_file: str | None,
    sound_after: dt_time | None,
    sound_before: dt_time | None,
    actions: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """The expiry settings passed to this run.

    Only the fields that were actually given are included; the empty string and
    the empty list are deliberate values (no sound, no actions).
    """
    payload: dict[str, Any] = {}
    if media_player is not None:
        payload[CONF_MEDIA_PLAYER] = media_player.strip()
    if sound_file is not None:
        payload[CONF_SOUND_FILE] = sound_file.strip()
    if sound_after is not None:
        payload[CONF_SOUND_AFTER] = sound_after.strftime("%H:%M:%S")
    if sound_before is not None:
        payload[CONF_SOUND_BEFORE] = sound_before.strftime("%H:%M:%S")
    if actions is not None:
        payload[CONF_ACTIONS] = _as_actions(actions)
    return payload or None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform (the services live in __init__.py)."""
    timer: SliderTimer = entry.runtime_data
    async_add_entities([SliderTimerRemainingSensor(timer)])


class SliderTimerRemainingSensor(SliderTimerEntity, SensorEntity):
    """Remaining time in H:MM:SS format.

    When idle the state is `unknown`, just like in the live YAML solution.
    """

    _attr_translation_key = KEY_REMAINING
    _attr_icon = "mdi:timer-outline"

    def __init__(self, timer: SliderTimer) -> None:
        super().__init__(timer, KEY_REMAINING)

    @property
    def native_value(self) -> str | None:
        """The remaining time while running or paused; no value when idle."""
        if self.timer.state == STATE_IDLE:
            return None
        return format_duration(self.timer.remaining)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The values in seconds and the state, for machine processing."""
        return {
            "status": self.timer.state,
            "remaining_seconds": int(self.timer.remaining.total_seconds()),
            "duration_seconds": int(self.timer.duration.total_seconds()),
            "ends_at": self.timer.ends_at,
        }

    # -------------------------------------------------------------- services

    async def async_start(
        self,
        hours: int | None = None,
        minutes: int | None = None,
        seconds: int | None = None,
        media_player: str | None = None,
        sound_file: str | None = None,
        sound_after: dt_time | None = None,
        sound_before: dt_time | None = None,
        actions: list[dict[str, Any]] | None = None,
    ) -> None:
        """Start; without a duration the default duration is used.

        The expiry settings are optional: whatever you leave out falls back to
        the settings of the config entry. The card passes them at start, so
        execution happens on the server – the card may be closed at expiry.

        A zero length is refused: such a timer would expire in the very moment it
        starts, playing the sound and running the actions immediately. A bad
        action list is refused as well, before the timer starts.
        """
        duration = self.timer.resolve_duration(hours, minutes, seconds)
        if duration.total_seconds() <= 0:
            raise ServiceValidationError(
                "The duration must be longer than zero.",
                translation_domain=DOMAIN,
                translation_key="zero_duration",
            )
        payload = _expiry_payload(
            media_player, sound_file, sound_after, sound_before, actions
        )
        if payload and payload.get(CONF_ACTIONS):
            await self._async_validate_actions(payload[CONF_ACTIONS])
        await self.timer.async_start(duration, expiry=payload)

    async def async_set(
        self,
        hours: int | None = None,
        minutes: int | None = None,
        seconds: int | None = None,
    ) -> None:
        """Set the default duration without starting."""
        if hours is None and minutes is None and seconds is None:
            raise ServiceValidationError(
                "At least one of hours, minutes or seconds is required.",
                translation_domain=DOMAIN,
                translation_key="no_duration",
            )
        self.timer.set_default(hours=hours, minutes=minutes, seconds=seconds)

    async def async_pause(self) -> None:
        """Pause the timer."""
        await self.timer.async_pause()

    async def async_resume(self) -> None:
        """Resume a paused timer."""
        await self.timer.async_resume()

    async def async_cancel(self) -> None:
        """Cancel the timer: it goes back to the idle state."""
        await self.timer.async_cancel()

    # ------------------------------------------------------------- private

    async def _async_validate_actions(self, actions: list[dict[str, Any]]) -> None:
        """Refuse an invalid action list before the timer starts.

        `async_validate_actions_config` resolves the devices, entities and
        conditions of the actions, so the caller gets the reason straight away
        instead of a failure at the moment of expiry.
        """
        try:
            await async_validate_actions_config(self.hass, actions)
        except Exception as err:  # noqa: BLE001 - any validation error type
            raise ServiceValidationError(
                f"The expiry actions are invalid: {err}",
                translation_domain=DOMAIN,
                translation_key="invalid_actions",
                translation_placeholders={"error": str(err)},
            ) from err
