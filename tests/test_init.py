"""Setup, migration, services, card resource and static files."""

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
import homeassistant.util.dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.slider_timer.const import (
    CARD_URL,
    DEFAULT_SOUND_FILE,
    DOMAIN,
    EVENT_FINISHED,
    LEGACY_SOUND_FILE,
    SOUND_URL,
)

DATA = {
    "name": "Konyha",
    "default_hours": 0,
    "default_minutes": 0,
    "default_seconds": 5,
    "media_player": None,
    "sound_file": DEFAULT_SOUND_FILE,
    "sound_after": None,
    "sound_before": None,
    "actions": [],
}


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await async_setup_component(hass, "http", {})
    assert await async_setup_component(hass, "lovelace", {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _resources(hass: HomeAssistant) -> list[dict]:
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    return hass.data[LOVELACE_DATA].resources.async_items()


async def test_setup_entities_services_resource(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, title="Konyha", data=DATA, version=1, minor_version=2
    )
    await _setup(hass, entry)

    registry = er.async_get(hass)
    keys = {
        e.unique_id.removeprefix(f"{entry.entry_id}_")
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    assert keys == {"remaining", "active", "hours", "minutes", "seconds"}

    for service in ("start", "set", "pause", "resume", "cancel"):
        assert hass.services.has_service(DOMAIN, service)

    urls = [r["url"] for r in _resources(hass)]
    assert urls == [f"{CARD_URL}?v=1.0.1"]
    assert _resources(hass)[0]["type"] == "module"


async def test_start_and_finish(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, title="Konyha", data=DATA, version=1, minor_version=2
    )
    await _setup(hass, entry)
    sensor = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_remaining"
    )
    finished = async_capture_events(hass, EVENT_FINISHED)

    await hass.services.async_call(
        DOMAIN, "start", {"entity_id": sensor}, blocking=True
    )
    assert hass.states.get(sensor).attributes["status"] == "active"

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()
    assert hass.states.get(sensor).attributes["status"] == "idle"
    assert len(finished) == 1


async def test_migration_keeps_entity_ids(hass: HomeAssistant) -> None:
    data = {**DATA, "sound_file": LEGACY_SOUND_FILE}
    entry = MockConfigEntry(
        domain=DOMAIN, title="Konyha", data=data, version=1, minor_version=1
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = {
        "sensor": ("hatralevo", "sensor.konyha_hatralevo"),
        "binary_sensor": ("aktiv", "binary_sensor.konyha_aktiv"),
        "number": ("perc", "number.konyha_perc"),
    }
    for domain, (key, entity_id) in old.items():
        registry.async_get_or_create(
            domain,
            DOMAIN,
            f"{entry.entry_id}_{key}",
            config_entry=entry,
            suggested_object_id=entity_id.split(".")[1],
        )

    assert await async_setup_component(hass, "http", {})
    assert await async_setup_component(hass, "lovelace", {})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.minor_version == 2
    assert entry.data["sound_file"] == DEFAULT_SOUND_FILE
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_remaining")
        == "sensor.konyha_hatralevo"
    )
    assert (
        registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_active"
        )
        == "binary_sensor.konyha_aktiv"
    )
    assert (
        registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_minutes")
        == "number.konyha_perc"
    )
    assert hass.states.get("sensor.konyha_hatralevo") is not None


async def test_hand_added_resource_is_switched(hass: HomeAssistant) -> None:
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    assert await async_setup_component(hass, "http", {})
    assert await async_setup_component(hass, "lovelace", {})
    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_get_info()
    await resources.async_create_item(
        {"res_type": "module", "url": "/local/slider-timer-card/slider-timer-card.js?v=3.0.3"}
    )
    await resources.async_create_item(
        {"res_type": "module", "url": "/hacsfiles/slider-timer-card/slider-timer-card.js"}
    )
    await resources.async_create_item({"res_type": "module", "url": "/local/other.js"})

    entry = MockConfigEntry(
        domain=DOMAIN, title="Konyha", data=DATA, version=1, minor_version=2
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    urls = sorted(r["url"] for r in resources.async_items())
    assert urls == sorted([f"{CARD_URL}?v=1.0.1", "/local/other.js"])


async def test_static_files(hass: HomeAssistant, hass_client) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, title="Konyha", data=DATA, version=1, minor_version=2
    )
    await _setup(hass, entry)
    client = await hass_client()
    card = await client.get(CARD_URL)
    assert card.status == 200
    assert "slider-timer-card" in await card.text()
    sound = await client.get(SOUND_URL)
    assert sound.status == 200
    assert len(await sound.read()) > 10000


async def test_config_flow(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "http", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Nappali", "default_minutes": 3}
    )
    assert result["type"] == "create_entry"
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.minor_version == 2
    assert entry.data["sound_file"] == DEFAULT_SOUND_FILE
