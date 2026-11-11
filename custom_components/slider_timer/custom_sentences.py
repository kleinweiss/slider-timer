"""Installing the sentence files (custom_sentences).

Assist reads its own sentences from the
`custom_sentences/<language>/<file>.yaml` files under the configuration
directory – not from an integration (bundled). That is why ours are copied
there, but only when no such file exists yet: an existing one is never
overwritten.

The copy happens while the integration is set up (`async_setup`), that is
before Home Assistant finishes starting; the sentence files are loaded at the
first conversation anyway.
"""

from __future__ import annotations

import logging
from pathlib import Path
import shutil

from homeassistant.core import HomeAssistant

from .const import CUSTOM_SENTENCES_DIR, SENTENCE_FILE, SENTENCE_LANGUAGES

_LOGGER = logging.getLogger(__name__)

SOURCE_DIR = Path(__file__).parent / "sentences"


def _target(hass: HomeAssistant, language: str) -> Path:
    return Path(hass.config.path(CUSTOM_SENTENCES_DIR, language, SENTENCE_FILE))


def _copy_missing(hass: HomeAssistant) -> list[Path]:
    """Copy the sentence files that are still missing (into the config dir)."""
    copied: list[Path] = []
    for language in SENTENCE_LANGUAGES:
        source = SOURCE_DIR / language / SENTENCE_FILE
        if not source.is_file():
            _LOGGER.warning("Sentence file missing from the package: %s", source)
            continue
        target = _target(hass, language)
        if target.exists():
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        except OSError as err:
            _LOGGER.warning(
                "The sentence file cannot be copied (%s): %s. For voice "
                "control it has to be put in place by hand.",
                target,
                err,
            )
            continue
        copied.append(target)
    return copied


async def async_install_sentences(hass: HomeAssistant) -> list[Path]:
    """Install the sentence files, if they are not there yet."""
    copied = await hass.async_add_executor_job(_copy_missing, hass)
    for path in copied:
        _LOGGER.info("Timer: sentence file copied – %s", path)
    return copied
