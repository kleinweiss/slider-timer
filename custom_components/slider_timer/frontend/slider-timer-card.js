/*
 * slider-timer-card - a custom, compact Lovelace card for a countdown timer.
 *
 * The card of the slider_timer integration. It ships inside the integration,
 * which serves it at `/slider_timer/slider-timer-card.js` and registers it as a
 * Lovelace resource (`?v=<integration version>`) by itself.
 *
 * The card drives the timer from the entities of the slider_timer integration: the
 * `*_remaining` (Hungarian installs: `*_hatralevo`) sensor provides the state and the remaining time, the matching
 * Hours / Minutes / Seconds number entities provide the duration, while the
 * expiry actions are passed on start by the card's `expiry:` block to the
 * `slider_timer.start` service - so the server runs them even when the dashboard
 * is closed at expiry.
 *
 *  1) Selecting the timer
 *     When the config is empty, the card discovers the integration's timers by
 *     their entities; `name` narrows down the discovered timers (the device
 *     name may be a part of it - "Nappali időzítő" - or contain it - "Nap").
 *  2) The editor (2.1.0) uses the HA `ha-form` element:
 *       - entity:   the sensor of the controlled timer
 *       - name:     the header text
 *       - icon:     the header icon
 *       - fields:   which sliders are shown (hours / minutes / seconds).
 *                   A hidden field counts as 0: it plays no part in the shown
 *                   duration or on start. (Older configs may also use
 *                   show_hours / show_minutes / show_seconds.)
 *       - buttons:  which buttons are shown (start/pause/resume/cancel)
 *       - settings_button: a small gear for the timer's settings
 *     The editor only writes the keys above; every other (hand-written) key
 *     is left untouched.
 *
 * In 2.4.0 the old `timer.*` + `start_script` + input_number based mode was
 * removed: the card works only with the slider_timer integration.
 *
 *    When an integration timer is selected, the "Expiry settings" section
 *    appears at the bottom of the editor (action + target, media player,
 *    sound file, sound from-until). These live in the card's `expiry:` block:
 *    on start the card passes them to the `slider_timer.start` service, and the
 *    server runs them at expiry - the dashboard may be closed at that time.
 *    Anything you leave empty in the editor uses the
 *    integration's setting.
 *
 * There is deliberately NO external dependency (no `lit` import), so it also
 * loads without internet. It uses HA theme variables, so it fits the theme.
 *
 * The loader URL carries a `?v=` version parameter (for the integration, the
 * manifest version), so the browser cache refreshes with every release.
 */
const SLIDER_TIMER_CARD_VERSION = "1.0.0";

/* The actual version is the ?v= parameter of the loader script URL, if any
 * (that is how it loads as a Lovelace resource); otherwise the constant above. */
const SLIDER_TIMER_CARD_RUNTIME_VERSION = (() => {
  try {
    for (const el of document.querySelectorAll('script[src*="slider-timer-card"]')) {
      const v = new URL(el.src, window.location.href).searchParams.get("v");
      if (v) return v;
    }
  } catch (_err) {
    /* the version is cosmetic data; on error the constant remains */
  }
  return SLIDER_TIMER_CARD_VERSION;
})();

/* The upper limit of the hours slider. It matches the integration's MAX_HOURS
 * value: a longer timer cannot be set. Minutes/seconds may go up to 60. */
const HOURS_MAX = 24;

/* seconds -> always "HH:MM:SS" (e.g. 00:00:10).
 * ceil: we show the upper whole second of the remaining time, so the change
 * falls exactly on the second edge (not on the half second, as with round). */
