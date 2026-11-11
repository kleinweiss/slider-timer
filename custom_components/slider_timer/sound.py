"""Expiry sound and actions.

The usual Home Assistant action syntax is used for the actions
(`helpers.script.Script`), so targets, data and conditions all work.

The settings may change per run (the card passes them at start), which is why
the decision is made at the moment of expiry: the value passed to the run comes
first, the config entry is only the fallback. Execution happens on the server,
so the card may be closed at expiry.

The time window applies to both the sound and the actions: outside the window
nothing runs. If the start and the end are the same, there is no time limit.
"""

from __future__ import annotations

from datetime import time as dt_time
import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntityFeature,
    async_process_play_media_url,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.script import (
    SCRIPT_MODE_PARALLEL,
    Script,
    async_validate_actions_config,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACTIONS,
    CONF_MEDIA_PLAYER,
    CONF_SOUND_AFTER,
    CONF_SOUND_BEFORE,
    CONF_SOUND_FILE,
    DEFAULT_SOUND_AFTER,
    DEFAULT_SOUND_BEFORE,
    DEFAULT_SOUND_FILE,
    DOMAIN,
    EVENT_FINISHED,
    MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
    SOUND_CONTENT_TYPE,
)
from .settings import get_setting

_LOGGER = logging.getLogger(__name__)

ATTR_MEDIA_CONTENT_ID = "media_content_id"
ATTR_MEDIA_CONTENT_TYPE = "media_content_type"
ATTR_MEDIA_ANNOUNCE = "announce"

# Name and running description of the script that runs the expiry actions
# (they show up in the logbook and in the running scripts). Home Assistant
# cannot translate script names, so the language of the instance
# (`hass.config.language`) picks the wording; anything unknown falls back to
# English.
ACTION_TITLES: dict[str, tuple[str, str]] = {
    "en": ("Expiry actions of {name}", "Expiry actions of {name}"),
    "hu": ("{name} lejáratkori műveletek", "{name} – lejáratkori műveletek"),
}


def _action_titles(hass: HomeAssistant, name: str) -> tuple[str, str]:
    """The script name and running description for the expiry actions."""
    language = str(hass.config.language or "").casefold()
    key = "hu" if language.startswith("hu") else "en"
    script_name, running_description = ACTION_TITLES[key]
    return script_name.format(name=name), running_description.format(name=name)


def _setting(entry: ConfigEntry, key: str, default: str) -> str:
    """A non-empty text setting, or the default."""
    value = get_setting(entry, key, default)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _media_player(entry: ConfigEntry) -> str | None:
    """The configured media player, or None if there is none."""
    value = get_setting(entry, CONF_MEDIA_PLAYER)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _actions(entry: ConfigEntry) -> list[dict[str, Any]]:
    """The configured expiry actions (empty list if there are none)."""
    value = get_setting(entry, CONF_ACTIONS)
    if isinstance(value, dict):
        return [value] if value else []
    if not isinstance(value, list):
        return []
    return [
        item
        for item in value
        if isinstance(item, dict) and item
    ]


def _parse_time(value: object, fallback: str) -> dt_time:
    """Turn a `"07:00"` / `"07:00:00"` setting into an hour:minute:second value."""
    for candidate in (value, fallback):
        if isinstance(candidate, str) and candidate.strip():
            parsed = dt_util.parse_time(candidate.strip())
            if parsed is not None:
                return parsed
    return dt_time(0, 0)


def _resolve_media_player(entry: ConfigEntry, run: dict[str, Any]) -> str | None:
    """The media player of this run, otherwise the entry setting.

    If the run deliberately gave it as empty (the card has no sound), there is
    no player – the entry setting does not apply in that case.
    """
    if CONF_MEDIA_PLAYER in run:
        value = run.get(CONF_MEDIA_PLAYER)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None
    return _media_player(entry)


def _resolve_sound_file(entry: ConfigEntry, run: dict[str, Any]) -> str:
    """The sound file of this run, otherwise the entry setting (default file)."""
    if CONF_SOUND_FILE in run:
        value = run.get(CONF_SOUND_FILE)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return DEFAULT_SOUND_FILE
    return _setting(entry, CONF_SOUND_FILE, DEFAULT_SOUND_FILE)


def _resolve_actions(entry: ConfigEntry, run: dict[str, Any]) -> list[dict[str, Any]]:
    """The actions of this run, otherwise the entry settings (empty: none)."""
    if CONF_ACTIONS in run:
        value = run.get(CONF_ACTIONS)
        if isinstance(value, dict):
            return [value] if value else []
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict) and item]
    return _actions(entry)


def _resolve_time(
    entry: ConfigEntry, run: dict[str, Any], key: str, default: str
) -> dt_time:
    """One end of the time window: the run value, otherwise the entry setting."""
    if key in run:
        return _parse_time(run.get(key), default)
    return _parse_time(get_setting(entry, key, default), default)


