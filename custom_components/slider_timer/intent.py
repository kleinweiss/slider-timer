"""Voice control: custom Assist intents.

The spoken sentences live in `sentences/<language>/slider_timer.yaml` (the
integration copies them under `custom_sentences/` in the configuration
directory). The replies are built here, in the handlers, and they always answer
in the language of the request; anything that is not Hungarian is answered in
English.

A timer is addressed by its name: the value of the `name` slot is compared with
the configured names without accents, case-insensitively and partially. When a
name is given, it has to match: an unmatched name is an error, and an ambiguous
(partially matching) one asks which timer is meant. Without a name the single
timer is used, and with several timers the code asks.
"""

from __future__ import annotations

from datetime import timedelta
import unicodedata

from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent

from .const import (
    DOMAIN,
    INTENT_CANCEL,
    INTENT_PAUSE,
    INTENT_RESUME,
    INTENT_START,
    INTENT_STATUS,
    SLOT_HOURS,
    SLOT_MINUTES,
    SLOT_NAME,
    SLOT_SECONDS,
    STATE_ACTIVE,
    STATE_IDLE,
    STATE_PAUSED,
)
from .timer import SliderTimer, format_duration

# The replies: an intent always answers in the language of the request.
MESSAGES: dict[str, dict[str, str]] = {
    "hu": {
        "started": "Időzítő elindítva: {name}, {remaining}.",
        "no_duration": "Nem adtad meg, mennyi ideig szóljon az időzítő.",
        "no_timer": "Nincs ilyen nevű időzítő: {name}.",
        "ask_name": "Több időzítő van beállítva; mondd meg, melyikre gondolsz.",
        "no_timer_at_all": "Nincs beállítva időzítő.",
        "resumed": "Időzítő folytatva, {remaining} van hátra.",
        "already_running": "Az időzítő már fut.",
        "nothing_paused": "Nincs szüneteltetett időzítő.",
        "paused": "Időzítő szüneteltetve, {remaining} van hátra.",
        "already_paused": "Az időzítő már szüneteltetve van.",
        "nothing_running": "Nincs futó időzítő.",
        "cancelled": "Időzítő törölve.",
        "status_active": "{remaining} van hátra.",
        "status_paused": "Az időzítő szüneteltetve van, {remaining} van hátra.",
        "status_idle": "Nincs futó időzítő.",
    },
    "en": {
        "started": "Timer started: {name}, {remaining}.",
        "no_duration": "I don't know how long the timer should run.",
        "no_timer": "There is no timer named {name}.",
        "ask_name": "There are several timers; please say which one you mean.",
        "no_timer_at_all": "There are no timers configured.",
        "resumed": "Timer resumed, {remaining} left.",
        "already_running": "The timer is already running.",
        "nothing_paused": "There is no paused timer.",
        "paused": "Timer paused, {remaining} left.",
        "already_paused": "The timer is already paused.",
        "nothing_running": "There is no running timer.",
        "cancelled": "Timer cancelled.",
        "status_active": "{remaining} left.",
        "status_paused": "The timer is paused, {remaining} left.",
        "status_idle": "There is no running timer.",
    },
}


