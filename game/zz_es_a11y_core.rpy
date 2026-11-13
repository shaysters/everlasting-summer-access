# Everlasting Summer Accessibility Mod - core
# Speech output through Prism, dialogue reading, scene and character
# announcements, and the story hotkeys. Screen navigation lives in
# zz_es_a11y_screens.rpy, image descriptions in zz_es_a11y_descriptions.rpy.

init -100 python:
    import __builtin__
    import os
    import re
    import sys
    import time
    import traceback as _es_traceback

    # ------------------------------------------------------------------
    # Logging: es_a11y_log.txt next to the game executable. Spoken text is
    # only logged when game/es_a11y_debug.txt exists.
    # ------------------------------------------------------------------

    ES_LOG_PATH = os.path.join(config.basedir, "es_a11y_log.txt")
    ES_LOG_SPEECH = os.path.exists(os.path.join(config.gamedir, "es_a11y_debug.txt"))
    # Used by automated tests: log speech without saying it.
    ES_MUTE = os.path.exists(os.path.join(config.gamedir, "es_a11y_mute.txt"))

    try:
        if os.path.getsize(ES_LOG_PATH) > 1000000:
            os.remove(ES_LOG_PATH)
    except Exception:
        pass

    def es_log(msg):
        try:
            if isinstance(msg, unicode):
                msg = msg.encode("utf-8")
            with __builtin__.open(ES_LOG_PATH, "a") as f:
                f.write("[{0}] {1}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), msg))
        except Exception:
            pass

    def es_log_exc(context):
        es_log("EXCEPTION in {0}:\n{1}".format(context, _es_traceback.format_exc()))

    es_log("=" * 60)
    ES_VERSION = "0.10.3"
    es_log("Everlasting Summer accessibility mod {0} loading.".format(ES_VERSION))

    # ------------------------------------------------------------------
    # Prism wrapper. game/prism.dll is the 64-bit build, matching
    # Everlasting Summer.exe. Prism chooses the best speech output
    # available (NVDA, JAWS, SAPI, ...).
    # ------------------------------------------------------------------

    PRISM_OK = 0
    PRISM_ERROR_ALREADY_INITIALIZED = 15

    class ESPrism(__builtin__.object):
        def __init__(self):
            self.available = False
            self.name = "none"
            self._dll = None
            self._backend = None
            self._failed_speaks = 0
            try:
                self._load()
            except Exception:
                es_log_exc("ESPrism._load")

        def _load(self):
            import ctypes

            if sys.maxsize <= 2 ** 32:
                es_log("Prism: the game was started as 32-bit; prism.dll is 64-bit only. "
                    "Start Everlasting Summer.exe, not Everlasting Summer-32.exe.")
                return
            path = os.path.join(config.gamedir, "prism.dll")
            if not os.path.exists(path):
                es_log("Prism: {0} not found.".format(path))
                return

            class PrismConfig(ctypes.Structure):
                _fields_ = [
                    ("version", ctypes.c_uint8),
                    ("registry", ctypes.c_void_p),
                    ("availability_callback", ctypes.c_void_p),
                    ("availability_userdata", ctypes.c_void_p),
                    ("availability_poll_interval_ms", ctypes.c_uint32),
                    ("availability_debounce_samples", ctypes.c_uint32),
                    ("availability_backoff_max_ms", ctypes.c_uint32),
                    ("availability_auto_power_manage", ctypes.c_bool),
                    ("availability_baseline_callback", ctypes.c_void_p),
                ]

            dll = ctypes.CDLL(path)
            dll.prism_config_init.restype = PrismConfig
            dll.prism_config_init.argtypes = []
            dll.prism_init.restype = ctypes.c_void_p
            dll.prism_init.argtypes = [ctypes.POINTER(PrismConfig)]
            dll.prism_registry_acquire_best.restype = ctypes.c_void_p
            dll.prism_registry_acquire_best.argtypes = [ctypes.c_void_p]
            dll.prism_backend_initialize.restype = ctypes.c_int
            dll.prism_backend_initialize.argtypes = [ctypes.c_void_p]
            dll.prism_backend_name.restype = ctypes.c_char_p
            dll.prism_backend_name.argtypes = [ctypes.c_void_p]
            dll.prism_backend_output.restype = ctypes.c_int
            dll.prism_backend_output.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_bool]
            dll.prism_backend_speak.restype = ctypes.c_int
            dll.prism_backend_speak.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_bool]
            dll.prism_backend_stop.restype = ctypes.c_int
            dll.prism_backend_stop.argtypes = [ctypes.c_void_p]

            self._cfg = dll.prism_config_init()
            ctx = dll.prism_init(ctypes.byref(self._cfg))
            if not ctx:
                es_log("Prism: prism_init failed.")
                return
            backend = dll.prism_registry_acquire_best(ctx)
            if not backend:
                es_log("Prism: no speech backend available.")
                return
            err = dll.prism_backend_initialize(backend)
            if err not in (PRISM_OK, PRISM_ERROR_ALREADY_INITIALIZED):
                es_log("Prism: backend initialize returned error {0}.".format(err))
                return

            self._dll = dll
            self._ctx = ctx
            self._backend = backend
            self.name = dll.prism_backend_name(backend) or "Prism"
            self.available = True
            es_log("Prism ready from {0}. Backend: {1}".format(path, self.name))

        def speak(self, text, interrupt=True):
            if not self.available:
                return False
            try:
                data = text.encode("utf-8")
                err = self._dll.prism_backend_output(self._backend, data, bool(interrupt))
                if err != PRISM_OK:
                    err = self._dll.prism_backend_speak(self._backend, data, bool(interrupt))
                if err != PRISM_OK:
                    self._failed_speaks += 1
                    if self._failed_speaks <= 5:
                        es_log("Prism: speak failed with error {0}.".format(err))
                    return False
                return True
            except Exception:
                es_log_exc("ESPrism.speak")
                return False

        def stop(self):
            if self.available:
                try:
                    self._dll.prism_backend_stop(self._backend)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Speech state shared by the whole mod. Everything that changes while
    # playing is kept on this object rather than in store variables, so
    # none of it ends up in save files.
    # ------------------------------------------------------------------

    class ESState(__builtin__.object):
        def __init__(self):
            # Keep one Prism instance for the whole process, across restarts.
            if getattr(sys, "_es_prism", None) is None:
                sys._es_prism = ESPrism()
            self.prism = sys._es_prism
            if not self.prism.available:
                es_log("Falling back to Ren'Py's built-in text to speech.")
            self.history = []
            self.review_index = -1
            self.last_line = u""
            # True while speech queued since the last dialogue line should
            # not be cut off by the next announcement or line.
            self.pending = False
            self.last_skipping = False
            self.present = {}
            self.current_scene = None
            # What was on screen before the last "scene" statement, so a
            # redraw of the same place and people stays quiet.
            self.redraw = {}
            # Other pictures (effects, captions) last shown, by tag.
            self.others = {}
            self.redraw_others = {}
            self.nav_index = {}
            self.nav_identity = None
            self.nav_previous = None
            self.just_loaded = False
            self.last_notify = (u"", 0.0)

        def clean(self, text):
            if text is None:
                return u""
            if not isinstance(text, unicode):
                text = unicode(__builtin__.str(text), "utf-8", "replace")
            text = re.sub(r"\{(w|p|nw|fast)[^}]*\}", u" ", text)
            text = re.sub(r"\{[^}]*\}", u"", text)
            text = text.replace(u"~", u" ")
            text = text.replace(u"’", u"'").replace(u"‘", u"'")
            text = text.replace(u"“", u'"').replace(u"”", u'"')
            return re.sub(r"\s+", u" ", text).strip()

        def speak(self, text, interrupt=True):
            text = self.clean(text)
            if not text:
                return
            if ES_LOG_SPEECH:
                es_log(u"SPEAK{0}: {1}".format("" if interrupt else " (queued)", text))
            if ES_MUTE:
                return
            if self.prism.available:
                self.prism.speak(text, interrupt)
            else:
                try:
                    renpy.display.tts.tts(text)
                except Exception:
                    pass

        def remember(self, text):
            text = self.clean(text)
            if not text:
                return
            self.last_line = text
            if not self.history or self.history[-1] != text:
                self.history.append(text)
                if len(self.history) > 500:
                    self.history = self.history[-500:]
            self.review_index = len(self.history) - 1

        def ui(self, text):
            # Menus and hotkey answers always cut off whatever is talking.
            self.pending = False
            self.speak(text, True)

        def announce(self, text, remember=True):
            # Scene, character and title announcements. The first one after
            # a dialogue line cuts that line off (the player has moved on);
            # later ones queue behind it.
            if remember:
                self.remember(text)
            self.speak(text, not self.pending)
            self.pending = True

        def line(self, text):
            # A redraw only counts until the story moves on.
            self.redraw = {}
            self.redraw_others = {}
            self.remember(text)
            self.speak(text, not self.pending)
            self.pending = False

    es = ESState()

    def es_tr(key, default=u""):
        # A string from the game's own interface translation table.
        try:
            value = store.translation_new.get(key)
            if value:
                return es.clean(value)
        except Exception:
            pass
        return default

    # ------------------------------------------------------------------
    # Character names, expressions and outfits for sprite announcements.
    # ------------------------------------------------------------------

    ES_CHARACTER_TAGS = ("dv", "sl", "un", "us", "mt", "el", "mi", "sh", "cs", "mz", "uv", "pi")

    ES_DEFAULT_NAMES = {
        "dv": u"Alisa", "sl": u"Slavya", "un": u"Lena", "us": u"Ulyana",
        "mt": u"Olga Dmitrievna", "el": u"Electronik", "mi": u"Miku",
        "sh": u"Shurik", "cs": u"Viola", "mz": u"Zhenya", "uv": u"Yulya",
        "pi": u"A pioneer",
    }

    ES_EXPRESSIONS = {
        "normal": u"", "smile": u"smiling", "smile2": u"smiling",
        "smile3": u"smiling", "normal_smile": u"smiling", "grin": u"grinning",
        "laugh": u"laughing", "laugh2": u"laughing", "happy": u"happy",
        "shy": u"shy", "shy2": u"shy", "sad": u"sad", "upset": u"upset",
        "angry": u"angry", "rage": u"furious", "scared": u"scared",
        "fear": u"frightened", "shocked": u"shocked", "surprise": u"surprised",
        "surprise2": u"surprised", "surp1": u"surprised", "surp2": u"surprised",
        "surp3": u"surprised", "bukal": u"surprised", "serious": u"serious",
        "cry": u"crying", "cry2": u"crying", "cry_smile": u"smiling through tears",
        "dontlike": u"displeased", "guilty": u"guilty", "tender": u"tender",
        "evil_smile": u"smiling wickedly", "fingal": u"with a black eye",
        "calml": u"calm",
    }

    ES_OUTFITS = {
        "pioneer": u"pioneer uniform", "pioneer2": u"pioneer uniform",
        "swim": u"swimsuit", "sport": u"sports uniform", "dress": u"dress",
        "panama": u"sun hat", "glasses": u"glasses", "stethoscope": u"stethoscope",
    }

    def es_char_name(tag):
        if store._preferences.language == "english" or store._preferences.language is None:
            return ES_DEFAULT_NAMES.get(tag, tag)
        return es_tr(tag, ES_DEFAULT_NAMES.get(tag, tag))

    def es_sprite_parts(attrs):
        # Splits sprite attributes into (expression, outfit, accessory).
        expr = outfit = acc = None
        for a in attrs:
            if a in ES_EXPRESSIONS and expr is None:
                expr = a
            elif a in ("pioneer", "pioneer2", "swim", "sport", "dress") and outfit is None:
                outfit = a
            elif a in ("panama", "glasses", "stethoscope"):
                acc = a
        return expr, outfit, acc

    def es_sprite_detail(attrs):
        expr, outfit, acc = es_sprite_parts(attrs)
        bits = []
        if expr and ES_EXPRESSIONS.get(expr):
            bits.append(ES_EXPRESSIONS[expr])
        if outfit and outfit not in ("pioneer", "pioneer2"):
            bits.append(u"in a " + ES_OUTFITS[outfit])
        if acc:
            bits.append(u"with " + ES_OUTFITS[acc])
        return u", ".join(bits)

    def es_who_is_here():
        names = []
        for tag in ES_CHARACTER_TAGS:
            attrs = es.present.get(tag)
            if attrs is None:
                continue
            detail = es_sprite_detail(attrs)
            names.append(es_char_name(tag) + (u", " + detail if detail else u""))
        if not names:
            return u"No one else is in view."
        if len(names) == 1:
            return u"In view: {0}.".format(names[0])
        return u"In view: {0}.".format(u"; ".join(names))

    # ------------------------------------------------------------------
    # Scene descriptions. ES_DESCRIPTIONS is filled in by
    # zz_es_a11y_descriptions.rpy, keyed by image name ("bg ext_beach_day").
    # ------------------------------------------------------------------

    ES_DESCRIPTIONS = {}

    ES_SILENT_IMAGES = __builtin__.set([
        "bg black", "black", "white", "red", "anim blink_up", "anim blink_down",
        "backdrop_back", "backdrop_new", "day_num",
    ])

    def es_inline_image_text(name):
        name = name.strip()
        text = ES_DESCRIPTIONS.get(name, u"")
        if text.startswith(u"Achievement banner: "):
            return text[len(u"Achievement banner: "):]
        if text:
            return text
        if name == "sdl_uv_chibi":
            return u"Yulya, the cat-eared girl:"
        try:
            # A route's icon, as used on the statistics page.
            for sec, routes in store.sdl_achv_section_to_routes.items():
                for r in routes:
                    if name in (r.get_icon_active(), r.get_icon_inactive()):
                        who = dict(ES_7DL_SECTIONS).get(sec, u"")
                        return u"{0}, {1}".format(who, es_7dl_image_text(r.get_title())).strip(u", ")
        except Exception:
            pass
        try:
            return es_7dl_image_text(name)
        except Exception:
            return u""

    ES_ONSCREEN_TEXT_TAGS =__builtin__.set(["alt_credits", "alt_credits_jap", "alt_letter"])

    def es_image_key(name):
        if name is None:
            return None
        if isinstance(name, __builtin__.basestring):
            parts = tuple(name.split())
        else:
            parts = tuple(name)
        return parts

    def es_scene_label(key):
        # Fallback when an image has no written description.
        tag = key.split()[0]
        rest = u" ".join(key.split()[1:])
        words = rest.replace(u"_", u" ")
        words = re.sub(r"\b(ext)\b", u"outside", words)
        words = re.sub(r"\b(int)\b", u"inside", words)
        if tag == "cg":
            return u"Illustration."
        return words.strip().capitalize() + u"."

    def es_describe_image(key):
        if key in ES_DESCRIPTIONS:
            return ES_DESCRIPTIONS[key]
        return None

    def es_scene_shown(parts):
        key = u" ".join(parts[:2])
        previous = es.current_scene
        es.current_scene = key
        if key == previous:
            # The same place drawn again: nothing new to hear.
            return
        # A new place: anyone who shows up now is news.
        es.redraw = {}
        es.redraw_others = {}
        if key in ES_SILENT_IMAGES or parts[0] in ES_SILENT_IMAGES:
            return
        if not persistent.es_a11y_scenes:
            return
        text = es_describe_image(key)
        if text is None:
            if ES_LOG_SPEECH:
                es_log(u"No description for {0}".format(key))
            if parts[0] == "anim":
                return
            text = es_scene_label(key)
        if text:
            es.announce(text)

    def es_other_shown(parts):
        # Images other than backgrounds and sprites with their own text
        # (full screen effects, the opening, title cards).
        if parts[0] == "urhere1":
            # A message scrawled all over the screen in ten handwritings.
            message = es.clean(getattr(store, "urhere", u""))
            if message:
                es.announce(u"Scrawled over and over, in many hands: " + message)
            return
        tag = parts[0]
        if tag in ("black", "white", "red"):
            # A plain colour fills the screen; the next place shown is a
            # change even if it is the one from before.
            es.current_scene = tag
            es.others.pop(tag, None)
            return
        key = u" ".join(parts)
        if es.others.get(tag) == key or es.redraw_others.get(tag) == key:
            # The same picture or caption shown again.
            es.others[tag] = key
            return
        es.others[tag] = key
        if parts[0] in ES_ONSCREEN_TEXT_TAGS and len(parts) > 1:
            # 7 Days of Summer shows narration as on-screen text:
            # show alt_credits "text".
            # The text arrives as written in the script, quotes and all.
            message = u" ".join(unicode(p) for p in parts[1:]).strip()
            if len(message) > 1 and message[0] == message[-1] and message[0] in u"\"'":
                message = message[1:-1]
            message = message.replace(u"\\n", u"\n")
            try:
                # Fill in [variables], as the game does when it draws it.
                message = renpy.substitutions.substitute(message)[0]
            except Exception:
                pass
            # Pictures inside the text (banners, route names) by name.
            message = re.sub(r"\{image=([^}]+)\}", lambda m: es_inline_image_text(m.group(1)) + u" ", message)
            lines = [l for l in (es.clean(l) for l in message.split(u"\n")) if l]
            out = []
            for i, l in enumerate(lines):
                following = lines[i + 1] if i + 1 < len(lines) else u""
                # A sentence carried over to the next line needs no stop.
                if l[-1] not in u".!?:,;…\"'" and not following[:1].islower():
                    l += u"."
                out.append(l)
            message = u" ".join(out)
            if message:
                es.announce(u"Caption: " + message)
            return
        text = ES_DESCRIPTIONS.get(key) or ES_DESCRIPTIONS.get(parts[0])
        if text and persistent.es_a11y_scenes:
            es.announce(text)

    def es_sprite_shown(tag, parts):
        attrs = tuple(parts[1:])
        old = es.present.get(tag)
        if old is None:
            # Shown again right after the scene was redrawn: only changes
            # in look are worth hearing.
            old = es.redraw.pop(tag, None)
        es.present[tag] = attrs
        if not persistent.es_a11y_characters:
            return
        name = es_char_name(tag)
        if old is None:
            detail = es_sprite_detail(attrs) if persistent.es_a11y_expressions else u""
            if not detail:
                # Outfit changes are worth hearing even with expressions off.
                expr, outfit, acc = es_sprite_parts(attrs)
                if outfit and outfit not in ("pioneer", "pioneer2"):
                    detail = u"in a " + ES_OUTFITS[outfit]
            es.announce(name + u" appears" + (u", " + detail if detail else u"") + u".")
            return
        old_expr, old_outfit, old_acc = es_sprite_parts(old)
        expr, outfit, acc = es_sprite_parts(attrs)
        if outfit != old_outfit and outfit:
            es.announce(u"{0} is now in {1}.".format(name, u"a " + ES_OUTFITS[outfit]))
        elif persistent.es_a11y_expressions and expr != old_expr and expr:
            word = ES_EXPRESSIONS.get(expr) or u"calm"
            es.announce(u"{0}: {1}.".format(name, word), remember=False)

    def es_on_show(name):
        if config.skipping:
            parts = es_image_key(name)
            if parts and parts[0] in ES_CHARACTER_TAGS:
                es.present[parts[0]] = tuple(parts[1:])
            elif parts and parts[0] in ("bg", "cg", "anim"):
                es.current_scene = u" ".join(parts[:2])
            return
        parts = es_image_key(name)
        if not parts:
            return
        tag = parts[0]
        if tag in ("bg", "cg", "anim") and len(parts) > 1:
            es_scene_shown(parts)
        elif tag in ES_CHARACTER_TAGS:
            es_sprite_shown(tag, parts)
        else:
            es_other_shown(parts)

    # Ren'Py modules survive a restart (the game restarts after the first
    # language choice), so hooks always wrap the original function, never a
    # proxy left over from before the restart.
    def es_original(fn):
        return getattr(fn, "_es_original", fn)

    def es_proxy(proxy, original):
        proxy._es_original = original
        return proxy

    es_orig_config_show = es_original(config.show)
    es_orig_renpy_show = es_original(renpy.show)
    es_orig_config_hide = es_original(config.hide)
    es_orig_renpy_hide = es_original(renpy.hide)
    es_orig_config_scene = es_original(config.scene)
    es_orig_renpy_scene = es_original(renpy.scene)

    def es_show_proxy(name, *args, **kwargs):
        try:
            layer = kwargs.get("layer")
            if layer in (None, "master"):
                es_on_show(name)
        except Exception:
            es_log_exc("es_show_proxy")
        return es_orig_config_show(name, *args, **kwargs)

    def es_renpy_show_proxy(name, *args, **kwargs):
        try:
            layer = kwargs.get("layer")
            if layer in (None, "master"):
                es_on_show(name)
        except Exception:
            es_log_exc("es_renpy_show_proxy")
        return es_orig_renpy_show(name, *args, **kwargs)

    def es_on_hide(name, layer):
        if layer not in (None, "master"):
            return
        parts = es_image_key(name)
        if not parts:
            return
        tag = parts[0]
        es.others.pop(tag, None)
        if tag in ES_CHARACTER_TAGS and tag in es.present:
            del es.present[tag]
            if persistent.es_a11y_characters and not config.skipping:
                es.announce(es_char_name(tag) + u" leaves.", remember=False)

    def es_hide_proxy(name, layer=None, *args, **kwargs):
        try:
            es_on_hide(name, layer)
        except Exception:
            es_log_exc("es_hide_proxy")
        return es_orig_config_hide(name, layer, *args, **kwargs)

    def es_renpy_hide_proxy(name, layer=None, *args, **kwargs):
        try:
            es_on_hide(name, layer)
        except Exception:
            es_log_exc("es_renpy_hide_proxy")
        return es_orig_renpy_hide(name, layer, *args, **kwargs)

    def es_on_scene():
        # Remember who and what was here, so that redrawing the same place
        # with the same people does not announce them all again.
        es.redraw.update(es.present)
        es.redraw_others.update(es.others)
        es.present = {}
        es.others = {}

    def es_scene_proxy(layer="master", *args, **kwargs):
        if layer in (None, "master"):
            es_on_scene()
        return es_orig_config_scene(layer, *args, **kwargs)

    def es_renpy_scene_proxy(layer="master", *args, **kwargs):
        if layer in (None, "master"):
            es_on_scene()
        return es_orig_renpy_scene(layer, *args, **kwargs)

    config.show = es_proxy(es_show_proxy, es_orig_config_show)
    renpy.show = es_proxy(es_renpy_show_proxy, es_orig_renpy_show)
    config.hide = es_proxy(es_hide_proxy, es_orig_config_hide)
    renpy.hide = es_proxy(es_renpy_hide_proxy, es_orig_renpy_hide)
    config.scene = es_proxy(es_scene_proxy, es_orig_config_scene)
    renpy.scene = es_proxy(es_renpy_scene_proxy, es_orig_renpy_scene)

    def es_rebuild_present():
        # After loading a save the sprite list is rebuilt from what is
        # actually on screen.
        es.present = {}
        es.current_scene = None
        try:
            for tag in renpy.get_showing_tags("master"):
                attrs = renpy.get_attributes(tag, "master") or ()
                if tag in ES_CHARACTER_TAGS:
                    es.present[tag] = tuple(attrs)
                elif tag in ("bg", "cg", "anim") and attrs:
                    es.current_scene = tag + u" " + attrs[0]
        except Exception:
            es_log_exc("es_rebuild_present")

    def es_describe_scene():
        es_rebuild_present()
        parts = []
        if es.current_scene and es.current_scene not in ES_SILENT_IMAGES:
            parts.append(es_describe_image(es.current_scene) or es_scene_label(es.current_scene))
        else:
            parts.append(u"The screen is dark.")
        parts.append(es_who_is_here())
        extra = es_7dl_tournament_summary()
        if extra:
            parts.append(extra)
        es.ui(u" ".join(parts))

    # 7 Days of Summer's card tournament draws its bracket as portraits only.
    ES_7DL_GAMBLERS = {"me": u"you", "un": u"Lena", "sl": u"Slavya", "dv": u"Alisa",
        "mi": u"Miku", "us": u"Ulyana", "sh": u"Shurik", "mz": u"Zhenya"}

    def es_7dl_tournament_summary():
        try:
            state = getattr(store, "alt_tournament_state", None)
            first = getattr(store, "alt_day2_gamblers_1_tour", None)
            if not state or not first or not renpy.showing("alt_tournament_bg", layer="underlay"):
                return u""
            def name(g):
                return ES_7DL_GAMBLERS.get(getattr(g, "take", None), getattr(g, "take", u"?"))
            def rounds(players, title):
                out = []
                for i in __builtin__.range(0, len(players) - 1, 2):
                    a, b = players[i], players[i + 1]
                    line = u"{0} against {1}".format(name(a), name(b))
                    won = [p for p in (a, b) if getattr(p, "winner", False)]
                    if won:
                        line += u", {0} won".format(name(won[0]))
                    out.append(line)
                return title + u": " + u"; ".join(out) + u"."
            parts = [u"Tournament table.", rounds(first[0:8], u"First round")]
            semi = getattr(store, "alt_day2_gamblers_semifinal", None)
            if semi and state not in ("1_round_start", "1_round_end"):
                parts.append(rounds(semi[0:4], u"Semifinal"))
            final = getattr(store, "alt_day2_gamblers_final", None)
            if final and state in ("final_start", "final_end"):
                parts.append(rounds(final[0:2], u"Final"))
            return u" ".join(parts)
        except Exception:
            es_log_exc("es_7dl_tournament_summary")
            return u""

    es_7dl_table_seen = [None]

    def es_7dl_table_check():
        try:
            if getattr(store, "alt_tournament_state", None) is None:
                return
            key = None
            if renpy.showing("alt_tournament_bg", layer="underlay"):
                key = store.alt_tournament_state
            if key != es_7dl_table_seen[0]:
                es_7dl_table_seen[0] = key
                if key is not None:
                    es.announce(u"The tournament table is on screen. Press D to hear who plays whom.")
        except Exception:
            es_log_exc("es_7dl_table_check")

    config.start_interact_callbacks.append(es_7dl_table_check)

    # ------------------------------------------------------------------
    # Dialogue reading. Patched in at the point where Ren'Py shows a line,
    # so ADV, NVL and menu captions are all covered.
    # ------------------------------------------------------------------

    es_orig_display_say = es_original(renpy.character.display_say)

    # The map's "nothing here" lines are written in Russian in every language.
    ES_UNTRANSLATED = {
        u"Тут ничего нет": u"There's nothing here.",
        u"Мне нечего тут делать": u"I have nothing to do here.",
        u"Пойду-ка я лучше еще куда-нибудь": u"I'd better go somewhere else.",
    }

    def es_line_text(who, what):
        try:
            what = renpy.substitutions.substitute(what)[0]
        except Exception:
            pass
        what = es.clean(what)
        if not what:
            return u""
        if store._preferences.language is not None:
            what = ES_UNTRANSLATED.get(what, what)
        if not re.search(r"\w", what, re.UNICODE):
            # A line of only dots or dashes is a wordless pause; say so,
            # since screen readers often skip punctuation.
            what = u"ellipsis"
        who = es.clean(who) if isinstance(who, __builtin__.basestring) else u""
        if who and persistent.es_a11y_names:
            return u"{0}: {1}".format(who, what)
        return what

    def es_display_say(who, what, *args, **kwargs):
        try:
            if not config.skipping:
                text = es_line_text(who, what)
                if text:
                    es.line(text)
        except Exception:
            es_log_exc("es_display_say")
        return es_orig_display_say(who, what, *args, **kwargs)

    renpy.character.display_say = es_proxy(es_display_say, es_orig_display_say)

    # Footnotes ("Sovyonok means Owlet") and other notifications.
    es_orig_notify = es_original(config.notify)

    def es_notify(message, *args, **kwargs):
        try:
            text = es.clean(message)
            now = time.time()
            if text and not config.skipping and persistent.es_a11y_notes and (text, now) != es.last_notify:
                es.last_notify = (text, now)
                es.announce(u"Note: " + text)
        except Exception:
            es_log_exc("es_notify")
        return es_orig_notify(message, *args, **kwargs)

    config.notify = es_proxy(es_notify, es_orig_notify)

    # ------------------------------------------------------------------
    # Story hotkeys.
    # ------------------------------------------------------------------

    def es_repeat():
        if es.last_line:
            es.ui(es.last_line)
        else:
            es.ui(u"Nothing to repeat yet.")

    def es_review(delta):
        if not es.history:
            es.ui(u"No history yet.")
            return
        idx = es.review_index
        if idx < 0:
            idx = len(es.history) - 1
        idx = __builtin__.max(0, __builtin__.min(len(es.history) - 1, idx + delta))
        es.review_index = idx
        prefix = u""
        if delta < 0 and idx == 0:
            prefix = u"Oldest line. "
        elif delta > 0 and idx == len(es.history) - 1:
            prefix = u"Latest line. "
        es.ui(prefix + es.history[idx])

    def es_review_edge(last):
        if not es.history:
            es.ui(u"No history yet.")
            return
        es.review_index = len(es.history) - 1 if last else 0
        es.ui(es.history[es.review_index])

    def es_status():
        es.ui(u"Accessibility mod. Speech through {0}. Press F1 in the story for the key list.".format(
            es.prism.name if es.prism.available else u"Ren'Py text to speech"))

    ES_STORY_HELP = (
        u"Story keys. Enter or Space: next line. "
        u"Up and Down arrows: review earlier lines; Home and End: oldest and newest. "
        u"R: repeat the last line. D: describe the scene and who is in view. "
        u"W: who is in view. L: open the text log. "
        u"Tab: toggle skipping. Page Up: roll back. Escape: game menu. "
        u"F1: this help."
    )

    def es_help_story():
        es.ui(ES_STORY_HELP)

    def es_who():
        es_rebuild_present()
        es.ui(es_who_is_here())

    # ------------------------------------------------------------------
    # Keymap changes. Ren'Py's own self-voicing would talk over Prism.
    # ------------------------------------------------------------------

    def _es_remove_keys(binding, keys):
        config.keymap[binding] = [k for k in config.keymap.get(binding, []) if k not in keys]