def _in_window(now: dt_time, after: dt_time, before: dt_time) -> bool:
    """Is it inside the time window (inclusive start, exclusive end)?"""
    if after == before:
        # Start = end: there is no time limit.
        return True
    if after < before:
        return after <= now < before
    # A window that wraps around, e.g. 22:00 - 06:00.
    return now >= after or now < before


def _async_play_sound(
    hass: HomeAssistant, entry: ConfigEntry, media_player: str, sound_file: str
) -> None:
    """Play the expiry sound (in announce mode if the player supports it)."""
    try:
        media_id = async_process_play_media_url(hass, sound_file)
    except HomeAssistantError as err:
        media_id = sound_file
        _LOGGER.warning(
            "Timer (%s): the sound URL cannot be resolved (%s)", entry.title, err
        )

    data: dict[str, Any] = {
        ATTR_ENTITY_ID: media_player,
        ATTR_MEDIA_CONTENT_ID: media_id,
        ATTR_MEDIA_CONTENT_TYPE: SOUND_CONTENT_TYPE,
    }
    state = hass.states.get(media_player)
    if state is not None and state.attributes.get("supported_features", 0) & (
        MediaPlayerEntityFeature.MEDIA_ANNOUNCE
    ):
        data[ATTR_MEDIA_ANNOUNCE] = True

    _LOGGER.debug(
        "Timer expired (%s): sound on %s (announce=%s)",
        entry.title,
        media_player,
        ATTR_MEDIA_ANNOUNCE in data,
    )
    hass.async_create_task(
        hass.services.async_call(
            MEDIA_PLAYER_DOMAIN, SERVICE_PLAY_MEDIA, data, blocking=False
        )
    )


async def _async_run_actions(
    hass: HomeAssistant,
    entry: ConfigEntry,
    actions: list[dict[str, Any]],
    context: Context | None,
) -> None:
    """Run the expiry actions.

    The actions can change from run to run, so they are validated and the
    `Script` is built here, at the moment of expiry, and is released when the
    run finishes. Validation comes first: a bad action list gets one clear log
    line instead of a traceback.

    The entry stores the raw, storable form (what the `ActionSelector` gives
    back), which is *not* the same as the normalised action list the runner
    needs, so there are two steps: `SCRIPT_SCHEMA` normalises, and the running
    Home Assistant validates the result. (The actions passed at start are
    already normalised and validated by the `start` service schema; this covers
    the ones stored in the settings.) Only the raw form is ever stored.
    """
    try:
        actions = await async_validate_actions_config(hass, cv.SCRIPT_SCHEMA(actions))
    except Exception as err:  # noqa: BLE001 - any validation error type
        _LOGGER.error(
            "Timer expired (%s): the expiry actions are invalid, nothing runs: %s",
            entry.title,
            err,
        )
        return

    script_name, running_description = _action_titles(hass, entry.title)
    script = Script(
        hass,
        actions,
        script_name,
        DOMAIN,
        running_description=running_description,
        script_mode=SCRIPT_MODE_PARALLEL,
        max_exceeded="silent",
    )
    _LOGGER.debug(
        "Timer expired (%s): running %d action(s)", entry.title, len(actions)
    )
    run = hass.async_create_task(script.async_run(context=context))
    run.add_done_callback(lambda _task: hass.async_create_task(script.async_unload()))


async def async_setup_sound(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Wire the expiry sound and actions to this config entry.

    The settings may change run by run (the card passes them at start), so we
    always subscribe and decide at the moment of expiry: the value passed to the
    run comes first, the config entry is only the fallback.
    """

    @callback
    def _async_expiry(event: Event) -> None:
        """Expiry: sound and/or actions, if the window is open."""
        if event.data.get("entry_id") != entry.entry_id:
            return

        timer = getattr(entry, "runtime_data", None)
        run = timer.run_expiry if timer is not None else {}

        after = _resolve_time(entry, run, CONF_SOUND_AFTER, DEFAULT_SOUND_AFTER)
        before = _resolve_time(entry, run, CONF_SOUND_BEFORE, DEFAULT_SOUND_BEFORE)
        if not _in_window(dt_util.now().time(), after, before):
            _LOGGER.debug(
                "Timer expired (%s): outside the time window, no sound and no actions",
                entry.title,
            )
            return

        media_player = _resolve_media_player(entry, run)
        if media_player is not None:
            _async_play_sound(
                hass, entry, media_player, _resolve_sound_file(entry, run)
            )

        actions = _resolve_actions(entry, run)
        if actions:
            hass.async_create_task(
                _async_run_actions(hass, entry, actions, event.context)
            )

    entry.async_on_unload(hass.bus.async_listen(EVENT_FINISHED, _async_expiry))
