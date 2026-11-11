"""Constants of the Timer integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "slider_timer"

# The integration serves its card and sound under this path.
URL_BASE: Final = f"/{DOMAIN}"

# --- configuration ---
CONF_NAME: Final = "name"

# Default name for a new timer. The visible name is translated: the `title`
# key of translations/en.json and translations/hu.json.
DEFAULT_NAME: Final = "Timer"

# Initial value of the number entities (the default duration).
DEFAULT_HOURS: Final = 0
DEFAULT_MINUTES: Final = 10
DEFAULT_SECONDS: Final = 0

# Upper limit of the hour field: 24 (same as the old input_number.orak max: 24).
MAX_HOURS: Final = 24
# Minutes and seconds go up to 60: when the slider of the bigger unit is hidden
# on the card, this field can carry the whole unit (60 minutes = 1 hour). The
# value is normalised the same way as before.
MAX_MINUTES: Final = 60
MAX_SECONDS: Final = 60

# Services
SERVICE_START: Final = "start"
SERVICE_PAUSE: Final = "pause"
SERVICE_RESUME: Final = "resume"
SERVICE_CANCEL: Final = "cancel"
SERVICE_SET: Final = "set"

ATTR_HOURS: Final = "hours"
ATTR_MINUTES: Final = "minutes"
ATTR_SECONDS: Final = "seconds"

# Events (following the built-in timer.finished)
EVENT_STARTED: Final = f"{DOMAIN}_started"
EVENT_PAUSED: Final = f"{DOMAIN}_paused"
EVENT_RESUMED: Final = f"{DOMAIN}_resumed"
EVENT_CANCELLED: Final = f"{DOMAIN}_cancelled"
EVENT_FINISHED: Final = f"{DOMAIN}_finished"

# States
STATE_IDLE: Final = "idle"
STATE_ACTIVE: Final = "active"
STATE_PAUSED: Final = "paused"

# --- entity keys (translation_key and the end of the unique_id) ---
KEY_REMAINING: Final = "remaining"
KEY_ACTIVE: Final = "active"
KEY_HOURS: Final = "hours"
KEY_MINUTES: Final = "minutes"
KEY_SECONDS: Final = "seconds"

# Up to config entry minor version 1 the keys were Hungarian. The migration in
# __init__.py renames the unique_ids; the entity IDs stay as they are.
LEGACY_KEYS: Final = {
    "hatralevo": KEY_REMAINING,
    "aktiv": KEY_ACTIVE,
    "ora": KEY_HOURS,
    "perc": KEY_MINUTES,
    "masodperc": KEY_SECONDS,
}

# --- the bundled Lovelace card ---
CARD_FILENAME: Final = "slider-timer-card.js"
CARD_URL: Final = f"{URL_BASE}/{CARD_FILENAME}"

# Storage (to restore state after a restart)
STORAGE_VERSION: Final = 1

# --- Assist: custom intents ---
# The sentences live in `sentences/<language>/*.yaml`; the integration copies
# them into `custom_sentences/<language>/` under the configuration directory.
INTENT_START: Final = "SliderTimerStart"
INTENT_RESUME: Final = "SliderTimerResume"
INTENT_PAUSE: Final = "SliderTimerPause"
INTENT_CANCEL: Final = "SliderTimerCancel"
INTENT_STATUS: Final = "SliderTimerStatus"

# The placeholder names are the same in every language (these are the slots).
SLOT_NAME: Final = "name"
SLOT_HOURS: Final = "hours"
SLOT_MINUTES: Final = "minutes"
SLOT_SECONDS: Final = "seconds"

# The shipped sentence files
SENTENCE_LANGUAGES: Final = ("hu", "en")
SENTENCE_FILE: Final = "slider_timer.yaml"
CUSTOM_SENTENCES_DIR: Final = "custom_sentences"

# --- expiry sound and actions ---
CONF_MEDIA_PLAYER: Final = "media_player"
CONF_SOUND_FILE: Final = "sound_file"
CONF_SOUND_AFTER: Final = "sound_after"
CONF_SOUND_BEFORE: Final = "sound_before"
# Actions on expiry: the usual Home Assistant action list (script syntax:
# `action`, `target`, `data`, conditions).
CONF_ACTIONS: Final = "actions"

# The bundled expiry sound, served by the integration itself (see card.py).
SOUND_URL: Final = f"{URL_BASE}/sounds/slider_timer_finish.flac"
DEFAULT_SOUND_FILE: Final = SOUND_URL
# The default of the betas (a file the user had to copy into www/).
LEGACY_SOUND_FILE: Final = "/local/Chat_Sounds/slider_timer_finish.flac"
# Time window: by default there is no limit – the expiry sound and the actions run
# at any time of day. In sound.py a start equal to the end means "no limit".
DEFAULT_SOUND_AFTER: Final = "00:00:00"
DEFAULT_SOUND_BEFORE: Final = "00:00:00"

MEDIA_PLAYER_DOMAIN: Final = "media_player"
SERVICE_PLAY_MEDIA: Final = "play_media"
SOUND_CONTENT_TYPE: Final = "music"

# The default duration (the initial value of the number entities)
CONF_DEFAULT_HOURS: Final = "default_hours"
CONF_DEFAULT_MINUTES: Final = "default_minutes"
CONF_DEFAULT_SECONDS: Final = "default_seconds"
