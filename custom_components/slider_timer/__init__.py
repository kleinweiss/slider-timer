"""Loading of the Timer integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.service import async_register_platform_entity_service
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_SOUND_FILE,
    DEFAULT_SOUND_FILE,
    DOMAIN,
    LEGACY_KEYS,
    LEGACY_SOUND_FILE,
    SERVICE_CANCEL,
    SERVICE_PAUSE,
    SERVICE_RESUME,
    SERVICE_SET,
    SERVICE_START,
    STORAGE_VERSION,
)
from .custom_sentences import async_install_sentences
from .card import async_setup_frontend
from .sensor import DURATION_SCHEMA, START_SCHEMA
from .settings import default_duration
from .sound import async_setup_sound
from .timer import SliderTimer, store_key

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
]

SliderTimerConfigEntry = ConfigEntry[SliderTimer]

_LOGGER = logging.getLogger(__name__)

# The services target the remaining-time sensor; (name, schema, method).
SERVICES = (
    (SERVICE_START, START_SCHEMA, "async_start"),
    (SERVICE_SET, DURATION_SCHEMA, "async_set"),
    (SERVICE_PAUSE, {}, "async_pause"),
    (SERVICE_RESUME, {}, "async_resume"),
    (SERVICE_CANCEL, {}, "async_cancel"),
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services, the card and the sentence files – once.

    The services are registered here rather than per config entry, so they
    exist (and validate) even before the first timer is set up.

    The card and the expiry sound are served by the integration; the card is
    loaded by a single Lovelace resource that the integration keeps up to date
    (see card.py – never `add_extra_js_url`, which races with the dashboard
    rendering).

    The voice control sentences come from the `custom_sentences/` directory
    under the configuration directory, so ours are copied there – only when no
    such file exists yet.
    """
    for name, schema, method in SERVICES:
        async_register_platform_entity_service(
            hass,
            DOMAIN,
            name,
            entity_domain=SENSOR_DOMAIN,
            schema=schema,
            func=method,
        )

    await async_setup_frontend(hass)
    await async_install_sentences(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an older config entry.

    1.1 -> 1.2: the entity keys became English (`hatralevo` -> `remaining`,
    `ora` -> `hours`, …). Only the unique_ids change; the entity IDs, names and
    history stay. The old default sound path (a file copied into `www/`) is
    switched to the bundled sound.
    """
    if entry.version > 1:
        # A newer version than this code knows: refuse instead of guessing.
        return False

    if entry.version == 1 and entry.minor_version < 2:
        prefix = f"{entry.entry_id}_"

        @callback
        def _rename(reg_entry: er.RegistryEntry) -> dict[str, str] | None:
            if not reg_entry.unique_id.startswith(prefix):
                return None
            key = reg_entry.unique_id.removeprefix(prefix)
            if key not in LEGACY_KEYS:
                return None
            return {"new_unique_id": prefix + LEGACY_KEYS[key]}

        await er.async_migrate_entries(hass, entry.entry_id, _rename)

        data = dict(entry.data)
        options = dict(entry.options)
        for values in (data, options):
            if values.get(CONF_SOUND_FILE) == LEGACY_SOUND_FILE:
                values[CONF_SOUND_FILE] = DEFAULT_SOUND_FILE

        hass.config_entries.async_update_entry(
            entry, data=data, options=options, minor_version=2
        )
        _LOGGER.info("Timer %s migrated to version 1.2", entry.title)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: SliderTimerConfigEntry) -> bool:
    """Load one configured timer."""
    timer = SliderTimer(hass, entry.entry_id, entry.title)
    await timer.async_restore()

    # The default duration of the setting overrides the sliders only when the
    # setting itself changed (see `SliderTimer.apply_settings`); a value set on
    # the sliders survives a restart while the setting stays the same.
    # `apply_settings` only changes the default duration, never a running (or
    # paused) countdown.
    hours, minutes, seconds = default_duration(entry)
    timer.apply_settings(hours, minutes, seconds)

    entry.runtime_data = timer

    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    await async_setup_sound(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SliderTimerConfigEntry) -> bool:
    """Unload: stop the pending timers."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    entry.runtime_data.async_shutdown()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: SliderTimerConfigEntry) -> None:
    """Remove the stored state of a deleted timer.

    Without this the `slider_timer.<entry_id>` file would stay behind in the
    storage directory as an orphan after the timer is deleted.
    """
    await Store(hass, STORAGE_VERSION, store_key(entry.entry_id)).async_remove()


async def _async_entry_updated(
    hass: HomeAssistant, entry: SliderTimerConfigEntry
) -> None:
    """Settings changed (e.g. rename or sound): reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
