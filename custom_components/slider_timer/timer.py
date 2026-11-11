"""The state machine of the timer.

This class keeps track of the state (idle / active / paused), the remaining time
and the moment of expiry. The entities only display what they see here, and they
subscribe to it as change listeners.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_HOURS,
    DEFAULT_MINUTES,
    DEFAULT_SECONDS,
    DOMAIN,
    EVENT_CANCELLED,
    EVENT_FINISHED,
    EVENT_PAUSED,
    EVENT_RESUMED,
    EVENT_STARTED,
    STATE_ACTIVE,
    STATE_IDLE,
    STATE_PAUSED,
    STORAGE_VERSION,
)

# The remaining time refreshes every second while the timer is running.
TICK_INTERVAL = timedelta(seconds=1)


def format_duration(value: timedelta) -> str:
    """H:MM:SS format – the hours are not padded with zeros."""
    total = max(0, int(value.total_seconds()))
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def _as_float(value: object) -> float:
    """Turn a stored value into a number, safely."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0


def store_key(entry_id: str) -> str:
    """The key of the `Store` that holds one timer's state.

    The state is written here and deleted when the timer is removed, so the key
    is built in one place only.
    """
    return f"{DOMAIN}.{entry_id}"


class SliderTimer:
    """The runtime state of one configured timer."""

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.name = name

        self._store: Store[dict] = Store(hass, STORAGE_VERSION, store_key(entry_id))
        self._listeners: list[CALLBACK_TYPE] = []
        self._unsub_finish: CALLBACK_TYPE | None = None
        self._unsub_tick: CALLBACK_TYPE | None = None

        self._state: str = STATE_IDLE
        self._duration: timedelta = timedelta()
        self._remaining: timedelta = timedelta()
        self._ends_at: datetime | None = None

        # The expiry settings passed to the current run (the card). Empty when
        # the caller gave nothing – in that case the settings of the config
        # entry apply.
        self._run_expiry: dict[str, Any] = {}

        # The values of the number entities: these make up the default duration.
        self._default_hours: int = DEFAULT_HOURS
        self._default_minutes: int = DEFAULT_MINUTES
        self._default_seconds: int = DEFAULT_SECONDS

        # The default duration of the settings as applied last time. The
        # integration writes the setting onto the number entities only when it
        # differs from this value (see `apply_settings`), so a slider value the
        # user set survives a restart while the setting stays unchanged.
        self._applied_settings: tuple[int, int, int] | None = None

    # ------------------------------------------------------------------- state

    @property
    def state(self) -> str:
        """idle / active / paused."""
        return self._state

    @property
    def duration(self) -> timedelta:
        """The total duration set last."""
        return self._duration

    @property
    def remaining(self) -> timedelta:
        """Remaining time (counted from the expiry while running)."""
        if self._state == STATE_ACTIVE and self._ends_at is not None:
            return max(timedelta(), self._ends_at - dt_util.utcnow())
        return self._remaining

    @property
    def ends_at(self) -> datetime | None:
        """The moment of expiry, or None when it is not running."""
        return self._ends_at

    @property
    def run_expiry(self) -> dict[str, Any]:
        """The expiry settings passed to the current run.

        It only contains the keys the caller (the card) gave; for the missing
        ones the settings of the config entry apply.
        """
        return self._run_expiry

    @property
    def default_hours(self) -> int:
        return self._default_hours

    @property
    def default_minutes(self) -> int:
        return self._default_minutes

    @property
    def default_seconds(self) -> int:
        return self._default_seconds

    @property
    def default_duration(self) -> timedelta:
        """The default duration built from the number entities."""
        return timedelta(
            hours=self._default_hours,
            minutes=self._default_minutes,
            seconds=self._default_seconds,
        )

    @property
    def applied_settings(self) -> tuple[int, int, int] | None:
        """The default duration of the settings as applied last time.

        None when the setting was never applied yet (a fresh timer).
        """
        return self._applied_settings

    def resolve_duration(
        self,
        hours: int | None = None,
        minutes: int | None = None,
        seconds: int | None = None,
    ) -> timedelta:
        """The duration given in the service, or the number entities.

        When no field is given at all, the default duration is used. When at
        least one field is given, the missing ones count as zero.
        """
        if hours is None and minutes is None and seconds is None:
            return self.default_duration
        return timedelta(hours=hours or 0, minutes=minutes or 0, seconds=seconds or 0)

    # --------------------------------------------------------------- listeners

    @callback
    def async_add_listener(self, update_callback: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """An entity subscribing to the state changes."""
        self._listeners.append(update_callback)

        @callback
        def remove_listener() -> None:
            self._listeners.remove(update_callback)

        return remove_listener

    @callback
    def async_update_listeners(self) -> None:
        """Notify every listener."""
        for update_callback in list(self._listeners):
            update_callback()

    # --------------------------------------------------------------- defaults

    @callback
    def set_default(
        self,
        hours: int | None = None,
        minutes: int | None = None,
        seconds: int | None = None,
    ) -> None:
        """Set the values of the number entities (and of the `set` service)."""
        if hours is not None:
            self._default_hours = max(0, int(hours))
        if minutes is not None:
            self._default_minutes = max(0, int(minutes))
        if seconds is not None:
            self._default_seconds = max(0, int(seconds))
        self.async_update_listeners()
        self.hass.async_create_task(self._async_save())

    @callback
    def apply_settings(self, hours: int, minutes: int, seconds: int) -> bool:
        """Apply the default duration of the settings, when it really changed.

        The setting overwrites the number entities (the card's sliders) only
        when it differs from the value applied the last time; a value set on
        the sliders therefore survives a restart while the setting stays the
        same. True when the setting was applied (the sliders moved).
        """
        wanted = (int(hours), int(minutes), int(seconds))
        if self._applied_settings == wanted:
            return False
        self._applied_settings = wanted
        self.set_default(hours=wanted[0], minutes=wanted[1], seconds=wanted[2])
        return True

    # -------------------------------------------------------------- operations

    async def async_start(
        self, duration: timedelta, expiry: dict[str, Any] | None = None
    ) -> None:
        """Start; it overwrites a running timer.

        `expiry` is the expiry settings passed by the caller (usually the card);
        a new run always takes the current value (passing an empty dict means
        the settings of the config entry apply).
        """
        self._cancel_handles()
        self._run_expiry = dict(expiry) if expiry else {}
        self._duration = duration
        self._remaining = duration
        self._ends_at = dt_util.utcnow() + duration
        self._state = STATE_ACTIVE
        self._schedule()
        self.async_update_listeners()
        await self._async_save()
        self._fire(EVENT_STARTED)

    async def async_pause(self) -> bool:
        """Pause. False when it was not running."""
        if self._state != STATE_ACTIVE or self._ends_at is None:
            return False
        now = dt_util.utcnow()
        self._remaining = max(timedelta(), self._ends_at - now)
        self._cancel_handles()
        self._ends_at = None
        self._state = STATE_PAUSED
        self.async_update_listeners()
        await self._async_save()
        self._fire(EVENT_PAUSED)
        return True

    async def async_resume(self) -> bool:
        """Resume from a paused state. False when there was nothing to resume."""
        if self._state != STATE_PAUSED or self._remaining.total_seconds() <= 0:
            return False
        self._ends_at = dt_util.utcnow() + self._remaining
        self._state = STATE_ACTIVE
        self._schedule()
        self.async_update_listeners()
        await self._async_save()
        self._fire(EVENT_RESUMED)
        return True

    async def async_cancel(self) -> None:
        """Cancel: the timer goes back to the idle state."""
        self._cancel_handles()
        self._ends_at = None
        self._remaining = timedelta()
        self._state = STATE_IDLE
        self.async_update_listeners()
        await self._async_save()
        self._fire(EVENT_CANCELLED)

    # ----------------------------------------------------------- internal hooks

    @callback
    def _schedule(self) -> None:
        """Set up the expiry listener and the one-second tick."""
        assert self._ends_at is not None
        self._unsub_finish = async_track_point_in_utc_time(
            self.hass, self._async_finished, self._ends_at
        )
        self._unsub_tick = async_track_time_interval(
            self.hass, self._async_tick, TICK_INTERVAL
        )

    @callback
    def _cancel_handles(self) -> None:
        """Stop the pending handles."""
        if self._unsub_finish is not None:
            self._unsub_finish()
            self._unsub_finish = None
        if self._unsub_tick is not None:
            self._unsub_tick()
            self._unsub_tick = None

    @callback
    def _async_tick(self, now: datetime) -> None:
        """Refresh every second (the remaining time counts from the expiry)."""
        self.async_update_listeners()

    @callback
    def _async_finished(self, now: datetime) -> None:
        """The moment of expiry."""
        self._cancel_handles()
        self._ends_at = None
        self._remaining = timedelta()
        self._state = STATE_IDLE
        self.async_update_listeners()
        self.hass.async_create_task(self._async_save())
        self._fire(EVENT_FINISHED)

    @callback
    def _fire(self, event_type: str) -> None:
        """Fire an event on the event bus."""
        self.hass.bus.async_fire(
            event_type,
            {
                "entry_id": self.entry_id,
                "name": self.name,
                "duration": int(self._duration.total_seconds()),
                "remaining": int(self._remaining.total_seconds()),
                "ends_at": self._ends_at.isoformat()
                if self._ends_at is not None
                else None,
            },
        )

    @callback
    def async_shutdown(self) -> None:
        """Called while the integration is being unloaded."""
        self._cancel_handles()
        self._listeners.clear()

    # ---------------------------------------------------------------- storage

    async def _async_save(self) -> None:
        """Save the state so it can be restored after a restart."""
        await self._store.async_save(
            {
                "state": self._state,
                "duration": self._duration.total_seconds(),
                "remaining": self._remaining.total_seconds(),
                "ends_at": self._ends_at.isoformat() if self._ends_at else None,
                "default_hours": self._default_hours,
                "default_minutes": self._default_minutes,
                "default_seconds": self._default_seconds,
                "applied_settings": list(self._applied_settings)
                if self._applied_settings is not None
                else None,
                "run_expiry": self._run_expiry or None,
            }
        )

    async def async_restore(self) -> bool:
        """Restore after Home Assistant has been restarted.

        It returns False when there was no stored state yet (in that case the
        default duration from setup may apply).
        """
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return False

        self._default_hours = int(_as_float(data.get("default_hours")))
        self._default_minutes = int(_as_float(data.get("default_minutes")))
        self._default_seconds = int(_as_float(data.get("default_seconds")))

        # The default duration of the settings as applied last time: it decides
        # on load whether the setting still overrides the sliders.
        saved_applied = data.get("applied_settings")
        if (
            isinstance(saved_applied, (list, tuple))
            and len(saved_applied) == 3
        ):
            self._applied_settings = (
                int(_as_float(saved_applied[0])),
                int(_as_float(saved_applied[1])),
                int(_as_float(saved_applied[2])),
            )

        # The expiry settings passed to the run survive the restart too: if the
        # timer expires in the meantime, the same sound plays.
        saved_expiry = data.get("run_expiry")
        if isinstance(saved_expiry, dict):
            self._run_expiry = saved_expiry

        self._duration = timedelta(seconds=_as_float(data.get("duration")))
        saved_state = data.get("state")
        ends_at_raw = data.get("ends_at")

        if saved_state == STATE_ACTIVE and isinstance(ends_at_raw, str):
            ends_at = dt_util.parse_datetime(ends_at_raw)
            now = dt_util.utcnow()
            if ends_at is not None and ends_at > now:
                # Still running: continue, the remaining time counts from the expiry.
                self._ends_at = ends_at
                self._remaining = ends_at - now
                self._state = STATE_ACTIVE
                self._schedule()
                return True
            # It expired during the outage: start idle, without an event
            # (so no sound plays after a restart).
            return True

        if saved_state == STATE_PAUSED:
            remaining = timedelta(seconds=_as_float(data.get("remaining")))
            if remaining.total_seconds() > 0:
                self._remaining = remaining
                self._state = STATE_PAUSED
        return True
