"""Setup and settings from the user interface."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.helpers.script import async_validate_actions_config
from homeassistant.util import slugify

from .const import (
    CONF_ACTIONS,
    CONF_DEFAULT_HOURS,
    CONF_DEFAULT_MINUTES,
    CONF_DEFAULT_SECONDS,
    CONF_MEDIA_PLAYER,
    CONF_NAME,
    CONF_SOUND_AFTER,
    CONF_SOUND_BEFORE,
    CONF_SOUND_FILE,
    DEFAULT_HOURS,
    DEFAULT_MINUTES,
    DEFAULT_NAME,
    DEFAULT_SECONDS,
    DEFAULT_SOUND_AFTER,
    DEFAULT_SOUND_BEFORE,
    DEFAULT_SOUND_FILE,
    DOMAIN,
    MAX_HOURS,
    MAX_MINUTES,
    MAX_SECONDS,
    MEDIA_PLAYER_DOMAIN,
)

from .settings import get_setting


def _defaults(entry: ConfigEntry | None = None) -> dict[str, Any]:
    """The initial values of the form (at setup, or the current settings)."""
    if entry is None:
        return {
            CONF_NAME: DEFAULT_NAME,
            CONF_DEFAULT_HOURS: DEFAULT_HOURS,
            CONF_DEFAULT_MINUTES: DEFAULT_MINUTES,
            CONF_DEFAULT_SECONDS: DEFAULT_SECONDS,
            CONF_MEDIA_PLAYER: None,
            CONF_SOUND_FILE: DEFAULT_SOUND_FILE,
            CONF_SOUND_AFTER: DEFAULT_SOUND_AFTER,
            CONF_SOUND_BEFORE: DEFAULT_SOUND_BEFORE,
            CONF_ACTIONS: [],
        }
    return {
        CONF_NAME: entry.title,
        CONF_DEFAULT_HOURS: get_setting(entry, CONF_DEFAULT_HOURS, DEFAULT_HOURS),
        CONF_DEFAULT_MINUTES: get_setting(entry, CONF_DEFAULT_MINUTES, DEFAULT_MINUTES),
        CONF_DEFAULT_SECONDS: get_setting(entry, CONF_DEFAULT_SECONDS, DEFAULT_SECONDS),
        CONF_MEDIA_PLAYER: get_setting(entry, CONF_MEDIA_PLAYER),
        CONF_SOUND_FILE: get_setting(entry, CONF_SOUND_FILE) or DEFAULT_SOUND_FILE,
        CONF_SOUND_AFTER: get_setting(entry, CONF_SOUND_AFTER) or DEFAULT_SOUND_AFTER,
        CONF_SOUND_BEFORE: get_setting(entry, CONF_SOUND_BEFORE)
        or DEFAULT_SOUND_BEFORE,
        CONF_ACTIONS: _as_actions(get_setting(entry, CONF_ACTIONS)),
    }


def _schema(current: dict[str, Any]) -> vol.Schema:
    """The settings form – the same at setup and afterwards."""
    keys: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=current[CONF_NAME]): str,
        vol.Optional(
            CONF_DEFAULT_HOURS, default=current[CONF_DEFAULT_HOURS]
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=MAX_HOURS)),
        vol.Optional(
            CONF_DEFAULT_MINUTES, default=current[CONF_DEFAULT_MINUTES]
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=MAX_MINUTES)),
        vol.Optional(
            CONF_DEFAULT_SECONDS, default=current[CONF_DEFAULT_SECONDS]
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=MAX_SECONDS)),
        vol.Optional(
            CONF_SOUND_FILE, default=current[CONF_SOUND_FILE]
        ): selector.TextSelector(),
        vol.Optional(
            CONF_SOUND_AFTER, default=current[CONF_SOUND_AFTER]
        ): selector.TimeSelector(),
        vol.Optional(
            CONF_SOUND_BEFORE, default=current[CONF_SOUND_BEFORE]
        ): selector.TimeSelector(),
    }

    # The media player may be empty (no sound); in that case we give no default.
    media_player = current.get(CONF_MEDIA_PLAYER)
    entity_selector = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=MEDIA_PLAYER_DOMAIN)
    )
    if isinstance(media_player, str) and media_player.strip():
        keys[vol.Optional(CONF_MEDIA_PLAYER, default=media_player)] = entity_selector
    else:
        keys[vol.Optional(CONF_MEDIA_PLAYER)] = entity_selector

    # Actions on expiry: the usual HA action list (action + target + data).
    keys[vol.Optional(CONF_ACTIONS, default=current[CONF_ACTIONS])] = (
        selector.ActionSelector()
    )

    return vol.Schema(keys)


def _as_actions(value: Any) -> list[dict[str, Any]]:
    """The raw, storable form of the actions (the selector gives a list).

    This is what the config entry keeps. The normalised action list is produced
    only at validation and at execution time (`SCRIPT_SCHEMA`, then the check
    against the running Home Assistant).
    """
    if isinstance(value, dict):
        return [value] if value else []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict) and item]


def _as_int(value: Any, fallback: int) -> int:
    """Turn a value coming from the form into an integer."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value.strip()))
        except ValueError:
            return fallback
    return fallback


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalise the form values (the entry stores them as JSON)."""
    media_player = user_input.get(CONF_MEDIA_PLAYER)
    if isinstance(media_player, str) and media_player.strip():
        media_player = media_player.strip()
    else:
        media_player = None

    sound_file = user_input.get(CONF_SOUND_FILE)
    if isinstance(sound_file, str) and sound_file.strip():
        sound_file = sound_file.strip()
    else:
        sound_file = DEFAULT_SOUND_FILE

    after = user_input.get(CONF_SOUND_AFTER)
    before = user_input.get(CONF_SOUND_BEFORE)

    return {
        CONF_NAME: str(user_input.get(CONF_NAME, "")).strip(),
        CONF_DEFAULT_HOURS: _as_int(user_input.get(CONF_DEFAULT_HOURS), DEFAULT_HOURS),
        CONF_DEFAULT_MINUTES: _as_int(
            user_input.get(CONF_DEFAULT_MINUTES), DEFAULT_MINUTES
        ),
        CONF_DEFAULT_SECONDS: _as_int(
            user_input.get(CONF_DEFAULT_SECONDS), DEFAULT_SECONDS
        ),
        CONF_MEDIA_PLAYER: media_player,
        CONF_SOUND_FILE: sound_file,
        CONF_SOUND_AFTER: after if isinstance(after, str) and after.strip() else None,
        CONF_SOUND_BEFORE: before if isinstance(before, str) and before.strip() else None,
        CONF_ACTIONS: _as_actions(user_input.get(CONF_ACTIONS)),
    }


async def _actions_error(
    hass: HomeAssistant, actions: list[dict[str, Any]]
) -> str | None:
    """Validate the actions of the form: the reason of the error, or None.

    The entry stores the raw, storable form (what the `ActionSelector` gives
    back), so the same two steps run as at expiry: `SCRIPT_SCHEMA` normalises it
    into an action list, and the running Home Assistant validates that. A bad
    list therefore does not get stored unnoticed: the form shows the reason
    instead.
    """
    if not actions:
        return None
    try:
        await async_validate_actions_config(hass, cv.SCRIPT_SCHEMA(actions))
    except Exception as err:  # noqa: BLE001 - any validation error type
        return str(err)
    return None


def _name_in_use(
    hass: HomeAssistant, name: str, skip_entry_id: str | None = None
) -> bool:
    """Whether another timer is already using this name.

    The comparison is the entity ID form (`slugify`): the accent and case
    differences disappear, so "Hálószoba" and "Haloszoba" count as the same
    name. Those are exactly the names the entity IDs, the card and the voice
    matching would confuse.
    """
    wanted = slugify(name)
    return any(
        entry.entry_id != skip_entry_id and slugify(entry.title) == wanted
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


class SliderTimerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a new timer.

    The entry carries no unique_id: the timer is identified by its entry_id
    (the entity unique_ids are built from that), so a unique_id derived from
    the name would only go stale on rename - which is exactly what used to
    block a freed name and let a duplicate one through. The name still has to
    be unique, because the card and the voice matching pick a timer by name;
    both flows check that instead.
    """

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Name, default duration and the expiry sound."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            data = _clean(user_input)
            if not data[CONF_NAME]:
                errors[CONF_NAME] = "name_required"
            elif _name_in_use(self.hass, data[CONF_NAME]):
                errors[CONF_NAME] = "name_exists"
            elif (error := await _actions_error(self.hass, data[CONF_ACTIONS])):
                errors[CONF_ACTIONS] = "invalid_actions"
                placeholders["error"] = error
            else:
                return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(_defaults()),
            errors=errors,
            description_placeholders=placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SliderTimerOptionsFlow()


class SliderTimerOptionsFlow(OptionsFlow):
    """The settings of an installed timer (rename, sound).

    Renaming does not change the entity IDs, only the displayed name of the
    device and of the entities. A name that is already in use (in the entity ID
    form) is refused, otherwise two timers could end up with the same name.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            data = _clean(user_input)
            if not data[CONF_NAME]:
                errors[CONF_NAME] = "name_required"
            elif _name_in_use(
                self.hass, data[CONF_NAME], self.config_entry.entry_id
            ):
                errors[CONF_NAME] = "name_exists"
            elif (error := await _actions_error(self.hass, data[CONF_ACTIONS])):
                errors[CONF_ACTIONS] = "invalid_actions"
                placeholders["error"] = error
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, title=data[CONF_NAME]
                )
                return self.async_create_entry(title="", data=data)

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(_defaults(self.config_entry)),
            errors=errors,
            description_placeholders=placeholders,
        )
