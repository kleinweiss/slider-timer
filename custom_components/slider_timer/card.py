"""Serving the bundled card and sound, and registering the card.

The card ships inside the integration, so one download installs everything.
It is loaded through a single Lovelace resource – the same mechanism as adding
it by hand – which the integration creates (or updates) itself in storage
mode. `add_extra_js_url` is deliberately *not* used: those modules are loaded
fire-and-forget, without waiting for them before the dashboard renders, which
causes the recurring "Custom element doesn't exist" errors.

The resource URL carries `?v=<integration version>`, so the browser cache
refreshes with every release. A resource the user added by hand earlier
(`/local/slider-timer-card/slider-timer-card.js?v=…`) is switched over to the
bundled copy, so the card is never loaded twice in two different versions.

In YAML resource mode Home Assistant does not let integrations change the
resources; the log then says which line to add.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_TYPE, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import CARD_FILENAME, CARD_URL, DOMAIN, URL_BASE

_LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).parent
CARD_PATH = ROOT / "frontend" / CARD_FILENAME
SOUNDS_PATH = ROOT / "sounds"

RESOURCE_TYPE = "module"
# A resource whose URL contains this belongs to us (bundled or hand-added).
RESOURCE_MATCH = CARD_FILENAME

_DATA_REGISTERED = f"{DOMAIN}_frontend_registered"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Serve the files and make sure the card's resource is in place."""
    if hass.data.get(_DATA_REGISTERED):
        return
    hass.data[_DATA_REGISTERED] = True

    version = (await async_get_integration(hass, DOMAIN)).version or "0"

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(CARD_URL, str(CARD_PATH), True),
            StaticPathConfig(f"{URL_BASE}/sounds", str(SOUNDS_PATH), True),
        ]
    )

    await _async_register_resource(hass, f"{CARD_URL}?v={version}")


async def _async_register_resource(hass: HomeAssistant, url: str) -> None:
    """Create or update the Lovelace resource of the card."""
    # Imported here: Lovelace is an after-dependency, it may be missing.
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
    except ImportError:  # pragma: no cover - very old or stripped-down core
        LOVELACE_DATA = "lovelace"  # type: ignore[assignment]

    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None:
        _LOGGER.warning(
            "Lovelace is not loaded; add the card as a resource by hand: %s", url
        )
        return

    if getattr(lovelace, "resource_mode", "storage") != "storage":
        _LOGGER.info(
            "Lovelace resources are in YAML mode; add this to `lovelace: "
            "resources:` (type: module) to load the card: %s",
            url,
        )
        return

    resources = lovelace.resources
    # The storage collection loads lazily; this makes sure the items are there.
    await resources.async_get_info()

    ours = [
        item
        for item in resources.async_items()
        if RESOURCE_MATCH in str(item.get(CONF_URL, ""))
    ]

    if not ours:
        await resources.async_create_item({"res_type": RESOURCE_TYPE, CONF_URL: url})
        _LOGGER.info("Card registered as a Lovelace resource: %s", url)
        return

    first, *duplicates = ours
    if first.get(CONF_URL) != url or first.get(CONF_TYPE) != RESOURCE_TYPE:
        await resources.async_update_item(
            first["id"], {"res_type": RESOURCE_TYPE, CONF_URL: url}
        )
        _LOGGER.info(
            "Card resource updated: %s -> %s", first.get(CONF_URL), url
        )
    # Two resources for the same card would load two versions of it.
    for item in duplicates:
        await resources.async_delete_item(item["id"])
        _LOGGER.info("Duplicate card resource removed: %s", item.get(CONF_URL))
