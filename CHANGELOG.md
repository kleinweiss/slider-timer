# Changelog

## 1.0.0 – 2026-11-11

**First public release – one repository, ready for the Home Assistant
Marketplace (HACS).** The integration and the card share one version from now
on, starting at 1.0.0 (it follows the `v1.0.0-beta.2` integration tag; the card
was 3.0.3). The entries below are the pre-release history.

* **The card ships inside the integration** – it is served at
  `/slider_timer/slider-timer-card.js`, and the integration adds it as a single
  dashboard resource by itself (`?v=<version>`). A hand-added
  `/local/…/slider-timer-card.js` or `/hacsfiles/…` resource is switched over,
  duplicates are removed. `add_extra_js_url` is still not used (it races with the
  dashboard rendering). YAML-mode resources: the log and the README give the line
  to add.
* **The expiry sound ships inside the integration** – served at
  `/slider_timer/sounds/slider_timer_finish.flac`, the new default. Entries that
  used the old `/local/Chat_Sounds/…` default are switched to it.
* **English entity keys** – `remaining`, `active`, `hours`, `minutes`,
  `seconds` (were `hatralevo`, `aktiv`, `ora`, `perc`, `masodperc`). Config entry
  1.1 → 1.2 migration: only the unique_ids change, entity IDs and history stay.
  The card recognises both the new and the old keys.
* **The services are registered once, in `async_setup`**
  (`async_register_platform_entity_service`), instead of per timer.
* **Manifest** – `dependencies: [http]`, `after_dependencies: [conversation,
  lovelace, media_player]`, version 1.0.0.
* **Repository** – `hacs.json`, the Validate workflow (Marketplace/HACS check,
  hassfest, tests) and a pytest suite (setup, services, expiry, migration,
  resource registration, static files, config flow).

## 3.0.3-beta.1 – 2026-10-19

**Beta release – the second review round** (integration 1.0.0, card 3.0.3).
Bundle: `slider-timer-3.0.3-beta.1.zip`. Tags: `v1.0.0-beta.2` (integration) and
`v3.0.3-beta.1` (card). It supersedes `3.0.2-beta.1`; the note below about the default
duration replaces that release's entry.