init 1 python:
    for _es_name, _es_default in (
            ("es_a11y_scenes", True),
            ("es_a11y_characters", True),
            ("es_a11y_expressions", False),
            ("es_a11y_names", True),
            ("es_a11y_notes", True),
            ):
        if getattr(persistent, _es_name) is None:
            setattr(persistent, _es_name, _es_default)


init 999 python:
    # The game replaces config.keymap wholesale at init -1600, so these run
    # after it. Bindings the game left out fall back to Ren'Py's defaults:
    # A opened Ren'Py's own accessibility menu and Alt+Shift+V its debug
    # voice, neither of which the mod can read, and Shift+G the renderer
    # menu. All of them are switched off, along with Ren'Py's self-voicing,
    # which would talk over Prism through SAPI. H (hide the text window)
    # goes too: hidden, the game ignores the arrow keys and seems stuck.
    for _es_binding in ("hide_windows", "self_voicing", "clipboard_voicing", "debug_voicing",
            "accessibility", "choose_renderer", "progress_screen", "director",
            "performance", "image_load_log", "memory_profile", "profile_once",
            "full_inspector"):
        config.keymap[_es_binding] = []
    _es_remove_keys("help", ["K_F1", "meta_shift_/"])

    def es_sanitize_preferences():
        # An earlier mod left non-numeric volumes in some setups, which
        # crashes the preferences sliders.
        try:
            defaults = {"music": 0.65, "sfx": 1.0, "voice": 0.75}
            for mixer, default in defaults.items():
                value = _preferences.volumes.get(mixer, default)
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    es_log("Repaired volume for {0}: {1!r}".format(mixer, value))
                    _preferences.volumes[mixer] = default
            saved = persistent.on_save_timeofday
            if saved:
                for slot, entry in __builtin__.list(saved.items()):
                    try:
                        if __builtin__.any(not isinstance(v, (int, float)) for v in entry[3:6]):
                            del saved[slot]
                    except Exception:
                        del saved[slot]
            for field, default in (("text_cps", 0), ("afm_time", 15)):
                if not isinstance(getattr(_preferences, field), (int, float)):
                    setattr(_preferences, field, default)
            _preferences.self_voicing = False
        except Exception:
            es_log_exc("es_sanitize_preferences")

    es_sanitize_preferences()

    def es_after_load():
        es.just_loaded = True
        es_sanitize_preferences()

    config.after_load_callbacks.append(es_after_load)

    # The day title card is drawn by new_chapter() without a show statement.
    if hasattr(store, "new_chapter"):
        es_orig_new_chapter = store.new_chapter

        def es_new_chapter(day_number, chapter_name="", *args, **kwargs):
            try:
                if day_number in (-1, 0) or getattr(store, "backdrop", None) in ("prologue", "epilogue"):
                    title = es.clean(chapter_name)
                else:
                    title = u"Day {0}.".format(day_number)
                if title:
                    es.present = {}
                    es.announce(title)
            except Exception:
                es_log_exc("es_new_chapter")
            return es_orig_new_chapter(day_number, chapter_name, *args, **kwargs)

        store.new_chapter = es_new_chapter

    # 7 Days of Summer draws its own title cards: alt_chapter() for days of
    # the main story and dlc_chapter() for chapters of its bonus story.
    def es_wrap_7dl_chapter(fname, word):
        orig = getattr(store, fname, None)
        if orig is None or getattr(orig, "_es_original", None) is not None:
            return
        def wrapper(number, chapter_name=u"", *args, **kwargs):
            try:
                title = u"{0} {1}.".format(word, number)
                name = es.clean(chapter_name)
                if name:
                    title += u" " + name
                es.present = {}
                es.announce(title)
            except Exception:
                es_log_exc(fname)
            return orig(number, chapter_name, *args, **kwargs)
        wrapper._es_original = orig
        setattr(store, fname, wrapper)

    es_wrap_7dl_chapter("alt_chapter", u"Day")
    es_wrap_7dl_chapter("dlc_chapter", u"Chapter")

    # Ending achievements are shown as images on the overlay layer.
    ES_ENDING_NAMES = {
        "main_good": "me_good", "main_bad": "me_bad", "sl_good": "sl_good",
        "sl_bad": "sl_bad", "dv_good": "dv_good", "dv_bad": "dv_bad",
        "un_good": "un_good", "un_bad": "un_bad", "us_good": "us_good",
        "us_bad": "us_bad", "mi": "miku", "uv_unknown_fucken_shit": "yulya",
        "uv_city": "all_together",
    }

    if hasattr(store, "show_achievement"):
        es_orig_show_achievement = store.show_achievement

        def es_show_achievement(img, *args, **kwargs):
            try:
                key = ES_ENDING_NAMES.get(img)
                if key:
                    es.announce(u"Ending reached: {0}.".format(es_tr(key, img)))
            except Exception:
                es_log_exc("es_show_achievement")
            return es_orig_show_achievement(img, *args, **kwargs)

        store.show_achievement = es_show_achievement

    es_log("Core hooks installed.")


