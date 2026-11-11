"""Reading the settings.

An earlier version used `entry.options` alone for renaming; from now on both the
`entry.data` stored at setup and the later `entry.options` count: the former is
the setup, the latter is the values of the settings form. When a key is present
in both, options wins.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_DEFAULT_HOURS,
    CONF_DEFAULT_MINUTES,
    CONF_DEFAULT_SECONDS,
    DEFAULT_HOURS,
    DEFAULT_MINUTES,
    DEFAULT_SECONDS,
)


def get_setting(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """A setting: options first, then data, finally the default."""
    if key in entry.options:
        return entry.options[key]
    if key in entry.data:
        return entry.data[key]
    return default


def _as_int(value: Any, fallback: int) -> int:
    """Turn a stored (textual) value into an integer, safely."""
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value.strip()))
        except ValueError:
            return fallback
    return fallback


def default_duration(entry: ConfigEntry) -> tuple[int, int, int]:
    """The default duration of the settings (hours, minutes, seconds).

    The settings override the sliders only when the setting itself changed:
    `SliderTimer.apply_settings` compares this value with the one applied last
    time (kept in the store) and only writes when they differ. The state of a
    running or paused timer is restored independently of this value.
    """
    return (
        _as_int(get_setting(entry, CONF_DEFAULT_HOURS), DEFAULT_HOURS),
        _as_int(get_setting(entry, CONF_DEFAULT_MINUTES), DEFAULT_MINUTES),
        _as_int(get_setting(entry, CONF_DEFAULT_SECONDS), DEFAULT_SECONDS),
    )