* **The default duration overrides the sliders only when the setting changes** – the
  setting is applied when it differs from the value applied the last time (kept in the
  timer's store), so a value set on the card's sliders or with the `set` service
  survives a restart while the setting stays the same. The settings page and the
  READMEs say so. A store written by an older version has no such record yet, so the
  setting applies to it once.
* **Voice control: the sentences are complete** – starting without a duration
  ("indítsd el az időzítőt", "indítsd el a nappali időzítőt") and reading the
  remaining time ("mennyi van még hátra", "mennyi idő van hátra") are both covered in
  Hungarian and English. A spoken name may carry an article ("a nappali időzítő") and
  is matched against the timer name in both directions; with several timers the answer
  asks which one is meant. "Állítsd le az időzítőt" still cancels.
* **The expiry actions are validated in every path** – the settings forms check the
  action list the same way the `start` service does (`async_validate_actions_config`),
  so an invalid action list is refused with a readable message instead of failing
  silently at expiry.
* **`iot_class: calculated`** in the manifest (the timer polls nothing), the keys in
  hassfest order; `hacs.json` declares the real minimum, **Home Assistant 2026.5.0**
  (the `Script.unload` API the expiry actions use).
* **A CI workflow** (`hassfest` + HACS validation) runs on push, on a schedule and on
  demand.
* **The expiry sound is our own recording now** – the bundled file is
  `www/Chat_Sounds/slider_timer_finish.flac` (1.85 s, 48 kHz stereo), replacing the
  previous `sounds_timer_finished.flac`. `DEFAULT_SOUND_FILE` follows the new name;
  an entry that still stores the old path keeps it, so point the timer's *sound file*
  setting to the new file on the settings page after installing.
* **The minutes / seconds descriptions say 0–60** in both languages (they used to say
  0–59, while the limit has been 60).
* **Card 3.0.3** – when the card's `name:` names a timer but no timer matches, the card
  shows no timer instead of falling back to the alphabetically first one; an ambiguous
  partial match (two timers tied) is no longer resolved arbitrarily. Bump the Lovelace
  resource `?v=` to `3.0.3` together with the card file.
* **The card is no longer inside the integration** – `custom_components/slider_timer/
  frontend/` is gone; the card reaches the installation through `www/` (or HACS) and a
  single Lovelace resource, as before.
* **The READMEs** carry the minimum HA version, the bundle layout (including
  `www/Chat_Sounds/`), the right install path (`custom_components/slider_timer`) and
  the fact that entity IDs are language-dependent – picking a timer from the UI is
  recommended.

## 3.0.2-beta.1 – 2026-10-19

**Beta release – the review fixes** (integration 1.0.0, card 3.0.2). This is the first
published release; the `slider-timer-3.0.0.zip` and `slider-timer-3.0.1.zip` beside it
were never published.

* **The expiry actions are validated** – the `start` service, the expiry run and both
  settings forms check the action list (`async_validate_actions_config`) and refuse an
  invalid one with a readable message (`invalid_actions`) instead of failing silently.
* **Voice control: the timer name is optional** – every sentence has a nameless variant
  too ("mennyi van hátra az időzítőből", "állítsd le az időzítőt"), and a leading
  article in a spoken name ("a nappali időzítő") is ignored. With several timers the
  answer asks which one is meant.
* **The expiry sound window has no default limit any more** – a fresh setup starts
  empty (`00:00:00` – `00:00:00` = always); an entry that already stores a window keeps
  it.
* **The default duration is applied on every load** – the hour / minute / second
  entities take the entry's default when the timer loads; the settings page says so.
  A running or paused countdown is untouched.
* **A removed timer leaves nothing behind** – the restore data is keyed by the config
  entry id and is dropped when the entry is removed.
* **`zero_duration`** – starting a timer whose hour / minute / second entities are all
  zero now reports the same readable error as the services.
* **The minute and second maximum is 60** (services and sliders) – 59 made a full
  minute unreachable.
* **Card 3.0.2** – `name:` matches in both directions: an exact device name, a title
  that contains it ("Nappali időzítő" → Nappali) or the beginning of it ("Nap"); the
  entity ID fallback also accepts the English suffixes (`remaining`, `hours`,
  `minutes`, `seconds`). Bump the Lovelace resource `?v=` to `3.0.2` together with the
  card file.
* **Config flow** – the name must be unique in both flows, with an inline `name_exists`
  error instead of a silent duplicate; the name-derived `unique_id` is gone, so a
  rename no longer blocks the freed name, and names that differ only in an accent
  ("Hálószoba" / "Haloszoba") are refused.
* **Distribution** – `dist/slider-timer-3.0.2-beta.1.zip`: integration + card + sound
  in one file, now including `hacs.json`. Tags: `v1.0.0-beta.1` (integration) and
  `v3.0.2-beta.1` (card, with the ZIP as the release asset).

## 3.0.1 – 2026-10-18

**Internationalisation pass – no user-visible behaviour change.**

* **Assist slots are English now** – `name`, `hours`, `minutes`, `seconds` (were
  `nev`, `ora`, `perc`, `masodperc`): `const.py`, both sentence files and the installed
  `custom_sentences/<language>/slider_timer.yaml` copies. The spoken Hungarian and
  English sentences themselves are unchanged.
* **Entity translation keys stay Hungarian on purpose** (`hatralevo`, `aktiv`, `ora`,
  `perc`, `masodperc`): they are part of the entity `unique_id`, so renaming them
  would recreate every entity. The visible names come from `translations/en.json`.
* **Manifest** – `documentation`, `issue_tracker` and `codeowners` now point to
  `github.com/kleinweiss/slider-timer`.
* **Card 3.0.1** – the entity picker's fallback also accepts English entity IDs
  (`*_remaining`) next to `*_hatralevo`; the primary match (the entity
  `translation_key`) is unchanged. Bump the Lovelace resource `?v=` to `3.0.1`.
* **Distribution** – `dist/slider-timer-3.0.1.zip`; the `slider-timer-3.0.0.zip` next
  to it was never published.

## 3.0.0 – 2026-10-18

**Rebrand: the project is now called *Slider Timer* – and it is integration-based.**

Every identifier and user-facing name was renamed consistently across the integration,
the card and the documentation, and the hand-written YAML package / blueprint layer was
retired: the integration now creates everything those files did by hand.

* **Integration** – HA domain `slider_timer` (was `idozito`), manifest name **Slider Timer**,
  version **1.0.0**. Services `slider_timer.start` / `.pause` / `.resume` / `.cancel` / `.set`,
  events `slider_timer_started` … `slider_timer_finished`, `integration_type: service`.
  Class names `SliderTimer*`; Assist intents `SliderTimerStart` … ; sentences file
  `custom_sentences/<language>/slider_timer.yaml`.
* **Card** – `www/slider-timer-card/slider-timer-card.js`, element type
  `custom:slider-timer-card`, version **3.0.0** (`SLIDER_TIMER_CARD_VERSION`). Added as a
  **Lovelace resource** (the integration does not serve it), and it works only with the
  integration's entities – the old `timer.*` mode was removed in card 2.4.0.
* **Repositories** – `slider-timer` (integration) and `slider-timer-card` (card).
* **Removed** – `package/slider_timer.yaml` and the four `blueprints/` (voice start, voice
  control, expiry sound, start script): the integration covers all of them (entities,
  services, Assist intents, built-in expiry sound). The earlier 2.0.0 (package-based) was
  never released.
* **Distribution** – `dist/slider-timer-3.0.0.zip`: `custom_components/slider_timer/`,
  `www/slider-timer-card/`, `www/Chat_Sounds/`, README/LICENSE/CHANGELOG.
* The earlier releases below keep their original `idozito` names – they are historical
  and the `dist/` ZIPs are unchanged.

## 1.0.2 – 2026-10-16

* `www/idozito-card/idozito-card.js`: card version **1.4.4** – the header status label's
  icons are correctly named `mdi:timer-play-outline` when running and
  `mdi:timer-pause-outline` when paused (1.0.1 incorrectly used `mdi:timer-play` / `mdi:timer-pause`
  instead). The idle icon is unchanged: `mdi:timer-outline`.
* In the documentation, the `?v=` value and the HACS card-repo release tag moved to **1.4.4**.
* `dist/idozito-timer-package-1.0.2.zip`: the complete package.

## 1.0.1 – 2026-10-16

* `www/idozito-card/idozito-card.js`: card version **1.4.3** – the header status label
  got a state-dependent icon (running = `mdi:timer-play`, paused = `mdi:timer-pause`,
  idle = `mdi:timer-outline`).
* In the documentation, the `?v=` value and the HACS card-repo release tag moved to **1.4.3**.
* `dist/idozito-timer-package-1.0.1.zip`: the complete package.

## Package 1.0.0 – 2026-10-16 (YAML package, before the integration)

First shareable release.

* `package/idozito.yaml`: the whole timer chain in a single Home Assistant package file
  (timer, 3 input_number, script, 3 automations, remaining-time sensor).
* `www/idozito-card/idozito-card.js`: card version 1.4.2 (without external dependencies).
* `www/Chat_Sounds/sounds_timer_finished.flac`: the sound played when the timer finishes.
* `blueprints/`: 3 automations + 1 script as blueprints (`!input` fields).
* `hacs-repo-card/`: HACS Dashboard repo skeleton (`hacs.json`, README, MIT license).
* Parameterisation for shareability: in the expiry automation the media player and the sound file
  were moved into a `variables:` block; the automation's identifier is `idozito_lejart_hang`
  (without the "nappali" reference).
* `dist/idozito-timer-package-1.0.0.zip`: the complete package.