# ----------------------------------------------------------------------
# Update check. Once per game start, asks GitHub for the latest release
# and says so if it's newer than ES_VERSION. Reads the release manifest
# the installer itself uses (a plain redirect, no API token or rate
# limit), through Windows' own curl.exe in the background, polled from a
# periodic callback. The notice waits for the main menu and a moment of
# silence, so it neither cuts off the start-up speech nor gets cut off by
# it. Nothing is sent except the request itself, and a failed check is
# only logged.
# ----------------------------------------------------------------------

init 1000 python:
    ES_UPDATE_URL = "https://github.com/shaysters/everlasting-summer-access/releases/latest/download/loadstone-release.json"
    ES_UPDATE_QUIET = 2.0

    es_update = {"proc": None, "latest": None, "done": False}
    es_last_speech = [time.time()]

    def es_track_speech():
        # Note when anything is spoken, so the update notice can wait for a pause.
        orig = es.speak
        def speak(text, interrupt=True):
            es_last_speech[0] = time.time()
            return orig(text, interrupt)
        es.speak = speak

    es_track_speech()

    def es_version_tuple(s):
        try:
            return tuple(int(p) for p in s.split("."))
        except Exception:
            return None

    def es_update_tick():
        u = es_update
        if u["done"]:
            return
        try:
            if u["latest"]:
                if es_detect()[0][0] == "main_menu" and time.time() - es_last_speech[0] >= ES_UPDATE_QUIET:
                    u["done"] = True
                    text = u"Everlasting Summer Access version {0} is available. Run the installer to update.".format(u["latest"])
                    es_log("Update announced.")
                    # R repeats it until the story starts.
                    if not es.last_line:
                        es.last_line = text
                    es.speak(text, False)
                return
            if u["proc"] is None:
                import subprocess
                curl = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "curl.exe")
                if not os.path.exists(curl):
                    curl = "curl"
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # keep the console hidden
                u["proc"] = subprocess.Popen(
                    [curl, "-s", "-L", "--max-time", "15", ES_UPDATE_URL],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
                return
            if u["proc"].poll() is None:
                return
            out = u["proc"].stdout.read()
            m = re.search(r'"version"\s*:\s*"v?([0-9.]+)"', out or "")
            if not m:
                u["done"] = True
                es_log("Update check skipped (exit code {0}).".format(u["proc"].returncode))
                return
            latest = m.group(1)
            es_log("Update check: installed {0}, latest {1}".format(ES_VERSION, latest))
            lv, iv = es_version_tuple(latest), es_version_tuple(ES_VERSION)
            if lv and iv and lv > iv:
                u["latest"] = latest
            else:
                u["done"] = True
        except Exception:
            u["done"] = True
            es_log_exc("update check")

    config.periodic_callbacks.append(es_update_tick)