function secondsToClock(seconds) {
  const total = Math.max(0, Math.ceil(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

/* Language strings. The default is English; on a Hungarian HA UI
 * (hass.language starts with "hu") the Hungarian table is used. Any other
 * language falls back to English. */
const TEXTS = {
  en: {
    state: { idle: "Idle", active: "Running", paused: "Paused" },
    noTimer: "No timer",
    timer: "Timer",
    settings: "Timer settings",
    fields: { hours: "Hours", minutes: "Minutes", seconds: "Seconds" },
    buttons: {
      start: "Start",
      pause: "Pause",
      resume: "Resume",
      cancel: "Cancel",
    },
    editor: {
      labels: {
        entity: "Timer",
        name: "Name",
        icon: "Icon",
        fields: "Sliders",
        buttons: "Buttons",
        settings_button: "Settings button",
      },
      helpers: {
        entity: "Which timer the card controls.",
        fields:
          "A slider that is turned off counts as 0 (in the display and when starting).",
        buttons: "If you turn them all off, only the countdown is shown.",
        settings_button: "Only shown for an integration timer.",
        integration: "integration",
      },
      expiryTitle: "Expiry settings",
      expiryNote:
        "Goes into the card's <code>expiry:</code> block and is passed to the timer when starting. The sound and the actions run on the server, so the dashboard may be closed at expiry. Anything you leave empty here uses the integration's setting.",
      hintNoTimer: "Select an integration timer to set the expiry options.",
      hintText:
        "The settings above belong to the card; the expiry section goes into the card's YAML expiry: block and is passed to the timer when starting. The sound and the actions run on the server, so the dashboard may be closed at expiry. Anything you leave empty here uses the integration's setting.",
      expiryLabels: {
        actions: "Actions to run",
        media_player: "Media player",
        sound_file: "Sound file",
        sound_after: "Sound and actions from",
        sound_before: "Sound and actions until",
      },
      expiryHelpers: {
        actions:
          "Actions that run when the timer expires. Left empty, the integration's setting applies.",
        media_player:
          "Media player for the expiry sound. Left empty, the integration's setting applies.",
        sound_file: "The media ID to play (e.g. /local/…).",
        sound_after:
          "Outside the time window neither the sound nor the actions run.",
        sound_before:
          "If the start and the end are the same, it is not time-bound.",
      },
    },
    cardName: "Slider Timer Card",
    cardDescription: "Compact timer with sliders and a countdown.",
  },
  hu: {
    state: { idle: "Készenlét", active: "Fut", paused: "Szüneteltetve" },
    noTimer: "Nincs időzítő",
    timer: "Időzítő",
    settings: "Időzítő beállításai",
    fields: { hours: "Óra", minutes: "Perc", seconds: "Másodperc" },
    buttons: {
      start: "Indítás",
      pause: "Szünet",
      resume: "Folytatás",
      cancel: "Mégse",
    },
    editor: {
      labels: {
        entity: "Időzítő",
        name: "Név",
        icon: "Ikon",
        fields: "Csúszkák",
        buttons: "Gombok",
        settings_button: "Beállítások gomb",
      },
      helpers: {
        entity: "Melyik időzítőt vezérelje a kártya.",
        fields:
          "A kikapcsolt csúszka 0-nak számít (kijelzésben és indításnál is).",
        buttons: "Ha mindet kikapcsolod, csak a visszaszámláló látszik.",
        settings_button: "Csak integrációs időzítőnél jelenik meg.",
        integration: "integráció",
      },
      expiryTitle: "Lejáratkori beállítások",
      expiryNote:
        "A kártya <code>expiry:</code> blokkjába kerül, és indításkor átadódik az időzítőnek. A hang és a művelet a szerveren fut le, ezért lejáratkor a dashboard lehet zárva is. Amit üresen hagysz, arra az integráció beállítása érvényes.",
      hintNoTimer: "Válassz integrációs időzítőt a lejáratkori beállításokhoz.",
      hintText:
        "A fenti beállítások a kártyához tartoznak; a lejáratkori szakasz a kártya YAML-jának expiry: blokkjába kerül, és indításkor átadódik az időzítőnek. A hang és a művelet a szerveren fut le, ezért lejáratkor a dashboard lehet zárva is. Amit itt üresen hagysz, arra az integráció beállítása érvényes.",
      expiryLabels: {
        actions: "Művelet végrehajtása",
        media_player: "Média lejátszó",
        sound_file: "Hangfájl",
        sound_after: "Hang és művelet ettől",
        sound_before: "Hang és művelet eddig",
      },
      expiryHelpers: {
        actions:
          "Lejáratkor lefutó műveletek. Üresen az integráció beállítása érvényes.",
        media_player:
          "A lejárati hang lejátszója. Üresen az integráció beállítása érvényes.",
        sound_file: "A lejátszandó média azonosítója (pl. /local/…).",
        sound_after: "Az időablakon kívül sem hang, sem művelet nem fut.",
        sound_before: "Ha a kezdet és a vég ugyanaz, nincs időhöz kötve.",
      },
    },
    cardName: "Slider Timer kártya",
    cardDescription: "Kompakt időzítő csúszkákkal és visszaszámlálóval.",
  },
};

/* The card language from the HA `hass.language` value: hu* -> Hungarian, else English. */
function textLang(hass) {
  const lang = String((hass && hass.language) || "en").toLowerCase();
  return lang.startsWith("hu") ? "hu" : "en";
}

/* The duration fields: the key is the service field and the number entity role. */
function cardFields(t) {
  return [
    { key: "hours", label: t.fields.hours },
    { key: "minutes", label: t.fields.minutes },
    { key: "seconds", label: t.fields.seconds },
  ];
}

/* The items of the editor selectors (the order is the display order). */
function fieldOptions(t) {
  return cardFields(t).map((field) => ({ value: field.key, label: field.label }));
}

function buttonOptions(t) {
  return ALL_BUTTONS.map((key) => ({ value: key, label: t.buttons[key] }));
}

/* The entities of the slider_timer integration: the platform name and the entity
 * keys (translation_key). The latter also lets us infer the entity ID suffix
 * for older entries that have no key. */
const INTEGRATION_PLATFORM = "slider_timer";
const INTEGRATION_KEYS = ["remaining", "hours", "minutes", "seconds"];
/* The translation_keys of the pre-1.0.0 betas (Hungarian). */
const LEGACY_TRANSLATION_KEYS = {
  hatralevo: "remaining",
  ora: "hours",
  perc: "minutes",
  masodperc: "seconds",
};
/* The entity ID suffixes belonging to each key: the English and the Hungarian
 * form (the entity IDs follow the language of the installation), so an entry
 * without a translation_key is still found. */
const INTEGRATION_SUFFIXES = {
  remaining: ["remaining", "hatralevo"],
  hours: ["hours", "ora"],
  minutes: ["minutes", "perc"],
  seconds: ["seconds", "masodperc"],
};

/* The three duration fields; the labels are language-dependent (cardFields). */
const CARD_FIELDS = cardFields(TEXTS.en);

/* The card's buttons (the order is also the display order). */
const ALL_BUTTONS = ["start", "pause", "resume", "cancel"];

/* state -> header icon */
const STATE_ICON = {
  idle: "mdi:timer-outline",
  active: "mdi:timer-play-outline",
  paused: "mdi:timer-pause-outline",
};

class SliderTimerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._built = false;
    this._inputs = {};
    this._dragging = {};
    this._lockedUntil = 0;
    this._timerId = null;
    this._active = false;
    this._lang = null;
    this._fields = CARD_FIELDS;
  }

  static getStubConfig() {
    /* An empty config is enough: the card discovers the timer by itself; in the
     * visual editor any of them can be selected afterwards. */
    return {};
  }

  static getConfigElement() {
    return document.createElement("slider-timer-card-editor");
  }

  setConfig(config) {
    if (config !== undefined && (config === null || typeof config !== "object")) {
      throw new Error("slider-timer-card: the configuration must be an object.");
    }
    this._config = Object.assign(
      {
        name: null,
        icon: "mdi:timer-outline",
        entity: null,
        /* New (2.1.0) display options - by default everything behaves as before. */
        fields: null,
        show_hours: true,
        show_minutes: true,
        show_seconds: true,
        buttons: null,
        settings_button: false,
      },
      config || {}
    );
    this._fields = this._visibleFields();
    this._build();
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  _t() {
    return TEXTS[textLang(this._hass)];
  }

  /* Refresh the static labels when the language changes (or on the first hass
   * assignment). hass arrives every second, so we only work on a change. */
  _applyLanguage() {
    const lang = textLang(this._hass);
    if (lang === this._lang) return;
    this._lang = lang;
    const t = this._t();
    this._gearEl.title = t.settings;
    this._gearEl.setAttribute("aria-label", t.settings);
    for (const key of ALL_BUTTONS) {
      const span = this._buttons[key].querySelector("span");
      if (span) span.textContent = t.buttons[key];
    }
    CARD_CUSTOM_ENTRY.name = t.cardName;
    CARD_CUSTOM_ENTRY.description = t.cardDescription;
    this._fields = this._visibleFields();
    this._buildSliders();
  }

  connectedCallback() {
    this._active = true;
    this._schedule(0);
  }

  disconnectedCallback() {
    this._active = false;
    this._clearTimer();
  }

  /* ---- update scheduling ----
   * On every render we compute the remaining time from the server-side absolute
   * `finishes_at` moment, so the display cannot drift.
   * The render itself, however, is aligned to the next second edge, so the number
   * flips exactly when it should and no value is skipped. */
  _clearTimer() {
    if (this._timerId !== null) {
      window.clearTimeout(this._timerId);
      this._timerId = null;
    }
  }

  _schedule(delay) {
    this._clearTimer();
    const wait = typeof delay === "number" ? delay : this._nextDelay();
    this._timerId = window.setTimeout(() => {
      this._timerId = null;
      this._update();
    }, Math.max(0, wait));
  }

  _nextDelay() {
    const snap = this._snapshot();
    if (!snap || snap.state !== "active" || !snap.endsAt) {
      return 1000; // idle / paused: there is no per-second change
    }
    const msLeft = new Date(snap.endsAt).getTime() - Date.now();
    if (!Number.isFinite(msLeft) || msLeft <= 0) return 1000; // expired, but the state change has not arrived yet
    const rem = msLeft % 1000;
    // +25 ms of slack so we render after the change for sure
    return rem === 0 ? 1000 : rem + 25;
  }

  getCardSize() {
    return 5;
  }

  /* ---- building ---- */
  _build() {
    const c = this._config;
    const t = this._t();
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          --slider-timer-blue: #2196f3;
          --slider-timer-yellow: #f6c344;
        }
        ha-card { overflow: hidden; }
        .wrap { padding: 12px 16px 14px; }
        .head { display: flex; align-items: center; gap: 8px; }
        .head ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
        .name { flex: 1 1 auto; font-size: 16px; font-weight: 500; color: var(--primary-text-color); }
        .state { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: var(--secondary-text-color); }
        .state ha-icon { color: inherit; --mdc-icon-size: 16px; }
        .state.active { color: var(--slider-timer-yellow); }
        .state.paused { color: var(--slider-timer-blue); }
        .gear {
          flex: 0 0 auto;
          display: inline-flex; align-items: center; justify-content: center;
          width: 30px; height: 30px; margin: -4px -6px -4px 0; padding: 0;
          border: none; border-radius: 50%; cursor: pointer;
          background: transparent; color: var(--secondary-text-color);
        }
        .gear:hover { background: var(--secondary-background-color); }
        .gear ha-icon { --mdc-icon-size: 18px; }
        .countdown {
          margin-top: 9px;
          font-size: 48px;
          font-weight: 300;
          line-height: 1.1;
          letter-spacing: 1px;
          text-align: center;
          font-variant-numeric: tabular-nums;
          color: var(--primary-text-color);
        }
        .countdown.active { color: var(--slider-timer-yellow); }
        .countdown.paused { color: var(--slider-timer-blue); }
        .body { min-height: 140px; display: flex; flex-direction: column; }
        .sliders { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
        .slider-row { display: grid; grid-template-columns: 74px 1fr 36px; align-items: center; gap: 8px; }
        .slider-label { font-size: 13px; color: var(--primary-text-color); }
        .slider-value { font-size: 13px; text-align: right; font-variant-numeric: tabular-nums; color: var(--primary-text-color); }
        input[type="range"] {
          width: 100%;
          height: 24px;
          margin: 0;
          outline: none;
          border: none;
          background: transparent;
          -webkit-appearance: none;
          appearance: none;
          cursor: pointer;
          -webkit-tap-highlight-color: transparent;
        }
        input[type="range"]:focus,
        input[type="range"]:focus-visible { outline: none; box-shadow: none; }
        input[type="range"]::-webkit-slider-runnable-track {
          height: 4px;
          border: none;
          border-radius: 2px;
          background: linear-gradient(to right,
            var(--slider-timer-blue) 0%,
            var(--slider-timer-blue) var(--fill, 0%),
            var(--divider-color) var(--fill, 0%),
            var(--divider-color) 100%);
        }
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 16px;
          height: 16px;
          margin-top: -6px;
          border: none;
          border-radius: 50%;
          background: var(--slider-timer-blue);
        }
        input[type="range"]::-moz-range-track {
          height: 4px; border: none; border-radius: 2px; background: var(--divider-color);
        }
        input[type="range"]::-moz-range-progress {
          height: 4px; border: none; border-radius: 2px; background: var(--slider-timer-blue);
        }
        input[type="range"]::-moz-range-thumb {
          width: 16px; height: 16px; border: none; border-radius: 50%; background: var(--slider-timer-blue);
        }
        input[type="range"]:focus::-webkit-slider-thumb { box-shadow: none; }
        .actions { display: flex; gap: 8px; margin-top: auto; padding-top: 14px; }
        .actions.stacked { flex-direction: column; }
        .btn {
          flex: 1 1 0;
          display: inline-flex; align-items: center; justify-content: center; gap: 6px;
          height: 38px; padding: 0 10px;
          border: none; cursor: pointer;
          border-radius: var(--ha-card-border-radius, 12px);
          font-family: inherit; font-size: 14px; font-weight: 500;
          background: var(--slider-timer-blue); color: var(--text-primary-color, #fff);
        }
        .btn.pause { background: var(--slider-timer-yellow); color: #1c1c1c; }
        .actions.stacked .btn { flex: 0 0 auto; width: 100%; height: 52px; }
        .btn ha-icon { --mdc-icon-size: 18px; }
        .btn.secondary { background: transparent; border: 1px solid var(--divider-color); color: var(--primary-text-color); }
        .btn:disabled { opacity: .5; cursor: default; }
        .btn[hidden], .sliders[hidden], .actions[hidden], .gear[hidden] { display: none; }
      </style>
      <ha-card>
        <div class="wrap">
          <div class="head">
            <ha-icon icon="${c.icon}"></ha-icon>
            <span class="name"></span>
            <span class="state"><ha-icon></ha-icon><span class="state-text"></span></span>
            <button class="gear" type="button" hidden
                    title="${t.settings}" aria-label="${t.settings}">
              <ha-icon icon="mdi:cog"></ha-icon>
            </button>
          </div>
          <div class="countdown">00:00:00</div>
          <div class="body">
            <div class="sliders"></div>
            <div class="actions">
              <button class="btn start" data-action="start"><ha-icon icon="mdi:play"></ha-icon><span>${t.buttons.start}</span></button>
              <button class="btn pause" data-action="pause"><ha-icon icon="mdi:pause"></ha-icon><span>${t.buttons.pause}</span></button>
              <button class="btn resume" data-action="resume"><ha-icon icon="mdi:play-pause"></ha-icon><span>${t.buttons.resume}</span></button>
              <button class="btn secondary cancel" data-action="cancel"><ha-icon icon="mdi:close"></ha-icon><span>${t.buttons.cancel}</span></button>
            </div>
          </div>
        </div>
      </ha-card>
    `;

    this._nameEl = this.shadowRoot.querySelector(".name");
    this._stateEl = this.shadowRoot.querySelector(".state");
    this._stateIconEl = this.shadowRoot.querySelector(".state ha-icon");
    this._stateTextEl = this.shadowRoot.querySelector(".state-text");
    this._countdownEl = this.shadowRoot.querySelector(".countdown");
    this._slidersEl = this.shadowRoot.querySelector(".sliders");
    this._actionsEl = this.shadowRoot.querySelector(".actions");
    this._gearEl = this.shadowRoot.querySelector(".gear");
    this._buttons = {
      start: this.shadowRoot.querySelector(".start"),
      pause: this.shadowRoot.querySelector(".pause"),
      resume: this.shadowRoot.querySelector(".resume"),
      cancel: this.shadowRoot.querySelector(".cancel"),
    };

    this._nameEl.textContent = c.name || t.timer;

    this._buildSliders();

    this.shadowRoot.querySelectorAll(".btn").forEach((btn) => {
      btn.addEventListener("click", () => this._onAction(btn.dataset.action));
    });
    this._gearEl.addEventListener("click", () => this._openSettings());

    this._built = true;
  }

  _buildSliders() {
    this._slidersEl.textContent = "";
    this._inputs = {};
    this._labels = {};

    for (const field of this._fields) {
      const row = document.createElement("div");
      row.className = "slider-row";

      const label = document.createElement("span");
      label.className = "slider-label";
      label.textContent = field.label;

      const input = document.createElement("input");
      input.type = "range";
      input.min = "0";
      input.max = String(this._fieldMax(field));
      input.step = "1";
      input.dataset.key = field.key;
      input.addEventListener("input", () => {
        this._dragging[field.key] = true;
        this._paintSlider(input);
        if (this._labels[field.key]) {
          this._labels[field.key].textContent = input.value;
        }
      });
      input.addEventListener("change", () => {
        this._dragging[field.key] = false;
        this._commit(field.key, Number(input.value));
      });

      const value = document.createElement("span");
      value.className = "slider-value";
      value.textContent = "0";

      row.appendChild(label);
      row.appendChild(input);
      row.appendChild(value);
      this._slidersEl.appendChild(row);

      this._inputs[field.key] = input;
      this._labels[field.key] = value;
    }
  }

  /* The upper limit of the slider. When the slider of a bigger unit is hidden,
   * this field can carry the whole unit: minutes up to 60, seconds up to 60.
   * That way the hidden hours leave no "gap" - 60 minutes can be given instead of 59.
   * The entity's own upper bound is the ceiling: nothing larger can be saved,
   * while the hours are capped at 24 (HOURS_MAX). */
  _fieldMax(field) {
    const index = CARD_FIELDS.findIndex((f) => f.key === field.key);
    const bigger = index > 0 ? CARD_FIELDS[index - 1] : null;
    const hiddenBigger = !!bigger && !this._fields.some((f) => f.key === bigger.key);

    const st = this._entityState(this._numberEntity(this._target(), field.key));
    const entityMax =
      st && st.attributes.max !== undefined ? Number(st.attributes.max) : null;
    const ceiling =
      Number.isFinite(entityMax) && entityMax > 0
        ? entityMax
        : field.key === "hours"
          ? HOURS_MAX
          : 59;

    let wanted;
    if (field.key === "hours") {
      wanted = Math.min(ceiling, HOURS_MAX);
    } else if (hiddenBigger) {
      wanted = 60;
    } else {
      wanted = Math.min(ceiling, 59);
    }
    return Math.min(wanted, ceiling);
  }

  /* ---- state -> display ---- */
  _entityState(entityId) {
    return this._hass && this._hass.states[entityId]
      ? this._hass.states[entityId]
      : null;
  }

  /* ---- the timer's source: the slider_timer integration ---- */

  /* The target in use and its entities: from the given `entity`, or by automatic
   * discovery (platform: slider_timer), narrowed by `name`. */
  _target() {
    if (!this._hass || !this._hass.entities) return null;
    return this._integrationTarget();
  }

  _integrationTarget() {
    const c = this._config || {};

    if (c.entity) {
      const group = this._groupForEntity(c.entity);
      return this._makeTarget(group || { remaining: c.entity });
    }

    const groups = this._integrationGroups();
    if (!groups.length) return null;

    const nameSpecified = Object.prototype.hasOwnProperty.call(c, "name");
    if (nameSpecified) {
      const match = this._groupForName(groups, c.name);
      if (match) return this._makeTarget(match);
      return null;
    }

    const match = this._groupForName(groups, c.name);
    if (match) return this._makeTarget(match);

    groups.sort((a, b) => this._deviceName(a).localeCompare(this._deviceName(b)));
    return this._makeTarget(groups[0]);
  }

  /* The group picked by the card's `name`. The timer's device name may either
   * be a part of it ("Nappali időzítő" -> Nappali) or contain it ("Nap" ->
   * Nappali); an exact match wins, then the containing one. Without a match
   * the caller falls back to the first timer, so a plain header text (or a
   * single timer) keeps working. */
  _groupForName(groups, wanted) {
    const text =
      wanted === undefined || wanted === null
        ? ""
        : String(wanted).trim().toLowerCase();
    if (!text) return null;

    let best = null;
    let bestScore = 0;
    for (const group of groups) {
      const name = this._deviceName(group).toLowerCase();
      if (!name) continue;
      let score = 0;
      if (name === text) score = 3;
      else if (text.includes(name)) score = 2;
      else if (name.includes(text)) score = 1;
      if (score > bestScore) {
        best = group;
        bestScore = score;
      } else if (score === bestScore && bestScore > 0) {
        best = null;
      }
    }
    return best;
  }

  /* The slider_timer platform entities grouped per device. */
  _integrationGroups() {
    const groups = {};
    const entities = (this._hass && this._hass.entities) || {};
    for (const entityId in entities) {
      const reg = entities[entityId];
      if (!reg || reg.platform !== INTEGRATION_PLATFORM) continue;
      const slot = this._entityKey(reg, entityId);
      if (!slot) continue;
      const groupKey = reg.device_id || entityId;
      const group = groups[groupKey] || (groups[groupKey] = { device_id: reg.device_id || null });
      if (!group[slot]) group[slot] = entityId;
    }
    return Object.values(groups).filter((group) => group.remaining);
  }

  /* The entity key (remaining / hours / minutes / seconds): first the
   * translation_key, otherwise the entity ID suffix (the Hungarian name or the
   * English alias). */
  _entityKey(reg, entityId) {
    const tk = reg.translation_key;
    if (tk && INTEGRATION_KEYS.includes(tk)) return tk;
    if (tk && LEGACY_TRANSLATION_KEYS[tk]) return LEGACY_TRANSLATION_KEYS[tk];
    for (const key of INTEGRATION_KEYS) {
      for (const suffix of INTEGRATION_SUFFIXES[key]) {
        if (entityId.endsWith("_" + suffix)) return key;
      }
    }
    return null;
  }

  _groupForEntity(entityId) {
    const reg = this._hass.entities[entityId];
    if (!reg || !reg.device_id) return null;
    return this._integrationGroups().find((g) => g.device_id === reg.device_id) || null;
  }

  _makeTarget(group) {
    if (!group || !group.remaining) return null;
    const device =
      group.device_id && this._hass.devices ? this._hass.devices[group.device_id] : null;
    return {
      sensor: group.remaining,
      numbers: {
        hours: group.hours || null,
        minutes: group.minutes || null,
        seconds: group.seconds || null,
      },
      device,
    };
  }

  _deviceName(group) {
    const device =
      group && group.device_id && this._hass.devices
        ? this._hass.devices[group.device_id]
        : null;
    return device ? device.name_by_user || device.name || "" : "";
  }

  /* ---- display options (2.1.0, from the visual editor) ---- */

  /* Which sliders are shown. Whatever is hidden counts as 0: it appears
   * neither in the shown duration nor on start. */
  _visibleFields() {
    const c = this._config || {};
    if (Array.isArray(c.fields)) {
      return cardFields(this._t()).filter(
        (field) => c.fields.indexOf(field.key) !== -1
      );
    }
    /* Backward compatibility: show_hours / show_minutes / show_seconds. */
    return cardFields(this._t()).filter((field) => {
      if (field.key === "hours") return c.show_hours !== false;
      if (field.key === "minutes") return c.show_minutes !== false;
      return c.show_seconds !== false;
    });
  }

  /* Which buttons are shown (a missing/empty setting means all). */
  _enabledButtons() {
    const c = this._config || {};
    if (!Array.isArray(c.buttons) || !c.buttons.length) return ALL_BUTTONS.slice();
    return ALL_BUTTONS.filter((name) => c.buttons.indexOf(name) !== -1);
  }

  /* The gear leads to the timer's integration settings. In phase 3 this is
   * replaced by the settings section inside the card. */
  _openSettings() {
    const path = "/config/integrations/integration/" + INTEGRATION_PLATFORM;
    try {
      window.history.pushState(null, "", path);
      window.dispatchEvent(new Event("location-changed"));
    } catch (_err) {
      window.location.href = path;
    }
  }

  /* The duration entity: the discovered number entity. */
  _numberEntity(target, key) {
    return (target && target.numbers && target.numbers[key]) || null;
  }

  _configuredSeconds(target) {
    const source = target || this._target();
    let total = 0;
    /* Only the visible fields count - a hidden slider counts as 0. */
    for (const field of this._fields) {
      const st = this._entityState(this._numberEntity(source, field.key));
      const n = st ? parseInt(st.state, 10) : 0;
      total += (Number.isFinite(n) ? n : 0) * (field.key === "hours" ? 3600 : field.key === "minutes" ? 60 : 1);
    }
    return total;
  }

  /* The duration sent on start. When every field is visible, null: in that
   * case the server works from the Hours/Minutes/Seconds entities. When one
   * is hidden, we pass only the visible ones, the hidden ones as 0. */
  _durationParams(target) {
    if (this._fields.length === CARD_FIELDS.length) return null;
    const params = {};
    for (const field of CARD_FIELDS) {
      if (this._fields.some((f) => f.key === field.key)) {
        const st = this._entityState(this._numberEntity(target, field.key));
        const n = st ? parseInt(st.state, 10) : 0;
        params[field.key] = Number.isFinite(n) && n > 0 ? n : 0;
      } else {
        params[field.key] = 0;
      }
    }
    return params;
  }

  /* The data of the `start` service from the card's `expiry:` block.
   *
   * We pass only the filled-in fields; for the rest the integration's setting
   * applies. For an old (expiry-less) configuration it stays empty and
   * everything comes from the integration. */
  _expiryPayload() {
    const expiry = (this._config && this._config.expiry) || null;
    const data = {};
    if (!expiry || typeof expiry !== "object") return data;

    const text = (raw) => (typeof raw === "string" ? raw.trim() : "");
    const mediaPlayer = text(expiry.media_player);
    if (mediaPlayer) data.media_player = mediaPlayer;
    const soundFile = text(expiry.sound_file);
    if (soundFile) data.sound_file = soundFile;
    const after = text(expiry.sound_after);
    if (after) data.sound_after = after;
    const before = text(expiry.sound_before);
    if (before) data.sound_before = before;
    if (Array.isArray(expiry.actions) && expiry.actions.length) {
      data.actions = expiry.actions;
    }
    return data;
  }

  /* A snapshot for the display. */
  _snapshot() {
    const target = this._target();
    let state = "none";
    let endsAt = null;
    let remainingSeconds = 0;

    if (target) {
      const st = this._entityState(target.sensor);
      const attrs = (st && st.attributes) || {};
      state = attrs.status || "idle";
      endsAt = attrs.ends_at || null;
      remainingSeconds = Number(attrs.remaining_seconds) || 0;
      if (state === "active" && endsAt) {
        const ms = new Date(endsAt).getTime() - Date.now();
        if (Number.isFinite(ms)) remainingSeconds = ms / 1000;
      } else if (state === "idle") {
        remainingSeconds = this._configuredSeconds(target);
      }
    } else {
      remainingSeconds = this._configuredSeconds(null);
    }

    return { target, state, endsAt, remainingSeconds };
  }

  _update() {
    if (!this._built || !this._hass) return;
    this._applyLanguage();
    const t = this._t();

    const snap = this._snapshot();
    const target = snap.target;
    const state = snap.state;
    const running = state === "active" || state === "paused";

    this._nameEl.textContent =
      this._config.name ||
      (target && target.device
        ? target.device.name_by_user || target.device.name
        : t.timer);

    this._countdownEl.textContent = secondsToClock(snap.remainingSeconds);
    this._countdownEl.className = `countdown ${running ? state : ""}`;
    this._stateIconEl.setAttribute("icon", STATE_ICON[state] || STATE_ICON.idle);
    this._stateTextEl.textContent =
      state === "none" ? t.noTimer : t.state[state] || state;
    this._stateEl.className = `state ${running ? state : ""}`;

    this._slidersEl.hidden = state !== "idle";
    this._actionsEl.classList.toggle("stacked", running);

    const enabled = this._enabledButtons();
    const wanted = (name) => enabled.indexOf(name) !== -1;
    this._actionsEl.hidden = enabled.length === 0;
    this._buttons.start.hidden = !wanted("start") || running;
    this._buttons.pause.hidden = !wanted("pause") || state !== "active";
    this._buttons.resume.hidden = !wanted("resume") || state !== "paused";
    this._buttons.cancel.hidden = !wanted("cancel") || !running;
    this._gearEl.hidden = !this._config.settings_button;

    this._syncSliders(target);

    const locked = Date.now() < this._lockedUntil || state === "none";
    Object.values(this._buttons).forEach((btn) => {
      btn.disabled = locked;
    });

    if (this._active) {
      this._schedule();
    }
  }

  /* coloring the filled part of the slider (the --fill CSS variable) */
  _paintSlider(input) {
    if (!input) return;
    const min = Number(input.min);
    const max = Number(input.max);
    const val = Number(input.value);
    const lo = Number.isFinite(min) ? min : 0;
    const hi = Number.isFinite(max) && max > lo ? max : lo + 1;
    const v = Number.isFinite(val) ? Math.min(Math.max(val, lo), hi) : lo;
    const pct = ((v - lo) / (hi - lo)) * 100;
    input.style.setProperty("--fill", `${pct.toFixed(2)}%`);
  }

  _syncSliders(target) {
    const source = target || this._target();
    for (const field of this._fields) {
      if (this._dragging[field.key]) continue;

      const st = this._entityState(this._numberEntity(source, field.key));
      const input = this._inputs[field.key];
      if (!st || !input) continue;

      const min = st.attributes.min !== undefined ? st.attributes.min : 0;
      const max = this._fieldMax(field);
      const step = st.attributes.step !== undefined ? st.attributes.step : 1;
      input.min = String(min);
      input.max = String(max);
      input.step = String(step);

      const value = parseInt(st.state, 10);
      if (Number.isFinite(value)) {
        input.value = String(value);
        this._labels[field.key].textContent = String(value);
      }
      this._paintSlider(input);
    }
  }

  /* ---- actions ---- */
  _commit(key, value) {
    const entityId = this._numberEntity(this._target(), key);
    if (!entityId || !this._hass) return;
    const domain = entityId.split(".")[0];
    this._hass.callService(domain, "set_value", {
      entity_id: entityId,
      value: value,
    });
  }

  _onAction(action) {
    if (!this._hass) return;
    if (Date.now() < this._lockedUntil) return;

    const target = this._target();
    if (!target) return;

    this._lockedUntil = Date.now() + 700;
    this._update();

    /* For the integration the duration comes from the Hours/Minutes/Seconds
     * entities. When every slider is visible, we pass no separate value (the
     * server decides). When one is hidden, we pass the visible fields - the
     * hidden one as 0. On start we also pass the card's `expiry:` block: the
     * sound and the action run on the server even when the dashboard is closed at expiry. */
    const data = { entity_id: target.sensor };
    if (action === "start") {
      const params = this._durationParams(target);
      if (params) Object.assign(data, params);
      Object.assign(data, this._expiryPayload());
    }
    this._hass.callService(INTEGRATION_PLATFORM, action, data);

    window.setTimeout(() => this._update(), 750);
  }
}

/* ------------------------------------------------------------------ editor
 *
 * The visual editor (`getConfigElement`) is likewise made without dependencies:
 * we use the HA `ha-form` element, which only has to be set as a property.
 * The schema appears in the dashboard's "Add card" dialog.
 *
 * The editor only writes the EDITOR_KEYS keys; every other, hand-written key
 * is left untouched.
 */

/* ---- expiry settings (integration timer) ----
 *
 * These live in the card's YAML `expiry:` block. On start the card passes
 * them to the `slider_timer.start` service, and the sound and the action run on
 * the server - the dashboard may be closed at expiry. That is why the editor
 * only writes the card's configuration. Anything we leave empty uses the
 * integration entry's setting (that remains the default).
 */

const EXPIRY_SCHEMA = [
  { name: "actions", selector: { action: {} } },
  { name: "media_player", selector: { entity: { domain: "media_player" } } },
  { name: "sound_file", selector: { text: {} } },
  {
    name: "",
    type: "grid",
    schema: [
      { name: "sound_after", selector: { time: {} } },
      { name: "sound_before", selector: { time: {} } },
    ],
  },
];

/* The HA time field (`ha-base-time-input`) saves on the native `change`
 * event, which fires on Enter and on leaving the field. So that the time
 * window is saved while typing too, we trigger `change` ourselves after a
 * short pause (see `_onExpiryInput`). The inputs of the time field carry
 * these names. */
const TIME_INPUT_NAMES = ["hours", "minutes", "seconds"];
const TIME_INPUT_COMMIT_DELAY = 400;

/* The keys always handled (rewritten) by the editor - nothing else is overwritten. */
const EDITOR_KEYS = [
  "entity",
  "name",
  "icon",
  "fields",
  "show_hours",
  "show_minutes",
  "show_seconds",
  "buttons",
  "settings_button",
];
/* The keys of the old (timer.*) mode: the card no longer uses them, so the
 * editor drops them from the config on every save. */
const LEGACY_KEYS = ["timer", "start_script", "hours", "minutes", "seconds"];

class SliderTimerCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._form = null;
    this._expiryForm = null;
    this._expiryShown = null;
    /* The current value of the expiry form (the card's `expiry:` block). */
    this._expiryData = {};
    this._optionsKey = "";
    this._emitted = null;
    /* The HA "config" string set is requested only once (see below). */
    this._configFragmentRequested = false;
    /* The time fields touched while typing (see `_onExpiryInput`). */
    this._pendingTimeInputs = new Set();
    this._commitTimer = null;
  }

  set hass(hass) {
    this._hass = hass || null;
    if (!this._form) {
      this._lang = textLang(this._hass);
      this._render();
      return;
    }
    if (textLang(this._hass) !== this._lang) {
      this._lang = textLang(this._hass);
      this._render();
      return;
    }
    this._form.hass = this._hass;
    if (this._expiryForm) this._expiryForm.hass = this._hass;
    /* We only redraw when the list of timers has actually changed. */
    if (this._timerOptionsKey() !== this._optionsKey) this._render();
  }

  get hass() {
    return this._hass;
  }

  _t() {
    return TEXTS[textLang(this._hass)];
  }

  /* The labels of the action selector (and its dialog) come from the HA
   * "config" string set (e.g. "Add action"). On a dashboard it is not loaded
   * by default, so - like the HA card-conditions editor does - we request it
   * once here. */
  _loadConfigFragment() {
    if (this._configFragmentRequested) return;
    if (!this._hass || typeof this._hass.loadFragmentTranslation !== "function") {
      return;
    }
    this._configFragmentRequested = true;
    this._hass.loadFragmentTranslation("config");
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
    /* We do not write our own emitted config echo back into the form,
     * otherwise the editor focus would be lost after every keystroke. */
    if (
      this._form &&
      this._emitted !== null &&
      JSON.stringify(this._config) === this._emitted
    ) {
      return;
    }
    this._render();
  }

  /* ---- the items of the timer selector ---- */

  _friendlyName(entityId) {
    const st = this._hass && this._hass.states ? this._hass.states[entityId] : null;
    return (st && st.attributes && st.attributes.friendly_name) || entityId;
  }

  _timerOptions() {
    const options = [];
    if (!this._hass) return options;

    const entities = this._hass.entities || {};
    for (const entityId of Object.keys(entities)) {
      const reg = entities[entityId];
      if (!reg || reg.platform !== INTEGRATION_PLATFORM) continue;
      const isRemaining =
        reg.translation_key === "remaining" ||
        reg.translation_key === "hatralevo" ||
        (entityId.startsWith("sensor.") &&
          (entityId.endsWith("_hatralevo") || entityId.endsWith("_remaining")));
      if (!isRemaining) continue;
      options.push({
        value: entityId,
        label: `${this._friendlyName(entityId)} (${this._t().editor.integration})`,
      });
    }

    /* If the config contains an entity that is not in the list right now. */
    const current = this._config.entity || "";
    if (current && !options.some((o) => o.value === current)) {
      options.push({ value: current, label: `${this._friendlyName(current)} (?)` });
    }
    return options;
  }

  _timerOptionsKey() {
    return JSON.stringify(this._timerOptions().map((o) => o.value));
  }

  /* ---- the selected timer ---- */

  _selectedEntity() {
    return this._config.entity || "";
  }

  /* ---- expiry settings (the card's `expiry:` block) ---- */

  _hintText() {
    const t = this._t().editor;
    if (!this._expiryShown) return t.hintNoTimer;
    return t.hintText;
  }

  /* The card's `expiry` block from the value of the expiry form.
   * Only the filled-in fields go in; for the ones left empty the integration's
   * setting applies. When everything is empty, there is no `expiry` key. */
  _expiryBlock(values) {
    const source = values || {};
    const block = {};
    const text = (raw) => (typeof raw === "string" ? raw.trim() : "");
    const mediaPlayer = text(source.media_player);
    if (mediaPlayer) block.media_player = mediaPlayer;
    const soundFile = text(source.sound_file);
    if (soundFile) block.sound_file = soundFile;
    const after = text(source.sound_after);
    if (after) block.sound_after = after;
    const before = text(source.sound_before);
    if (before) block.sound_before = before;
    const actions = Array.isArray(source.actions)
      ? source.actions.filter((a) => a && Object.keys(a).length)
      : [];
    if (actions.length) block.actions = actions;
    return Object.keys(block).length ? block : null;
  }

  /* The keys of the checked sliders (also from the old show_* keys). */
  _visibleFieldKeys(config) {
    const c = config || {};
    if (Array.isArray(c.fields)) {
      return CARD_FIELDS.filter((f) => c.fields.indexOf(f.key) !== -1).map(
        (f) => f.key
      );
    }
    return CARD_FIELDS.filter((f) => {
      if (f.key === "hours") return c.show_hours !== false;
      if (f.key === "minutes") return c.show_minutes !== false;
      return c.show_seconds !== false;
    }).map((f) => f.key);
  }

  /* ---- schema and data ---- */

  _schema() {
    const schema = [
      {
        name: "entity",
        selector: { select: { mode: "dropdown", options: this._timerOptions() } },
      },
      { name: "name", selector: { text: {} } },
      { name: "icon", selector: { icon: {} } },
      {
        name: "fields",
        selector: {
          select: { multiple: true, mode: "list", options: fieldOptions(this._t()) },
        },
      },
      {
        name: "buttons",
        selector: {
          select: { multiple: true, mode: "list", options: buttonOptions(this._t()) },
        },
      },
      { name: "settings_button", selector: { boolean: {} } },
    ];
    return schema;
  }

  _data() {
    const c = this._config || {};
    const data = {
      entity: c.entity || "",
      name: c.name || "",
      icon: c.icon || "mdi:timer-outline",
      fields: this._visibleFieldKeys(c),
      buttons:
        Array.isArray(c.buttons) && c.buttons.length
          ? c.buttons.slice()
          : ALL_BUTTONS.slice(),
      settings_button: c.settings_button === true,
    };
    return data;
  }

  /* ---- rendering ---- */

  _render() {
    const showExpiry = !!this._selectedEntity();
    if (showExpiry) this._loadConfigFragment();
    const rebuild = !this._form || showExpiry !== this._expiryShown;

    if (rebuild) {
      this._expiryShown = showExpiry;
      this._buildDom(showExpiry);
    }

    this._form.hass = this._hass;
    this._form.schema = this._schema();
    this._form.data = this._data();
    this._optionsKey = this._timerOptionsKey();

    const hint = this.shadowRoot.querySelector(".hint");
    if (hint) hint.textContent = this._hintText();

    this._alignListFields();
  }

  /* HA centers the checkboxes of the list (multiple-choice) fields
   * (`ha-checkbox{display:flex; justify-content:center}`) and puts the helper
   * text (`ha-input-helper-text`) at the left edge with a 16 px indent - so the
   * two do not line up. With a style injected into the shadow root of the list
   * field, the checkboxes also move into the 16 px text column, aligned with
   * the left edge of the helper text.
   *
   * The selector is deliberately `div > ha-checkbox`: HA inserts its own
   * stylesheet as `adoptedStyleSheets` into the shadow root of
   * `ha-selector-select`, and it overrides any later-inserted rule of ours
   * with the same specificity (Chrome puts adopted sheets at the end of the
   * order). Because of the higher specificity, however, our rule wins. The
   * `ha-selector-select` is created in the selector's own shadow DOM with a
   * delay, so we wait for it with a few short attempts. */
  _alignListFields(attempt) {
    const tries = typeof attempt === "number" ? attempt : 0;
    let pending = 0;
    for (const form of [this._form, this._expiryForm]) {
      if (!form || !form.shadowRoot) continue;
      for (const selector of form.shadowRoot.querySelectorAll("ha-selector")) {
        const select = selector.selector && selector.selector.select;
        if (!select || !select.multiple) continue;
        const inner = selector.shadowRoot
          ? selector.shadowRoot.querySelector("ha-selector-select")
          : null;
        if (!inner || !inner.shadowRoot) {
          pending += 1;
          continue;
        }
        if (!inner.shadowRoot.querySelector("ha-checkbox")) continue;
        if (inner.shadowRoot.querySelector("style[data-slider-timer-align]")) continue;
        const style = document.createElement("style");
        style.setAttribute("data-slider-timer-align", "");
        /* A `div >` is not decoration: HA's own stylesheet (adoptedStyleSheets)
         * would override our rule of the same specificity. */
        style.textContent =
          "div > ha-checkbox{justify-content:flex-start;padding-inline-start:16px}";
        inner.shadowRoot.appendChild(style);
      }
    }
    if (pending && tries < 20) {
      setTimeout(() => this._alignListFields(tries + 1), 150);
    }
  }

  _buildDom(showExpiry) {
    const t = this._t().editor;
    /* We drop any pending time-field save: the old DOM elements are about
     * to disappear. */
    this._pendingTimeInputs.clear();
    if (this._commitTimer !== null) {
      clearTimeout(this._commitTimer);
      this._commitTimer = null;
    }
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .hint {
          padding: 30px 2px 0;
          font-size: 12px;
          line-height: 1.4;
          color: var(--secondary-text-color);
        }
        .section {
          margin-top: 20px;
          padding-top: 12px;
          border-top: 1px solid var(--divider-color);
        }
        .section-title {
          padding: 0 2px 4px;
          font-size: 14px;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .section .note {
          padding: 0 2px 8px;
          font-size: 12px;
          line-height: 1.4;
          color: var(--secondary-text-color);
        }
        .note code {
          font-family: var(--code-font-family, monospace);
        }
      </style>
      <ha-form class="card"></ha-form>
      ${
        showExpiry
          ? `<div class="section">
        <div class="section-title">${t.expiryTitle}</div>
        <div class="note">${t.expiryNote}</div>
        <ha-form class="expiry"></ha-form>
      </div>`
          : ""
      }
      <div class="hint"></div>
    `;

    this._form = this.shadowRoot.querySelector("ha-form.card");
    this._form.computeLabel = (item) =>
      this._t().editor.labels[item.name] || item.name;
    this._form.computeHelper = (item) =>
      this._t().editor.helpers[item.name] || "";
    this._form.addEventListener("value-changed", (ev) => {
      ev.stopPropagation();
      this._onChanged(ev.detail.value);
    });

    this._expiryForm = this.shadowRoot.querySelector("ha-form.expiry");
    if (this._expiryForm) {
      this._expiryData = Object.assign({}, this._config.expiry || {});
      this._expiryForm.hass = this._hass;
      this._expiryForm.schema = EXPIRY_SCHEMA;
      this._expiryForm.data = this._expiryData;
      this._expiryForm.computeLabel = (item) =>
        this._t().editor.expiryLabels[item.name] || item.name;
      this._expiryForm.computeHelper = (item) =>
        this._t().editor.expiryHelpers[item.name] || "";
      this._expiryForm.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        this._onExpiryChanged(ev.detail.value);
      });
      this._expiryForm.addEventListener("input", (ev) => this._onExpiryInput(ev));
    }
  }

  /* A change of the top form; the expiry block is the last known value. */
  _onChanged(value) {
    this._emit(this._buildConfig(value || {}, this._expiryData));
  }

  /* A change of the expiry form (automatic save into the card's YAML). */
  _onExpiryChanged(value) {
    this._expiryData = value || {};
    this._emit(this._buildConfig(this._data(), this._expiryData));
  }

  /* The HA time field only saves on the native `change` event (Enter or
   * leaving the field). For the time window it is handier if it also saves
   * while typing: we watch the `input` event of the hours/minutes/seconds
   * input and, after a short pause, trigger `change` ourselves. That way HA's
   * own processing runs unchanged (formatting, 12/24 hour, seconds). */
  _onExpiryInput(ev) {
    const input = this._timeInputFrom(ev);
    if (!input) return;
    this._pendingTimeInputs.add(input);
    if (this._commitTimer !== null) clearTimeout(this._commitTimer);
    this._commitTimer = setTimeout(() => {
      this._commitTimer = null;
      this._commitTimeInputs();
    }, TIME_INPUT_COMMIT_DELAY);
  }

  /* From the `input` event we find the time field's input (hours/minutes/seconds). */
  _timeInputFrom(ev) {
    const path = typeof ev.composedPath === "function" ? ev.composedPath() : [];
    for (const node of path) {
      if (!node || node.localName !== "ha-input") continue;
      const name =
        node.name ||
        (typeof node.getAttribute === "function" ? node.getAttribute("name") : "");
      if (TIME_INPUT_NAMES.indexOf(name) !== -1) return node;
    }
    return null;
  }

  _commitTimeInputs() {
    const pending = Array.from(this._pendingTimeInputs);
    this._pendingTimeInputs.clear();
    for (const input of pending) {
      /* If the field disappeared in the meantime (mode switch, closed editor),
       * we send no event. */
      if (input.isConnected === false) continue;
      try {
        input.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
      } catch (err) {
        /* If the internal structure of the HA time field changes, we do no harm:
         * the value is then saved in the usual way (with Enter or on losing
         * focus). */
      }
    }
  }

  _emit(config) {
    this._config = config;
    this._emitted = JSON.stringify(config);
    /* When the expiry section appears or disappears, the schema changes too. */
    this._render();
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      })
    );
  }

  _buildConfig(value, expiryValue) {
    const config = Object.assign({}, this._config);

    /* The keys handled by the editor are always rewritten; the leftover keys of
     * the old (timer.*) mode are dropped - the card no longer uses them. */
    for (const key of EDITOR_KEYS.concat(LEGACY_KEYS)) delete config[key];
    delete config.expiry;

    const selected = String(value.entity || "");
    if (selected) config.entity = selected;

    if (value.name) config.name = value.name;
    if (value.icon && value.icon !== "mdi:timer-outline") config.icon = value.icon;

    const fields = Array.isArray(value.fields) ? value.fields.slice() : [];
    if (fields.length < CARD_FIELDS.length) config.fields = fields;

    const buttons = Array.isArray(value.buttons) ? value.buttons.slice() : [];
    if (buttons.length && buttons.length < ALL_BUTTONS.length) config.buttons = buttons;
    if (value.settings_button) config.settings_button = true;

    if (selected) {
      const expiry = this._expiryBlock(expiryValue);
      if (expiry) config.expiry = expiry;
    }

    return config;
  }
}

if (!customElements.get("slider-timer-card")) {
  customElements.define("slider-timer-card", SliderTimerCard);
}
if (!customElements.get("slider-timer-card-editor")) {
  customElements.define("slider-timer-card-editor", SliderTimerCardEditor);
}

window.customCards = window.customCards || [];
const CARD_CUSTOM_ENTRY = {
  type: "slider-timer-card",
  name: TEXTS.en.cardName,
  description: TEXTS.en.cardDescription,
  preview: true,
};
if (!window.customCards.some((c) => c.type === "slider-timer-card")) {
  window.customCards.push(CARD_CUSTOM_ENTRY);
}

console.info(
  `%c SLIDER TIMER CARD %c ${SLIDER_TIMER_CARD_RUNTIME_VERSION} `,
  "background:#03a9f4;color:#fff;font-weight:700;border-radius:4px 0 0 4px;",
  "background:#2b2b2b;color:#fff;border-radius:0 4px 4px 0;"
);