def _fold(text: str) -> str:
    """Lowercase, accent-free form for the comparison."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        char for char in decomposed if not unicodedata.combining(char)
    ).casefold().strip()


# The articles that may end up in the spoken `name` slot: the sentence templates
# make them optional, so the wildcard can swallow them ("a nappali", "the
# kitchen", "egy nappali"). Hungarian and English both occur (the sentence file's
# language decides), so both are stripped.
ARTICLES: tuple[str, ...] = ("a", "an", "the", "az", "egy")


def _strip_article(text: str) -> str:
    """Drop a leading (or standalone) article from the spoken name.

    Without this the reply would echo the article ("Nincs ilyen nevű időzítő:
    a nappali.") and the match would rely on the partial comparison only.
    """
    words = text.split()
    if words and words[0].casefold() in ARTICLES:
        words = words[1:]
    return " ".join(words)


def _timers(hass: HomeAssistant) -> list[SliderTimer]:
    """The loaded timers."""
    timers: list[SliderTimer] = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        timer = getattr(entry, "runtime_data", None)
        if isinstance(timer, SliderTimer):
            timers.append(timer)
    return timers


def _resolve_timer(hass: HomeAssistant, spoken: str) -> tuple[SliderTimer | None, str]:
    """The timer belonging to the spoken name (or the key of the error)."""
    timers = _timers(hass)
    if not timers:
        return None, "no_timer_at_all"

    folded = _fold(_strip_article(spoken))
    if not folded:
        # No name was spoken: a single timer is meant; with several we ask.
        if len(timers) == 1:
            return timers[0], ""
        return None, "ask_name"

    # A name was spoken: only an unambiguous match may be used. An exact match
    # wins; a name that matches nothing (or several timers) is never quietly
    # replaced by another timer.
    if exact := [timer for timer in timers if _fold(timer.name) == folded]:
        if len(exact) == 1:
            return exact[0], ""
        return None, "ask_name"

    if partial := [
        timer
        for timer in timers
        if folded in _fold(timer.name) or _fold(timer.name) in folded
    ]:
        if len(partial) == 1:
            return partial[0], ""
        return None, "ask_name"

    return None, "no_timer"


class _SliderTimerIntent(intent.IntentHandler):
    """Shared helpers for the timer intents."""

    def _slots(self, intent_obj: intent.Intent) -> dict[str, str]:
        slots: dict[str, str] = {}
        for key, slot in (intent_obj.slots or {}).items():
            value = slot.get("value") if isinstance(slot, dict) else slot
            if value is not None:
                slots[key] = str(value)
        return slots

    def _number(self, slots: dict[str, str], key: str) -> int:
        """The number of the slot (the first run of digits in the spoken text)."""
        digits = ""
        for char in slots.get(key, ""):
            if char.isdigit():
                digits += char
            elif digits:
                break
        return int(digits) if digits else 0

    def _language(self, intent_obj: intent.Intent) -> str:
        language = str(intent_obj.language or "").casefold()
        return "hu" if language.startswith("hu") else "en"

    def _respond(
        self, intent_obj: intent.Intent, key: str, **values: str
    ) -> intent.IntentResponse:
        message = MESSAGES[self._language(intent_obj)][key]
        response = intent_obj.create_response()
        response.async_set_speech(message.format(**values))
        return response

    def _timer(
        self, intent_obj: intent.Intent
    ) -> tuple[SliderTimer | None, intent.IntentResponse | None]:
        spoken = _strip_article(self._slots(intent_obj).get(SLOT_NAME, ""))
        timer, failure = _resolve_timer(intent_obj.hass, spoken)
        if timer is None:
            return None, self._respond(intent_obj, failure, name=spoken)
        return timer, None


class SliderTimerStartIntent(_SliderTimerIntent):
    """Start a timer with a given duration."""

    intent_type = INTENT_START

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        timer, failure = self._timer(intent_obj)
        if timer is None:
            assert failure is not None
            return failure

        slots = self._slots(intent_obj)
        seconds = 0
        for key, factor in (
            (SLOT_HOURS, 3600),
            (SLOT_MINUTES, 60),
            (SLOT_SECONDS, 1),
        ):
            value = self._number(slots, key)
            if value > 0:
                seconds += value * factor

        if seconds <= 0:
            # Without a duration the number entities apply.
            seconds = int(timer.default_duration.total_seconds())
        if seconds <= 0:
            return self._respond(intent_obj, "no_duration")

        await timer.async_start(timedelta(seconds=seconds))
        return self._respond(
            intent_obj,
            "started",
            name=timer.name,
            remaining=format_duration(timedelta(seconds=seconds)),
        )


class SliderTimerResumeIntent(_SliderTimerIntent):
    """Resume a paused timer."""

    intent_type = INTENT_RESUME

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        timer, failure = self._timer(intent_obj)
        if timer is None:
            assert failure is not None
            return failure

        if timer.state == STATE_PAUSED:
            remaining = format_duration(timer.remaining)
            await timer.async_resume()
            return self._respond(intent_obj, "resumed", remaining=remaining)
        if timer.state == STATE_ACTIVE:
            return self._respond(intent_obj, "already_running")
        return self._respond(intent_obj, "nothing_paused")


class SliderTimerPauseIntent(_SliderTimerIntent):
    """Pause a running timer."""

    intent_type = INTENT_PAUSE

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        timer, failure = self._timer(intent_obj)
        if timer is None:
            assert failure is not None
            return failure

        if timer.state == STATE_ACTIVE:
            remaining = format_duration(timer.remaining)
            await timer.async_pause()
            return self._respond(intent_obj, "paused", remaining=remaining)
        if timer.state == STATE_PAUSED:
            return self._respond(intent_obj, "already_paused")
        return self._respond(intent_obj, "nothing_running")


class SliderTimerCancelIntent(_SliderTimerIntent):
    """Cancel a timer."""

    intent_type = INTENT_CANCEL

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        timer, failure = self._timer(intent_obj)
        if timer is None:
            assert failure is not None
            return failure

        if timer.state == STATE_IDLE:
            return self._respond(intent_obj, "nothing_running")
        await timer.async_cancel()
        return self._respond(intent_obj, "cancelled")


class SliderTimerStatusIntent(_SliderTimerIntent):
    """Ask for the remaining time."""

    intent_type = INTENT_STATUS

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        timer, failure = self._timer(intent_obj)
        if timer is None:
            assert failure is not None
            return failure

        if timer.state == STATE_ACTIVE:
            return self._respond(
                intent_obj,
                "status_active",
                remaining=format_duration(timer.remaining),
            )
        if timer.state == STATE_PAUSED:
            return self._respond(
                intent_obj,
                "status_paused",
                remaining=format_duration(timer.remaining),
            )
        return self._respond(intent_obj, "status_idle")


async def async_setup_intents(hass: HomeAssistant) -> None:
    """Register the intents (called by the `intent` platform)."""
    for handler in (
        SliderTimerStartIntent(),
        SliderTimerResumeIntent(),
        SliderTimerPauseIntent(),
        SliderTimerCancelIntent(),
        SliderTimerStatusIntent(),
    ):
        intent.async_register(hass, handler)
