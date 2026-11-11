# Everlasting Summer Accessibility Mod - screen navigation
#
# One screen, es_a11y_global, is kept on top in every context (story, game
# menu, main menu, splash screens). It works out which game screen is open
# and gives it a keyboard list: Up/Down move, Left/Right change values,
# Enter activates, Escape goes back. The game's own screens are left as
# they are; their actions are reused, so everything behaves as if clicked.

init -90 python:

    class ESItem(__builtin__.object):
        """One entry in a keyboard list.

        label   text, or a function returning text
        action  Ren'Py action run on Enter, or None for read-only entries
        adjust  function(delta) run on Left/Right
        delete  action run on the Delete key
        after   function run after the action, for spoken feedback
        """
        def __init__(self, label, action=None, adjust=None, delete=None, after=None):
            self.label = label
            self.action = action
            self.adjust = adjust
            self.delete = delete
            self.after = after

        def text(self):
            if callable(self.label):
                return self.label()
            return self.label

    class ESMode(__builtin__.object):
        def __init__(self, name, identity=None, items=None, intro=u"", start=0, escape=None, story=False):
            self.name = name
            self.identity = identity
            self.items = items or []
            self.intro = intro
            self.start = start
            self.escape = escape
            self.story = story

        @property
        def nav(self):
            return bool(self.items)

    def es_screen(name):
        try:
            return renpy.get_screen(name)
        except Exception:
            return None

    def es_scope(screen, key, default=None):
        try:
            return screen.scope.get(key, default)
        except Exception:
            return default

    def es_screen_parts(screen):
        # Reads a displayed screen as it is drawn: plain text, and buttons
        # with their own actions. Used for screens of other mods whose
        # buttons depend on their internal state, so nothing of theirs has
        # to be copied. Returns ("text", str) and ("button", str, action).
        out = []
        seen = __builtin__.set()

        def text_of(d):
            parts = []
            def walk(x):
                if isinstance(x, renpy.text.text.Text):
                    parts.append(u"".join(t for t in x.text if isinstance(t, __builtin__.basestring)))
                    return
                for c in x.visit() or []:
                    if c is not None:
                        walk(c)
            walk(d)
            return es.clean(u" ".join(parts))

        def walk(d):
            if d is None or id(d) in seen:
                return
            seen.add(id(d))
            if isinstance(d, renpy.display.behavior.Button):
                out.append(("button", text_of(d), d.action))
                return
            if isinstance(d, renpy.text.text.Text):
                t = text_of(d)
                if t:
                    out.append(("text", t))
                return
            for c in d.visit() or []:
                walk(c)

        try:
            walk(getattr(screen, "child", None))
        except Exception:
            es_log_exc("es_screen_parts")
        return out

    # Names for picture-only buttons, worked out from what the button does.
    ES_ACTION_FUNCTION_LABELS = {
        "cur_page_dec": u"Previous page", "cur_page_inc": u"Next page",
        "cur_char_idx_dec": u"Previous character", "cur_char_idx_inc": u"Next character",
        "reset_vars": u"Back", "previous": u"Previous track", "next": u"Next track",
        "stop": u"Stop the music and close",
    }
    ES_ACTION_JUMP_LABELS = {
        "main_menu_7dl": u"Back to the 7 Days of Summer menu",
        "alt_stories_start": u"Back to Stories",
    }

    def es_flat_actions(action):
        out = []
        if isinstance(action, (__builtin__.list, tuple)):
            for a in action:
                out.extend(es_flat_actions(a))
        elif action is not None:
            out.append(action)
        return out

    def es_action_label(action):
        acts = es_flat_actions(action)
        kinds = [type(a).__name__ for a in acts]
        for a in acts:
            if type(a).__name__ == "Jump":
                target = getattr(a, "label", None)
                if target in ES_ACTION_JUMP_LABELS:
                    return ES_ACTION_JUMP_LABELS[target]
        for a, kind in __builtin__.zip(acts, kinds):
            if kind == "Function":
                fn = getattr(getattr(a, "callable", None), "__name__", "")
            else:
                fn = getattr(a, "__name__", "")
            if fn in ES_ACTION_FUNCTION_LABELS:
                return ES_ACTION_FUNCTION_LABELS[fn]
            if kind == "PauseAudio":
                return u"Play or pause"
            if "Shuffle" in kind:
                return u"Shuffle on or off"
            if "Loop" in kind or "SingleTrack" in kind or kind == "If":
                return u"Repeat mode"
            if kind.endswith("Stop") and "MusicRoom" in kind:
                return u"Stop the music and close"
        # A button that only closes something.
        if acts and __builtin__.all(k in ("Hide", "With") for k in kinds):
            return u"Close"
        return u""

    # Fixed interface words of 7 Days of Summer, in English.
    ES_7DL_UI_WORDS = [
        (u"^ПРОСЛУШАНО: (.*)$", u"Listened to: \\1"),
        (u"^СТРАНИЦА (\\d+)/(\\d+)$", u"Page \\1 of \\2"),
        (u"^Открыто концовок: (.*)$", u"Endings unlocked: \\1"),
        (u"^Прогресс прохождения мода: (.*)$", u"Mod completion: \\1"),
        (u"^День (\\d+)$", u"Day \\1"),
        (u"^Часть (\\d+)$", u"Part \\1"),
        (u"^Пролог$", u"Prologue"), (u"^Коммон-рут$", u"Common route"),
        (u"^Семён$", u"Semyon"), (u"^Ульяна$", u"Ulyana"), (u"^Ольга$", u"Olga"),
        (u"^Лена$", u"Lena"), (u"^Славя$", u"Slavya"), (u"^Алиса$", u"Alisa"),
        (u"^Мику$", u"Miku"), (u"^\\?+$", u"Locked"),
    ]

    def es_7dl_words(text):
        for pattern, english in ES_7DL_UI_WORDS:
            if re.match(pattern, text):
                return re.sub(pattern, english, text)
        return text

    def es_scraped_items(screen, labels=None, skip_empty=True):
        # labels maps on-screen text (or a button's position among the
        # buttons, for picture buttons) to an English label. Runs of locked
        # entries are read as one.
        labels = labels or {}
        items = []
        n = 0
        locked = [0]

        def flush():
            if locked[0] == 1:
                items.append(ESItem(u"Locked"))
            elif locked[0] > 1:
                items.append(ESItem(u"{0} locked entries".format(locked[0])))
            locked[0] = 0

        for part in es_screen_parts(screen):
            if part[0] == "text":
                label = labels.get(part[1]) or es_7dl_words(part[1])
                if label == u"Locked":
                    locked[0] += 1
                    continue
                flush()
                items.append(ESItem(label))
                continue
            n += 1
            label = labels.get(part[1]) or labels.get(n) or es_7dl_words(part[1]) or es_action_label(part[2])
            if not label and skip_empty:
                continue
            if label == u"Locked":
                locked[0] += 1
                continue
            flush()
            if part[2] is None:
                items.append(ESItem(label))
            else:
                items.append(ESItem(label, part[2]))
        flush()
        return items

    def es_onoff(value):
        return u"on" if value else u"off"

    def es_checked(label, value):
        return u"{0}: {1}".format(label, u"selected" if value else u"not selected")

    # ------------------------------------------------------------------
    # Main menu and game menu.
    # ------------------------------------------------------------------

    def es_items_main_menu(screen):
        items = [
            ESItem(u"New game", [Function(translate), Start()]),
            ESItem(u"Load game", [Function(translate), ShowMenu("load")]),
            ESItem(u"Settings", [Function(translate), ShowMenu("preferences")]),
            ESItem(u"Gallery", [Function(collect_all), ShowMenu("gallery")]),
        ]
        try:
            if True in persistent.endings.values():
                items.append(ESItem(u"Endings", ShowMenu("history")))
        except Exception:
            pass
        items += [
            ESItem(u"Information", ShowMenu("help")),
            ESItem(u"Soviet Games website", OpenURL("http://sovietgames.su")),
            ESItem(u"Quit", ShowMenu("quit")),
        ]
        return ESMode("main_menu", screen, items, u"Everlasting Summer. Main menu.")

    def es_items_game_menu(screen):
        items = [
            ESItem(u"Return to the story", Return()),
            ESItem(u"Save game", ShowMenu("save")),
            ESItem(u"Load game", ShowMenu("load")),
            ESItem(u"Settings", [ShowMenu("preferences"), Hide("game_menu_selector")]),
            ESItem(u"Main menu", MainMenu()),
            ESItem(u"Quit", ShowMenu("quit")),
        ]
        return ESMode("game_menu", screen, items, u"Game menu.", escape=Return())

    # ------------------------------------------------------------------
    # Save and load.
    # ------------------------------------------------------------------

    ES_PAGES = ["auto"] + [__builtin__.str(i) for i in __builtin__.range(1, 10)]

    def es_page_name(page=None):
        if page is None:
            page = FileCurrentPage()
        if page == "auto":
            return u"Autosaves"
        if page == "quick":
            return u"Quick saves"
        return u"Page {0}".format(page)

    def es_slot_label(i):
        when = FileTime(i, format=u"%d %B %Y, %H:%M", empty=u"")
        if not when:
            return u"Slot {0}: empty".format(i)
        name = es.clean(FileSaveName(i))
        if name:
            return u"Slot {0}: {1}, saved {2}".format(i, name, when)
        return u"Slot {0}: saved {1}".format(i, when)

    def es_change_page(delta):
        page = FileCurrentPage()
        try:
            idx = ES_PAGES.index(page)
        except ValueError:
            idx = 1
        idx = __builtin__.max(0, __builtin__.min(len(ES_PAGES) - 1, idx + delta))
        renpy.run([FilePage(ES_PAGES[idx]), SetVariable("selected_slot", False)])
        es.ui(es_page_name(ES_PAGES[idx]) + u". " + es_slot_label(1))
        es.nav_index[("save_load")] = 1

    def es_items_file(screen, saving):
        items = [ESItem(lambda: u"{0}. Left and right arrows change page.".format(es_page_name()),
            adjust=es_change_page)]
        for i in __builtin__.range(1, 13):
            if saving:
                action = [SetVariable("selected_slot", i), FunctionCallback(on_save_callback, i), FileSave(i)]
            else:
                action = [SetVariable("selected_slot", i), FunctionCallback(on_load_callback, i), FileLoad(i)]
            items.append(ESItem(renpy.curry(es_slot_label)(i), action, delete=FileDelete(i),
                after=renpy.curry(es_file_after)(i, saving)))
        if saving:
            items.append(ESItem(u"Switch to load", ShowMenu("load")))
        else:
            items.append(ESItem(u"Switch to save", ShowMenu("save")))
        items.append(ESItem(u"Settings", ShowMenu("preferences")))
        items.append(ESItem(u"Back", Return()))
        intro = u"Save game." if saving else u"Load game."
        intro += u" Enter {0} the selected slot, Delete erases it.".format(u"saves to" if saving else u"loads")
        return ESMode("save_load", screen, items, intro + u" " + es_page_name() + u".", start=1, escape=Return())

    def es_file_after(i, saving):
        # Saving to an empty slot needs no confirmation, so say it worked.
        if saving and es_screen("yesno_prompt") is None:
            es.ui(u"Saved. " + es_slot_label(i))

    # ------------------------------------------------------------------
    # Settings.
    # ------------------------------------------------------------------

    def es_set_volume(mixer, delta):
        value = _preferences.volumes.get(mixer, 1.0)
        if not isinstance(value, (int, float)):
            value = 1.0
        value = __builtin__.max(0.0, __builtin__.min(1.0, __builtin__.round(value + delta, 2)))
        _preferences.set_volume(mixer, value)
        renpy.restart_interaction()
        es.ui(u"{0}%".format(int(__builtin__.round(value * 100))))
        if mixer == "sfx":
            renpy.play("sound/test.ogg", channel="sound")

    def es_volume_label(name, mixer):
        value = _preferences.volumes.get(mixer, 1.0)
        if not isinstance(value, (int, float)):
            value = 1.0
        return u"{0} volume: {1}%".format(name, int(__builtin__.round(value * 100)))

    ES_CPS_STEPS = [10, 20, 30, 40, 50, 60, 80, 100, 125, 150, 200, 0]

    def es_text_speed_label():
        cps = _preferences.text_cps
        if not cps:
            return u"Text speed: instant"
        return u"Text speed: {0} characters per second".format(cps)

    def es_text_speed(delta):
        cps = _preferences.text_cps or 0
        steps = ES_CPS_STEPS
        if cps in steps:
            idx = steps.index(cps)
        else:
            idx = len([s for s in steps[:-1] if s < cps])
        idx = __builtin__.max(0, __builtin__.min(len(steps) - 1, idx + delta))
        _preferences.text_cps = steps[idx]
        renpy.restart_interaction()
        es.ui(es_text_speed_label().split(u": ", 1)[1])

    def es_afm_on():
        return _preferences.afm_time != 0 and _preferences.afm_enable

    def es_afm_toggle(delta=0):
        if es_afm_on():
            renpy.run([Preference("auto-forward time", 0), Preference("auto-forward after click", "disable"),
                Preference("auto-forward", "disable")])
        else:
            if not _preferences.afm_time:
                _preferences.afm_time = 15
            renpy.run([Preference("auto-forward after click", "enable"), Preference("auto-forward", "enable")])
        renpy.restart_interaction()
        es.ui(u"Auto-forward " + es_onoff(es_afm_on()))

    def es_afm_time(delta):
        value = __builtin__.max(1, __builtin__.min(40, int(_preferences.afm_time or 15) + delta))
        _preferences.afm_time = value
        renpy.restart_interaction()
        es.ui(u"{0}".format(value))

    def es_toggle_field(obj, field, labels=None):
        def toggle(delta=0):
            setattr(obj, field, not getattr(obj, field))
            renpy.restart_interaction()
            es.ui(es_onoff(getattr(obj, field)))
        return toggle

    def es_toggle_fullscreen(delta=0):
        if _preferences.fullscreen:
            renpy.run(Preference("display", "window"))
            es.ui(u"Windowed")
        else:
            renpy.run(Preference("display", "fullscreen"))
            es.ui(u"Fullscreen")

    def es_toggle_skip(delta=0):
        _preferences.skip_unseen = not _preferences.skip_unseen
        renpy.restart_interaction()
        es.ui(u"Skips all text" if _preferences.skip_unseen else u"Skips seen text only")

    def es_toggle_font(delta=0):
        persistent.font_size = "large" if persistent.font_size == "small" else "small"
        renpy.restart_interaction()
        es.ui(u"Big" if persistent.font_size == "large" else u"Normal")

    def es_items_preferences(screen):
        def flag(label, field):
            return ESItem(lambda: u"{0}: {1}".format(label, es_onoff(getattr(persistent, field))),
                es_toggle_field(persistent, field), adjust=es_toggle_field(persistent, field))
        items = [
            ESItem(lambda: u"Display: " + (u"fullscreen" if _preferences.fullscreen else u"windowed"),
                Function(es_toggle_fullscreen), adjust=es_toggle_fullscreen),
            ESItem(lambda: u"Skip: " + (u"all text" if _preferences.skip_unseen else u"seen text only"),
                Function(es_toggle_skip), adjust=es_toggle_skip),
            ESItem(lambda: es_volume_label(u"Music", "music"), Play("sound", "sound/test.ogg"),
                adjust=lambda d: es_set_volume("music", d * 0.05)),
            ESItem(lambda: es_volume_label(u"Sound", "sfx"), Play("sound", "sound/test.ogg"),
                adjust=lambda d: es_set_volume("sfx", d * 0.05)),
            ESItem(lambda: es_volume_label(u"Ambience", "voice"), Play("sound", "sound/test.ogg"),
                adjust=lambda d: es_set_volume("voice", d * 0.05)),
            ESItem(es_text_speed_label, None, adjust=es_text_speed),
            ESItem(lambda: u"Auto-forward: " + es_onoff(es_afm_on()), Function(es_afm_toggle), adjust=es_afm_toggle),
            ESItem(lambda: u"Auto-forward delay: {0}".format(_preferences.afm_time), None, adjust=es_afm_time),
            ESItem(lambda: u"Font: " + (u"big" if persistent.font_size == "large" else u"normal"),
                Function(es_toggle_font), adjust=es_toggle_font),
            ESItem(u"Language", ShowMenu("language_menu")),
            ESItem(lambda: u"Show achievements: " + es_onoff(persistent.show_achievements),
                es_toggle_field(persistent, "show_achievements"), adjust=es_toggle_field(persistent, "show_achievements")),
            flag(u"Accessibility: describe scenes", "es_a11y_scenes"),
            flag(u"Accessibility: announce characters arriving and leaving", "es_a11y_characters"),
            flag(u"Accessibility: announce facial expressions", "es_a11y_expressions"),
            flag(u"Accessibility: read speaker names", "es_a11y_names"),
            flag(u"Accessibility: read footnotes", "es_a11y_notes"),
            ESItem(u"Mods and user scenarios", ShowMenu("mods")),
            ESItem(u"Image filters", ShowMenu("filters")),
            ESItem(u"Save game", ShowMenu("save")),
            ESItem(u"Load game", ShowMenu("load")),
            ESItem(u"Back", Return()),
        ]
        return ESMode("preferences", screen, items,
            u"Settings. Left and right arrows change values, Enter toggles.", escape=Return())

    # ------------------------------------------------------------------
    # Language, mods, filters, endings, help.
    # ------------------------------------------------------------------

    ES_LANGUAGES = [
        (None, u"Russian", u"Бесконечное Лето"),
        ("english", u"English", u"Everlasting Summer"),
        ("spanish", u"Spanish", u"Eterno Verano"),
        ("italian", u"Italian", u"Eterna Estate"),
        ("chinese", u"Chinese", u"Everlasting Summer"),
        ("french", u"French", u"Everlasting Summer"),
        ("portuguese", u"Portuguese", u"Everlasting Summer"),
        ("turkish", u"Turkish", u"Everlasting Summer"),
    ]

    def es_items_language_menu(screen):
        items = []
        start = 0
        for i, (code, name, title) in enumerate(ES_LANGUAGES):
            current = _preferences.language == code
            if current:
                start = i
            action = [SetField(config, "window_title", title), SetField(persistent, "show_hentai_ach", False),
                Language(code), Function(reload_names), Function(stop_music), Function(renpy.utter_restart)]
            items.append(ESItem(name + (u", current" if current else u"") + u". The game restarts.", action))
        items.append(ESItem(u"Cancel", Hide("language_menu")))
        return ESMode("language_menu", screen, items, u"Language.", start=start, escape=Hide("language_menu"))

    def es_items_mods(screen):
        items = []
        try:
            for lbl, name in __builtin__.sorted(store.mods.iteritems()):
                items.append(ESItem(es.clean(name), [SetField(persistent, "jump_to", lbl), Start()]))
        except Exception:
            es_log_exc("es_items_mods")
        if not items:
            items.append(ESItem(u"No mods installed."))
        items.append(ESItem(u"Back", ShowMenu("preferences")))
        return ESMode("mods", screen, items, u"Mods and user scenarios.", escape=ShowMenu("preferences"))

    def es_filter_label(i):
        try:
            item = persistent.filters[i]
            return u"{0}: {1}".format(es.clean(store.filters[item["id"]]), es_onoff(item["is_active"]))
        except Exception:
            return u"Filter"

    def es_items_filters(screen):
        items = []
        try:
            for i, item in enumerate(persistent.filters):
                items.append(ESItem(renpy.curry(es_filter_label)(i), [Function(apply_filter, i), ShowMenu("filters")],
                    after=renpy.curry(lambda n: es.ui(es_filter_label(n)))(i)))
        except Exception:
            es_log_exc("es_items_filters")
        if not items:
            items.append(ESItem(u"No filters installed."))
        items.append(ESItem(u"Apply and restart the game", [Function(stop_music), Function(renpy.utter_restart)]))
        items.append(ESItem(u"Back", ShowMenu("preferences")))
        return ESMode("filters", screen, items, u"Image filters.", escape=ShowMenu("preferences"))

    ES_ENDINGS = [
        ("me_good", "main_good", "epilogue_main"), ("me_bad", "main_bad", "main_bad_ending"),
        ("sl_good", "sl_good", "epilogue_sl"), ("sl_bad", "sl_bad", "epilogue_sl"),
        ("dv_good", "dv_good", "epilogue_dv"), ("dv_bad", "dv_bad", "epilogue_dv"),
        ("un_good", "un_good", "epilogue_un_good"), ("un_bad", "un_bad", "epilogue_un_bad"),
        ("us_good", "us_good", "epilogue_us"), ("us_bad", "us_bad", "epilogue_us"),
        ("miku", "mi", "epilogue_mi"), ("yulya", "uv_unknown_fucken_shit", "epilogue_uv_ulya"),
        ("all_together", "uv_city", "epilogue_uv_city"),
    ]

    def es_items_history(screen):
        items = []
        for key, ach, lbl in ES_ENDINGS:
            if persistent.endings.get(ach):
                items.append(ESItem(u"{0}. Enter replays this ending.".format(es_tr(key, key)),
                    [SetField(persistent, "jump_to", lbl), SetField(persistent, "replay", ach), Start()]))
            else:
                items.append(ESItem(u"Locked ending."))
        items.append(ESItem(u"Back", Return()))
        found = len([1 for k, a, l in ES_ENDINGS if persistent.endings.get(a)])
        return ESMode("history", screen, items,
            u"Endings. {0} of {1} found.".format(found, len(ES_ENDINGS)), escape=Return())

    def es_items_help(screen):
        items = [
            ESItem(es_tr("info_text", u"Official VKontakte community, Russian only.")),
            ESItem(es_tr("android_text", u"Android version on Google Play.")),
            ESItem(es_tr("ios_text", u"iOS version on the App Store.")),
            ESItem(u"Back", Return()),
        ]
        return ESMode("help", screen, items, u"Information.", escape=Return())

    # ------------------------------------------------------------------
    # Gallery, sprite viewer and music room.
    # ------------------------------------------------------------------

    def es_gallery_list():
        return gallery_cg if gallery_mode == "cg" else gallery_bg

    def es_gallery_label(name, unlocked, n, total):
        if not unlocked:
            return u"{0} of {1}: locked.".format(n, total)
        key = (u"cg " if gallery_mode == "cg" else u"bg ") + name
        text = ES_DESCRIPTIONS.get(key) or es_scene_label(key)
        return u"{0} of {1}: {2}".format(n, total, text)

    def es_gallery_view(name):
        key = (u"cg " if gallery_mode == "cg" else u"bg ") + name
        text = ES_DESCRIPTIONS.get(key) or es_scene_label(key)
        es.ui(u"Showing picture. " + text + u" Press Enter or Escape to return.")

    def es_items_gallery(screen):
        items = []
        names = es_gallery_list()
        total = len(names)
        unlocked_count = 0
        for n, name in enumerate(names):
            action = g.Action(name)
            unlocked = action is not None
            if unlocked:
                unlocked_count += 1
                action = [Function(es_gallery_view, name, _update_screens=False), action]
            items.append(ESItem(es_gallery_label(name, unlocked, n + 1, total), action))
        if gallery_mode == "cg":
            title = u"Gallery, illustrations"
            items += [
                ESItem(u"Switch to backgrounds", [SetVariable("gallery_mode", "bg"), SetVariable("page", 0), ShowMenu("gallery")]),
                ESItem(u"Switch to sprites", [SetVariable("page", 0), ShowMenu("gallery_sp")]),
                ESItem(u"Switch to music", [SetVariable("page", 0), ShowMenu("music_room")]),
            ]
        else:
            title = u"Gallery, backgrounds"
            items += [
                ESItem(u"Switch to illustrations", [SetVariable("gallery_mode", "cg"), SetVariable("page", 0), ShowMenu("gallery")]),
                ESItem(u"Switch to sprites", [SetVariable("page", 0), ShowMenu("gallery_sp")]),
                ESItem(u"Switch to music", [SetVariable("page", 0), ShowMenu("music_room")]),
            ]
        items.append(ESItem(u"Back", Return()))
        intro = u"{0}. {1} of {2} unlocked.".format(title, unlocked_count, total)
        return ESMode("gallery_" + gallery_mode, screen, items, intro, escape=Return())

    def es_sprite_description():
        if not show_spr:
            return u"No sprite chosen."
        bits = [es_char_name(show_spr)]
        if show_spr_dress:
            bits.append(ES_OUTFITS.get(show_spr_dress, show_spr_dress))
        if show_spr_emo:
            bits.append(ES_EXPRESSIONS.get(show_spr_emo) or u"neutral expression")
        if show_spr_acc:
            bits.append(u"with " + ES_OUTFITS.get(show_spr_acc, show_spr_acc))
        return u"Showing: " + u", ".join(bits) + u"."

    def es_items_gallery_sp(screen):
        items = [ESItem(es_sprite_description)]
        items.append(ESItem(lambda: u"Character: " + (es_char_name(show_spr) if show_spr else u"none") + u". Enter to choose.",
            [ShowMenu("sprite_menu"), SetVariable("spr_menu_spr", True), SetVariable("spr_menu_dress", False),
             SetVariable("spr_menu_emo", False), SetVariable("show_spr", False), SetVariable("show_spr_dress", False),
             SetVariable("show_spr_emo", False), SetVariable("show_spr_acc", False), SetVariable("spr_menu_acc", False)]))
        if show_spr:
            items.append(ESItem(lambda: u"Outfit: " + (ES_OUTFITS.get(show_spr_dress, u"none") if show_spr_dress else u"none") + u". Enter to choose.",
                [ShowMenu("sprite_menu"), SetVariable("show_spr_emo", False), SetVariable("spr_menu_dress", True),
                 SetVariable("spr_menu_emo", False), SetVariable("show_spr_dress", False), SetVariable("show_spr_acc", False),
                 SetVariable("spr_menu_acc", False)]))
            if show_spr_dress or show_spr in ("pi", "sh", "cs", "uv"):
                items.append(ESItem(lambda: u"Expression: " + ((ES_EXPRESSIONS.get(show_spr_emo) or u"neutral") if show_spr_emo else u"none") + u". Enter to choose.",
                    [ShowMenu("sprite_menu"), SetVariable("spr_menu_emo", True), SetVariable("spr_menu_acc", False),
                     SetVariable("show_spr_emo", False), SetVariable("show_spr_acc", False)]))
                if show_spr_emo and show_spr in ("mt", "mz", "cs"):
                    items.append(ESItem(lambda: u"Accessory: " + (ES_OUTFITS.get(show_spr_acc, u"none") if show_spr_acc else u"none") + u". Enter to choose.",
                        [ShowMenu("sprite_menu"), SetVariable("spr_menu_acc", True), SetVariable("show_spr_acc", False)]))
        items += [
            ESItem(u"Switch to backgrounds", [SetVariable("gallery_mode", "bg"), SetVariable("page", 0), SetVariable("show_spr", False), ShowMenu("gallery")]),
            ESItem(u"Switch to music", [SetVariable("page", 0), SetVariable("show_spr", False), ShowMenu("music_room")]),
            ESItem(u"Back", [Return(), SetVariable("show_spr", False)]),
        ]
        return ESMode("gallery_sp", screen, items, u"Sprite viewer.", start=1,
            escape=[Return(), SetVariable("show_spr", False)])

    def es_sprite_option_name(value):
        if spr_menu_spr:
            return es_char_name(value)
        if spr_menu_emo:
            return ES_EXPRESSIONS.get(value) or u"neutral"
        return ES_OUTFITS.get(value, es_tr(value, value))

    def es_items_sprite_menu(screen):
        items = []
        for spr, value in es_scope(screen, "show_spr_menu", []) or []:
            if spr_menu_acc:
                var = "show_spr_acc"
            elif spr_menu_emo:
                var = "show_spr_emo"
            elif spr_menu_dress:
                var = "show_spr_dress"
            else:
                var = "show_spr"
            items.append(ESItem(es_sprite_option_name(value),
                [SetVariable(var, value), Hide("sprite_menu"), ShowMenu("gallery_sp")]))
        if spr_menu_acc:
            items.append(ESItem(u"No accessory", [SetVariable("show_spr_acc", False), Hide("sprite_menu"), ShowMenu("gallery_sp")]))
        if not items:
            items.append(ESItem(u"Nothing unlocked yet."))
        back = [Hide("sprite_menu"), ShowMenu("gallery_sp")]
        items.append(ESItem(u"Cancel", back))
        return ESMode("sprite_menu", screen, items, u"Choose.", escape=back)

    def es_items_music_room(screen):
        items = []
        for name, track in __builtin__.sorted(music_box.iteritems()):
            items.append(ESItem(name, mr.Play(track), after=renpy.curry(lambda n: es.ui(u"Playing " + n))(name)))
        items += [
            ESItem(u"Switch to sprites", [ShowMenu("gallery_sp"), SetVariable("page", 0)]),
            ESItem(u"Switch to illustrations", [SetVariable("gallery_mode", "cg"), ShowMenu("gallery"), SetVariable("page", 0)]),
            ESItem(u"Back", Return()),
        ]
        return ESMode("music_room", screen, items, u"Music room. Enter plays a track.", escape=Return())

    # ------------------------------------------------------------------
    # Prompts and one-off screens.
    # ------------------------------------------------------------------

    def es_items_yesno(screen):
        message = es.clean(es_scope(screen, "message", u""))
        yes = es_scope(screen, "yes_action")
        no = es_scope(screen, "no_action")
        items = [ESItem(u"Yes", yes), ESItem(u"No", no)]
        return ESMode("yesno", screen, items, message, escape=no)

    def es_items_quit(screen):
        items = [ESItem(u"Yes, quit", Quit(confirm=False)), ESItem(u"No", Return())]
        return ESMode("quit", screen, items, u"Do you really want to quit the game?", escape=Return())

    def es_items_license(screen):
        try:
            lic = store.translation_new["license"]
            text, yes, no = lic["text"], lic["yes"], lic["no"]
        except Exception:
            text, yes, no = u"License agreement.", u"Accept", u"Decline"
        items = [
            ESItem(es.clean(text)),
            ESItem(es.clean(yes), [Hide("license"), Return()]),
            ESItem(es.clean(no) + u" The game will close.", [Hide("license"), Quit(confirm=False)]),
        ]
        return ESMode("license", screen, items, u"License agreement.")

    def es_items_support(screen):
        items = [
            ESItem(es_tr("lmr", u"Support our new game!") + u" Open the Love, Money, Rock'n'Roll page.",
                [Hide("support"), OpenURL("https://sovietgames.su/love-money-rocknroll/"), Return()]),
            ESItem(lambda: es_tr("lmr_hide", u"Don't show again") + (u": selected" if persistent.lmr_hide else u""),
                SetField(persistent, "lmr_hide", True)),
            ESItem(es_tr("lmr_skip", u"Skip"), [Hide("support"), Return()]),
        ]
        return ESMode("support", screen, items, u"Advertisement.", start=2)

    def es_items_cardgame_results(screen):
        status = es_scope(screen, "result_status") or getattr(store, "result_status", None)
        result = {"win": u"You win!", "draw": u"It's a draw."}.get(status, u"You lose.")
        items = [ESItem(result + u" Continue.", Return("continue"))]
        return ESMode("cardgame_results", screen, items, u"Card game over.")

    def es_items_text_log(screen):
        items = []
        try:
            for h in store._history_list:
                text = es_line_text(h.who, h.what)
                if text:
                    items.append(ESItem(text))
        except Exception:
            es_log_exc("es_items_text_log")
        if not items:
            items.append(ESItem(u"The log is empty."))
        items.append(ESItem(u"Close the log", Return()))
        return ESMode("text_log", screen, items, u"Text log, newest at the bottom.",
            start=__builtin__.max(0, len(items) - 2), escape=Return())

    def es_items_gallery_image(screen):
        # The gallery's full screen view; Enter or Escape closes it.
        return ESMode("gallery_image", screen, [], u"")

    # ------------------------------------------------------------------
    # In-game modes: choices, the camp map, the card game, first run
    # language picker, and the story itself.
    # ------------------------------------------------------------------

    def es_choice_items(raw):
        items = []
        heading = []
        try:
            chosen_before = persistent.choices or []
        except Exception:
            chosen_before = []
        for entry in raw or []:
            try:
                caption, action = entry[0], entry[1]
            except Exception:
                continue
            original = caption
            try:
                # Choice captions are translated as they are drawn.
                caption = renpy.substitutions.substitute(caption)[0]
            except Exception:
                pass
            caption = es.clean(caption)
            if not caption:
                continue
            if action:
                label = caption
                if persistent.licensed and original in chosen_before:
                    label += u" (chosen before)"
                items.append(ESItem(label, action))
            else:
                heading.append(caption)
        return heading, items

    def es_items_choice(screen):
        heading, items = es_choice_items(es_scope(screen, "items"))
        intro = u" ".join(heading) or u"Choose."
        return ESMode("choice", screen, items, intro)

    ES_ZONE_NAMES = {
        "me_mt_house": u"Olga Dmitrievna's cabin, where you live",
        "estrade": u"Stage", "music_club": u"Music club", "square": u"Square",
        "dining_hall": u"Dining hall", "sport_area": u"Sports area",
        "beach": u"Beach", "boat_station": u"Boat dock", "clubs": u"Clubs building",
        "library": u"Library", "medic_house": u"Infirmary",
        "camp_entrance": u"Camp gates", "forest": u"Forest",
    }

    ES_ZONE_ORDER = ["me_mt_house", "square", "dining_hall", "music_club", "clubs",
        "library", "medic_house", "estrade", "sport_area", "beach", "boat_station",
        "camp_entrance", "forest"]

    def es_zone_label(name, data):
        label = ES_ZONE_NAMES.get(name, name.replace("_", " ").capitalize())
        chibi = data.get("chibi")
        if chibi is not None:
            for who, img in store.map_chibi.items():
                if img is chibi or img == chibi:
                    if who in ES_CHARACTER_TAGS:
                        label += u", {0} is here".format(es_char_name(who))
                    elif who == "?":
                        label += u", someone is here"
                    break
        if data.get("been_here"):
            label += u", visited"
        return label

    def es_items_map():
        items = []
        zones = getattr(store, "global_zones", {}) or {}
        names = [n for n in ES_ZONE_ORDER if n in zones] + __builtin__.sorted(n for n in zones if n not in ES_ZONE_ORDER)
        for name in names:
            data = zones[name]
            if data.get("available"):
                items.append(ESItem(es_zone_label(name, data), Function(store.map.zoneclick, name)))
        return ESMode("map", ("map", id(zones)), items, u"Camp map. Choose where to go.")

    # Card game ----------------------------------------------------------

    ES_SUITS = {"2ch": u"2ch", "ussr": u"USSR", "utan": u"Utan", "uvao": u"UVAO"}
    ES_VALUES = {1: u"Ace", 11: u"Jack", 12: u"Queen", 13: u"King"}

    def es_card_label(name):
        try:
            if name == name_of_none:
                return u"empty slot"
            value, suit = name
            return u"{0} of {1}".format(ES_VALUES.get(value, unicode(value)), ES_SUITS.get(suit, suit))
        except Exception:
            return u"card"

    def es_card_name(card):
        return es_card_label(getattr(card, "name", None))

    def es_card_visible(card):
        # Mirrors card_button(): the tutorial hides even the player's cards.
        state = getattr(card, "visible", None)
        return (state == "VISIBLE" and store.VISIBLE) or (state == "INVISIBLE" and store.INVISIBLE) \
            or card.name == name_of_none

    def es_card_game_active():
        try:
            if not getattr(store, "cards_my", None):
                return False
            state = store.cards_state
            # Player-interactive phases of the stock ES card game and the
            # 7DL tournament (same state names; rivals may be CardGameRivalUs,
            # CardGameRivalWiseUsual, CardGameRivalWiseLikeUS, etc.).
            if state in ("me_defend_1", "me_defend_2", "me_select_1", "me_select_2",
                         "rival_select", "results"):
                return True
            # After a match the state stays "win", "draw" or "fail" and the
            # cards are never cleared, so those states must not count, or the
            # card view would stay on through the rest of the story.
        except Exception:
            pass
        return False

    def es_hand_summary(cards, mine=True):
        names = []
        for i, card in enumerate(cards):
            if card.name == name_of_none:
                continue
            if es_card_visible(card):
                names.append(es_card_name(card))
            else:
                names.append(u"face down")
        counts = {}
        for card in cards:
            if card.name != name_of_none and es_card_visible(card):
                counts[card.name[0]] = counts.get(card.name[0], 0) + 1
        groups = []
        for value, count in __builtin__.sorted(counts.items(), key=lambda kv: -kv[1]):
            if count >= 2:
                word = {2: u"pair", 3: u"three", 4: u"four"}.get(count, u"set")
                groups.append(u"{0} of {1}s".format(word, ES_VALUES.get(value, unicode(value))))
        text = u", ".join(names)
        if groups:
            text += u". Sets: " + u", ".join(groups)
        return text

    def es_card_phase():
        state = store.cards_state
        mine = store.cards_my
        if state == "rival_select":
            return u"Your opponent is choosing a card. Pick which of your cards to offer."
        if state in ("me_defend_1", "me_defend_2"):
            target = None
            for i, c in enumerate(mine):
                if c.interesting:
                    target = u"card {0}, {1}".format(i + 1, es_card_name(c))
            text = u"Your opponent wants your {0}. ".format(target) if target else u""
            if state == "me_defend_1":
                return text + u"Defend by choosing two of your cards to swap, or end your turn to give it up. {0} swaps left.".format(store.changes_left)
            for c in mine:
                if c.dy:
                    return u"Swap your {0} with which card? Choosing it again cancels.".format(es_card_name(c))
            return u"Choose the second card to swap with."
        if state == "me_select_2":
            return u"Your turn: choose one of your opponent's cards to take."
        if state == "me_select_1":
            return u"Your turn: choose a card to give."
        if state == "results":
            return u"Results."
        return u""

    def es_items_cards():
        state = store.cards_state
        mine = store.cards_my
        rival_cards = store.cards_rival
        items = []
        if state == "results" and store.result_status in (None, "in_progress"):
            # Cards are being turned over; the result comes next.
            return ESMode("cards")
        if store.result_status not in (None, "in_progress"):
            result = {"win": u"You win!", "draw": u"It's a draw.", "fail": u"You lose."}.get(store.result_status, u"")
            items.append(ESItem(u"{0} Continue.".format(result), Return("ok")))
            items.append(ESItem(u"Your hand: " + es_hand_summary(mine)))
            items.append(ESItem(u"Opponent's hand: " + es_hand_summary(rival_cards, False)))
            return ESMode("cards", ("cards", state, store.result_status), items, u"Card game results.")
        if state in ("me_defend_1", "me_defend_2"):
            items.append(ESItem(u"End turn", Return("end_of_turn")))
        for i, card in enumerate(mine):
            if card.name == name_of_none:
                continue
            selectable = state in ("me_defend_1", "me_defend_2", "rival_select")
            selectable = selectable or (state == "me_select_1" and CARD_GAME_WITH_EXCHANGE)
            selectable = selectable or (state == "me_select_2" and i == store.my_card)
            label = u"Your card {0}: {1}".format(i + 1, es_card_name(card) if es_card_visible(card) else u"face down")
            if card.interesting and state in ("me_defend_1", "me_defend_2", "rival_select"):
                label += u", wanted by opponent"
            if card.dy:
                label += u", lifted"
            if state == "me_select_2" and i == store.my_card:
                label += u". Enter cancels"
            items.append(ESItem(label, Return(("my", i)) if selectable else None))
        if state == "me_select_2":
            for i, card in enumerate(rival_cards):
                if not getattr(card, "allow", False) or card.name == name_of_none:
                    continue
                shown = es_card_name(card) if es_card_visible(card) else u"face down"
                label = u"Opponent's card {0}: {1}".format(i + 1, shown)
                if card.interesting:
                    label += u", your last pick"
                items.append(ESItem(label, Return(("rival", i))))
        items.append(ESItem(lambda: u"Your hand: " + es_hand_summary(store.cards_my)))
        items.append(ESItem(lambda: u"Rounds left: {0}. Swaps left: {1}.".format(store.cycles_left, store.changes_left)))
        intro = es_card_phase()
        start = 0
        if state in ("me_defend_1", "me_defend_2"):
            start = 1
        elif state == "me_select_2":
            # Start on the first card that can be taken.
            for n, item in enumerate(items):
                if item.action is not None and isinstance(item.action, Return) and item.action.value[0] == "rival":
                    start = n
                    break
        return ESMode("cards", ("cards", state, store.cycles_left, store.changes_left), items, intro, start=start)

    def es_card_counts(cards):
        counts = {}
        for card in cards:
            if card.name != name_of_none and es_card_visible(card):
                counts[card.name] = counts.get(card.name, 0) + 1
        return counts

    def es_card_news():
        # Said before a card game announcement: who you are playing on the
        # first one, then which cards changed hands since the last one.
        news = []
        mine = store.cards_my
        counts = es_card_counts(mine)
        state = store.cards_state
        if getattr(es, "cards_game", None) != id(mine):
            es.cards_game = id(mine)
            es.cards_counts = counts
            es.cards_state = state
            es.cards_changes = store.changes_left
            try:
                news.append(u"Playing cards against {0}.".format(es.clean(store.rival.name)))
            except Exception:
                pass
            return u" ".join(news)
        old = es.cards_counts
        gained = [k for k in counts for n in __builtin__.range(counts[k] - old.get(k, 0))]
        lost = [k for k in old for n in __builtin__.range(old[k] - counts.get(k, 0))]
        if lost:
            news.append(u"You gave away {0}.".format(u", ".join(es_card_label(k) for k in lost)))
        if gained:
            news.append(u"You received {0}.".format(u", ".join(es_card_label(k) for k in gained)))
        if state == "me_select_2" and es.cards_state == "me_select_2" and not gained:
            news.append(u"Your opponent swapped two of their cards. Choose again.")
        if es.cards_state == "me_defend_2" and state == "me_defend_1":
            if store.changes_left == es.cards_changes:
                news.append(u"Swap cancelled.")
            else:
                news.append(u"Cards swapped.")
        elif es.cards_state == "me_defend_2" and state == "rival_select":
            news.append(u"Cards swapped.")
        es.cards_counts = counts
        es.cards_state = state
        es.cards_changes = store.changes_left
        return u" ".join(news)

    ES_CARD_HELP = (
        u"Card game. Each player holds six cards. Over three rounds you swap cards with your opponent. "
        u"When your opponent targets one of your cards you may swap two of your cards to hide it, or end your turn. "
        u"Then you take one card from your opponent; they may shuffle before you take it. "
        u"At the end, the player with more cards in pairs, threes or fours wins. "
        u"Use the arrow keys to read cards, Enter to choose."
    )

    # First run language picker, drawn with ui.imagebutton during the splash.

    def es_items_first_language():
        items = []
        for code, name, title in ES_LANGUAGES:
            items.append(ESItem(name, Return(code or "None")))
        return ESMode("first_language", ("first_language",), items,
            u"Everlasting Summer. Choose a language with the arrow keys and press Enter.", start=1)

    # ------------------------------------------------------------------
    # 7 Days of Summer (7DL / 7DS:LA) menus
    # ------------------------------------------------------------------

    def es_items_menu_7dl(screen):
        items = []
        pivo = getattr(persistent, "pivo_default_7dl", False)

        if not pivo:
            # Menu when 7DL is NOT the default main menu (starts the mod)
            items.append(ESItem(u"Start 7DS:LA", [
                Hide("menu_7dl", transition=Dissolve(0.2)),
                Hide("settings_7dl", transition=Dissolve(0.2)),
                Hide("contacts_7dl", transition=Dissolve(0.2)),
                Hide("media_7dl", transition=Dissolve(0.2)),
                Stop('music', fadeout=2),
                SetField(sdl_mus_engine, "is_active", False),
                Jump("start_7dl")
            ]))
            items.append(ESItem(u"Settings", Show("settings_7dl", transition=Dissolve(0.2), embedded=False)))
            items.append(ESItem(u"Achievements", [
                Hide("menu_7dl", transition=Dissolve(0.2)),
                Hide("settings_7dl", transition=Dissolve(0.2)),
                Hide("contacts_7dl", transition=Dissolve(0.2)),
                Hide("media_7dl", transition=Dissolve(0.2)),
                Jump("sdl_achvlist_main")
            ]))
            items.append(ESItem(u"Contacts", Show("contacts_7dl", transition=Dissolve(0.2))))
            items.append(ESItem(u"Stories", [
                Hide("menu_7dl", transition=Dissolve(0.2)),
                Hide("settings_7dl", transition=Dissolve(0.2)),
                Hide("contacts_7dl", transition=Dissolve(0.2)),
                Hide("media_7dl", transition=Dissolve(0.2)),
                Jump("alt_stories_start")
            ]))
            items.append(ESItem(u"Media", Show("media_7dl", transition=Dissolve(0.2))))
            items.append(ESItem(u"Main menu (Everlasting Summer)", [
                Hide("menu_7dl", transition=Dissolve(0.2)),
                Hide("settings_7dl", transition=Dissolve(0.2)),
                Hide("contacts_7dl", transition=Dissolve(0.2)),
                Hide("media_7dl", transition=Dissolve(0.2)),
                Function(alt_exit),
                MainMenu(confirm=False)
            ]))
        else:
            # Menu when 7DL IS the default main menu
            items.append(ESItem(u"New game", [
                Hide("menu_7dl", transition=Dissolve(0.2)),
                Hide("settings_7dl", transition=Dissolve(0.2)),
                Hide("contacts_7dl", transition=Dissolve(0.2)),
                Hide("media_7dl", transition=Dissolve(0.2)),
                Stop('music', fadeout=2),
                SetField(sdl_mus_engine, "is_active", False),
                Start()
            ]))
            items.append(ESItem(u"Load game", [
                Hide("settings_7dl", transition=Dissolve(0.2)),
                Hide("contacts_7dl", transition=Dissolve(0.2)),
                Hide("media_7dl", transition=Dissolve(0.2)),
                Show("alt_load")
            ]))
            items.append(ESItem(u"Settings", Show("settings_7dl", transition=Dissolve(0.2), embedded=False)))
            items.append(ESItem(u"Achievements", [
                Hide("menu_7dl", transition=Dissolve(0.2)),
                Hide("settings_7dl", transition=Dissolve(0.2)),
                Hide("contacts_7dl", transition=Dissolve(0.2)),
                Hide("media_7dl", transition=Dissolve(0.2)),
                Jump("sdl_achvlist_main")
            ]))
            items.append(ESItem(u"Contacts", Show("contacts_7dl", transition=Dissolve(0.2))))
            items.append(ESItem(u"Stories", [
                Hide("menu_7dl", transition=Dissolve(0.2)),
                Hide("settings_7dl", transition=Dissolve(0.2)),
                Hide("contacts_7dl", transition=Dissolve(0.2)),
                Hide("media_7dl", transition=Dissolve(0.2)),
                Jump("alt_stories_start")
            ]))
            items.append(ESItem(u"Media", Show("media_7dl", transition=Dissolve(0.2))))
            items.append(ESItem(u"Quit", [
                Hide("settings_7dl", transition=Dissolve(0.2)),
                Hide("contacts_7dl", transition=Dissolve(0.2)),
                Hide("media_7dl", transition=Dissolve(0.2)),
                Show("alt_quit", transition=Dissolve(0.2))
            ]))

        if getattr(persistent, "pivo_completed", False):
            items.append(ESItem(u"Statistics", [
                Hide("menu_7dl", transition=Dissolve(0.2)),
                Hide("settings_7dl", transition=Dissolve(0.2)),
                Hide("contacts_7dl", transition=Dissolve(0.2)),
                Hide("media_7dl", transition=Dissolve(0.2)),
                Jump("alt_7dl_stats")
            ]))

        items.append(ESItem(u"Changelog", Show("alt_changelog", Dissolve(0.2), alt_changelog_text)))

        return ESMode("menu_7dl", screen, items, u"7 Days of Summer. Main menu.")

    def es_items_settings_7dl(screen):
        items = []
        embedded = es_scope(screen, "embedded", False)

        if getattr(persistent, "pivo_default_7dl", False) and not embedded:
            items.append(ESItem(u"ES settings", [
                Hide("settings_description_7dl", transition=Dissolve(0.2)),
                Show("alt_preferences", transition=Dissolve(0.2))
            ]))

        # Toggle: Start with 7DS:LA
        if not getattr(persistent, "pivo_default_7dl", False):
            items.append(ESItem(u"Start with 7DS:LA: off. Enter to enable.", [
                SetField(persistent, 'pivo_default_7dl', True),
                Show("alt_copy_saves", Dissolve(0.2),
                     "In this mode, 7DS:LA has its own save slots. Copy mod saves from ES slots to 7DS:LA slots? The saves will be copied sequentially to empty slots.",
                     alt_saves_copy_in)
            ]))
        else:
            items.append(ESItem(u"Start with 7DS:LA: on. Enter to disable.", [
                SetField(persistent, 'pivo_default_7dl', False),
                Show("alt_copy_saves", Dissolve(0.2),
                     "Copy mod saves from 7DS:LA slots to ES slots? The saves will be copied sequentially to empty slots.",
                     alt_saves_copy_out)
            ]))

        # Hentai content
        if not getattr(persistent, "hentai_graphics_7dl", False):
            items.append(ESItem(u"Hentai-content: off. Enter to enable.", [
                SetField(persistent, 'hentai_graphics_7dl', True),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))
        else:
            items.append(ESItem(u"Hentai-content: on. Enter to disable.", [
                SetField(persistent, 'hentai_graphics_7dl', False),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))

        # LP widget
        if not getattr(persistent, "lp_widget_7dl", False):
            items.append(ESItem(u"Widget (LP): off. Enter to enable.", [
                SetField(persistent, 'lp_widget_7dl', True),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))
        else:
            items.append(ESItem(u"Widget (LP): on. Enter to disable.", [
                SetField(persistent, 'lp_widget_7dl', False),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))

        # Music widget
        if not getattr(persistent, "music_widget_7dl", False):
            items.append(ESItem(u"Widget (music): off. Enter to enable.", [
                SetField(persistent, 'music_widget_7dl', True),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))
        else:
            items.append(ESItem(u"Widget (music): on. Enter to disable.", [
                SetField(persistent, 'music_widget_7dl', False),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))

        # Thoughts style
        if not getattr(persistent, "thoughts_tilde_7dl", False):
            items.append(ESItem(u"Thoughts: quotations. Enter to switch to tilde.", [
                SetField(persistent, 'thoughts_tilde_7dl', True),
                Function(alt_thoughts_tilde_update),
                Function(reload_names),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))
        else:
            items.append(ESItem(u"Thoughts: tilde. Enter to switch to quotations.", [
                SetField(persistent, 'thoughts_tilde_7dl', False),
                Function(alt_thoughts_tilde_update),
                Function(reload_names),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))

        # Splash screen
        if not getattr(persistent, "chapter_off_7dl", False):
            items.append(ESItem(u"Splashscreen: on. Enter to disable.", [
                SetField(persistent, 'chapter_off_7dl', True),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))
        else:
            items.append(ESItem(u"Splashscreen: off. Enter to enable.", [
                SetField(persistent, 'chapter_off_7dl', False),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))

        # Achievements emotions
        if not getattr(persistent, "achv_sprite_emo_7dl", False):
            items.append(ESItem(u"Emotions (Achievelist): off. Enter to enable.", [
                SetField(persistent, 'achv_sprite_emo_7dl', True),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))
        else:
            items.append(ESItem(u"Emotions (Achievelist): on. Enter to disable.", [
                SetField(persistent, 'achv_sprite_emo_7dl', False),
                Hide("settings_description_7dl", transition=Dissolve(0.2))
            ]))

        # Streamer mode
        if not getattr(persistent, "stream_mode_7dl", False):
            items.append(ESItem(u"Streamer mode: off. Enter to enable (restarts game).", [
                SetField(persistent, 'stream_mode_7dl', True),
                Show("alt_confirm_reload", Dissolve(0.5), False)
            ]))
        else:
            items.append(ESItem(u"Streamer mode: on. Enter to disable (restarts game).", [
                SetField(persistent, 'stream_mode_7dl', False),
                Show("alt_confirm_reload", Dissolve(0.5), False)
            ]))

        items.append(ESItem(u"Back", Hide("settings_7dl", transition=Dissolve(0.2))))

        return ESMode("settings_7dl", screen, items,
            u"7DS:LA settings. Enter toggles options.",
            escape=Hide("settings_7dl", transition=Dissolve(0.2)))

    def es_items_alt_preferences(screen):
        # Reuse standard preferences list and add 7DL-specific toggle when applicable
        base = es_items_preferences(screen)
        items = __builtin__.list(base.items)

        if getattr(persistent, "pivo_default_7dl", False):
            if not getattr(store, "use_settings_7dl", False):
                items.insert(0, ESItem(u"Show 7DS:LA menu", SetVariable("use_settings_7dl", True)))
            else:
                items.insert(0, ESItem(u"Hide 7DS:LA menu", SetVariable("use_settings_7dl", False)))

        # Ensure Back closes alt_preferences properly
        for i, item in enumerate(items):
            label = item.label() if callable(item.label) else item.label
            if label == u"Back":
                items[i] = ESItem(u"Back", [Hide("alt_preferences"), Return()])
                break

        return ESMode("alt_preferences", screen, items,
            u"Settings (7DS:LA). Left and right arrows change values, Enter toggles.",
            escape=[Hide("alt_preferences"), Return()])

    def es_items_alt_game_menu(screen):
        items = [
            ESItem(u"Return to the story", Return()),
            ESItem(u"Save game", ShowMenu("save")),
            ESItem(u"Load game", ShowMenu("load")),
            ESItem(u"Settings", [ShowMenu("preferences"), Hide("alt_game_menu_selector")]),
            ESItem(u"Main menu", [Function(alt_exit), MainMenu()]),
            ESItem(u"Quit", ShowMenu("quit")),
        ]
        return ESMode("alt_game_menu_selector", screen, items, u"Game menu (7DS:LA).", escape=Return())

    def es_items_alt_save(screen):
        return es_items_file(screen, True)

    def es_items_alt_load(screen):
        return es_items_file(screen, False)

    def es_items_alt_quit(screen):
        items = [
            ESItem(u"Yes, quit", Quit(confirm=False)),
            ESItem(u"No, stay", Hide("alt_quit", transition=Dissolve(0.2))),
        ]
        return ESMode("alt_quit", screen, items, u"Quit the game?",
                      escape=Hide("alt_quit", transition=Dissolve(0.2)))

    def es_notice_lines(text):
        # One list entry per paragraph of a 7DL notice, so long notices can
        # be read a line at a time.
        lines = []
        for part in re.split(r"\n+", text or u""):
            part = es.clean(part)
            if part:
                lines.append(ESItem(part))
        return lines

    def es_items_alt_changelog(screen):
        # Called with return_on_close when the mod shows it by itself after
        # an update; then only Return closes it.
        if es_scope(screen, "return_on_close", False):
            close = Return(True)
        else:
            close = Hide("alt_changelog", transition=Dissolve(0.5))
        items = es_notice_lines(es_scope(screen, "alt_text")) + [ESItem(u"OK", close)]
        return ESMode("alt_changelog", screen, items, u"Notice.", escape=close)

    # The opening choice of hero. The fourth, the Major, appears once the
    # other three have each reached their true ending.
    ES_7DL_HEROES = [
        ("loki", u"Loki. \"Forgive. Farewell.\" Everyone gets the reality they deserve."),
        ("herc", u"Herc. \"Cool it, pal!\" Not every problem is solved by force, and not everything is measured by honesty."),
        ("dr", u"Drisch, the weakling. \"It all began...\" All he cares about is his loneliness and his computer."),
    ]

    def es_items_charsel(screen, major=False):
        items = []
        for var, label in ES_7DL_HEROES:
            items.append(ESItem(label, [SetVariable(var, True), Jump("alt_day0_char")]))
        if major:
            items.append(ESItem(u"The Major. \"Nothing is forever...\" Thinking about the inevitability of death only brings your end closer.",
                Jump("alt_day0_char")))
        return ESMode("charsel_7dl", screen, items, u"Choose your hero.")

    def es_items_dlc_actsel(screen):
        acts = [
            (1, u"Act one: The Owlet and the Butterfly", True),
            (2, u"Act two: The Trofimovs", getattr(persistent, "dlc_act1", False)),
            (3, u"Act three: Boris", getattr(persistent, "dlc_act2", False)),
        ]
        items = []
        for n, label, open_ in acts:
            if open_:
                items.append(ESItem(label, Jump("alt_dlc_act_{0}_start".format(n))))
            else:
                items.append(ESItem(label + u", locked until you finish the act before it."))
        return ESMode("dlc_actsel", screen, items, u"Choose an act.")

    ES_7DL_SAVE_WARNING_LABELS = {
        u"Загрузить это сохранение": u"Load this save",
        u"Загрузить другое сохранение": u"Load another save",
        u"Вернуться на начало дня": u"Go back to the start of the day",
        u"Начать игру заново": u"Start the game over",
        u"Загрузить это сохранение. На свой страх и риск, о возможных последствиях предупрежден.":
            u"Load this save anyway, at your own risk",
        u"Ваши действия:": u"What do you want to do?",
        u"РАБОТОСПОСОБНОСТЬ НЕ ГАРАНТИРУЕТСЯ. ВЫЛЕТ ИГРЫ ВОЗМОЖЕН В ЛЮБОЙ МОМЕНТ":
            u"It may not work, and the game may crash at any moment.",
        u"РЕКОМЕНДУЕТСЯ НАЧАТЬ ИГРУ ЗАНОВО": u"Starting the game over is recommended.",
        u"ЕСЛИ В ПРОЦЕССЕ ДАЛЬНЕЙШЕГО ПРОХОЖДЕНИЯ ВЫ СТОЛКНЁТЕСЬ С ОШИБКАМИ, ЗАГРУЗИТЕ ЭТО СОХРАНЕНИЕ И ВЫБЕРИТЕ «ВЕРНУТЬСЯ НА НАЧАЛО ДНЯ»":
            u"If you run into errors later on, load this save again and choose Go back to the start of the day.",
    }

    def es_items_7dl_save_warning(screen):
        # Shown when loading a save from an older version of 7 Days of Summer.
        items = es_scraped_items(screen, ES_7DL_SAVE_WARNING_LABELS)
        return ESMode("save_warning_7dl", screen, items,
            u"This save comes from an older version of 7 Days of Summer.")

    def es_items_un_cl_selector(screen):
        items = es_scraped_items(screen, {1: u"Day 3", 2: u"Day 4", 3: u"Back to Stories"})
        return ESMode("un_cl_selector_7dl", screen, items, u"Lena-classic. Choose where to start.")

    def es_items_alt_timer(screen):
        items = [ESItem(u"Quick-time event: return to the camp! Press Enter or 7 within {0} seconds.".format(int(ES_7DL_QTE_SECONDS)),
            [Hide("alt_timer"), Return()])]
        return ESMode("alt_timer", screen, items, u"Quick!")

    def es_items_replays_7dl(screen):
        # The Moments tab of Stories: replays of scenes, by route and day.
        # Titles are read from the screen, in the mod's own language.
        items = es_scraped_items(screen, {u"…": u"Back"})
        stories = es_screen("stories_main_7dl")
        if stories is not None:
            items += es_items_stories_main_7dl(stories).items
        return ESMode("replays_7dl", screen, items, u"Moments. Replay scenes you have seen.")

    def es_items_music_7dl(screen):
        items = es_scraped_items(screen)
        return ESMode("music_7dl", screen, items, u"Music player.",
            escape=Hide("music_7dl", transition=Dissolve(0.2)))

    # 7 Days of Summer's ending list ("achievements"). Its captions are text
    # pictures in Russian; these are their English names.
    ES_7DL_ACHV_TEXT = {
        "sdl_achv_7dl_route": u"7DL route", "sdl_achv_xxx_route": u"Special route",
        "sdl_achv_smt_route": u"Other", "sdl_achv_need_route": u"This route isn't finished yet",
        "sdl_achv_info_end": u"Requires the ending", "sdl_achv_info_or": u"or",
        "sdl_achv_info_puz": u"Requires completing the heart puzzle",
        "sdl_achv_char_label_loki": u"Loki", "sdl_achv_char_label_herc": u"Herc",
        "sdl_achv_char_label_dr": u"Drisch",
        "sdl_achv_dlc": u"DLC", "sdl_achv_dlc_act1": u"Alisa's ending",
        "sdl_achv_me_7dl": u"Main story", "sdl_achv_mi_7dl": u"Main story", "sdl_achv_dv_7dl": u"Main story",
        "sdl_achv_sl_7dl": u"Main story", "sdl_achv_un_7dl": u"Main story", "sdl_achv_mt_7dl": u"Main story",
        "sdl_achv_us_7dl": u"Main story",
        "sdl_achv_me_ntr": u"Loner", "sdl_achv_mi_djt": u"Radio host", "sdl_achv_dv_djt": u"Radio host",
        "sdl_achv_sl_clt": u"Classic", "sdl_achv_un_fzd": u"Friend zone", "sdl_achv_va_smt": u"Other",
        "sdl_achv_dv_DR_exc": u"Drisch's exclusive ending", "sdl_achv_dv_HE_exc": u"Herc's exclusive ending",
        "sdl_achv_dv_LO_exc": u"Loki's exclusive ending", "sdl_achv_dv_bad": u"Bad ending",
        "sdl_achv_dv_good": u"Good ending", "sdl_achv_dv_good_RF": u"Good ending, modern Russia",
        "sdl_achv_dv_good_US": u"Good ending, USSR", "sdl_achv_dv_neu": u"Neutral ending",
        "sdl_achv_dv_rej": u"Rejection ending", "sdl_achv_dv_rej_RF": u"Rejection ending, modern Russia",
        "sdl_achv_dv_rej_US": u"Rejection ending, USSR", "sdl_achv_dv_shard": u"Shard of memory",
        "sdl_achv_dv_tran": u"Transit ending", "sdl_achv_dv_true": u"True ending",
        "sdl_achv_me_dr_exc": u"Drisch's exclusive ending", "sdl_achv_me_dr_true": u"Drisch's true ending",
        "sdl_achv_me_good": u"Good ending", "sdl_achv_me_herc_exc": u"Herc's exclusive ending",
        "sdl_achv_me_herc_true": u"Herc's true ending", "sdl_achv_me_loki_exc": u"Loki's exclusive ending",
        "sdl_achv_me_loki_true": u"Loki's true ending", "sdl_achv_me_neu": u"Neutral ending",
        "sdl_achv_me_shard": u"Shard of memory", "sdl_achv_me_true": u"True ending",
        "sdl_achv_mi_DR_exc": u"Drisch's exclusive ending", "sdl_achv_mi_HE_exc": u"Herc's exclusive ending",
        "sdl_achv_mi_LO_exc": u"Loki's exclusive ending", "sdl_achv_mi_bad": u"Bad ending",
        "sdl_achv_mi_good": u"Good ending", "sdl_achv_mi_good_IN": u"Good ending, abroad",
        "sdl_achv_mi_good_RF": u"Good ending, modern Russia", "sdl_achv_mi_good_US": u"Good ending, USSR",
        "sdl_achv_mi_rej": u"Rejection ending", "sdl_achv_mi_shard": u"Shard of memory",
        "sdl_achv_mi_true": u"True ending",
        "sdl_achv_mt_bad": u"Bad ending", "sdl_achv_mt_good": u"Good ending",
        "sdl_achv_mt_herc_exc": u"Herc's exclusive ending", "sdl_achv_mt_neu": u"Neutral ending",
        "sdl_achv_mt_shard": u"Shard of memory", "sdl_achv_mt_true": u"True ending",
        "sdl_achv_sl_DR_good": u"Drisch's good ending", "sdl_achv_sl_HE_good": u"Herc's good ending",
        "sdl_achv_sl_LO_exc": u"Loki's exclusive ending", "sdl_achv_sl_LO_good": u"Loki's good ending",
        "sdl_achv_sl_LO_neu": u"Loki's neutral ending", "sdl_achv_sl_LO_rej": u"Loki's rejection ending",
        "sdl_achv_sl_bad": u"Bad ending", "sdl_achv_sl_good_IN": u"Good ending, abroad",
        "sdl_achv_sl_good_RF": u"Good ending, modern Russia", "sdl_achv_sl_good_US": u"Good ending, USSR",
        "sdl_achv_sl_rej_IN": u"Rejection ending, abroad", "sdl_achv_sl_rej_RF": u"Rejection ending, modern Russia",
        "sdl_achv_sl_shard": u"Shard of memory", "sdl_achv_sl_true_IN": u"True ending, abroad",
        "sdl_achv_un_bad": u"Bad ending", "sdl_achv_un_bad_IN": u"Bad ending, abroad",
        "sdl_achv_un_bad_POST": u"Alisa's postscript", "sdl_achv_un_good_IN": u"Good ending, abroad",
        "sdl_achv_un_good_RF": u"Good ending, modern Russia", "sdl_achv_un_good_US": u"Good ending, USSR",
        "sdl_achv_un_neu": u"Neutral ending", "sdl_achv_un_rej": u"Rejection ending",
        "sdl_achv_un_shard": u"Shard of memory", "sdl_achv_un_true_IN": u"True ending, abroad",
        "sdl_achv_us_bad": u"Bad ending", "sdl_achv_us_good": u"Good ending",
        "sdl_achv_us_good_IN": u"Good ending, the Sparks", "sdl_achv_us_shard": u"Shard of memory",
        "sdl_achv_us_tran_mi": u"Transit ending to Miku", "sdl_achv_us_tran_un": u"Transit ending to Lena",
        "sdl_achv_us_true": u"True ending", "sdl_achv_us_true_IN": u"Abroad ending, the Sparks",
        "sdl_achv_va_certif": u"Certificate of honour!", "sdl_achv_va_club27": u"Club 27",
        "sdl_achv_va_diary": u"Read all three parts of Olga's diary", "sdl_achv_va_drunk": u"Roughed up...",
        "sdl_achv_va_kat": u"Catapult ending", "sdl_achv_va_lost": u"Wasted",
        "sdl_achv_va_qte": u"Reflex and IQ test", "sdl_achv_va_tran": u"Glug, glug...",
        "sdl_achv_va_victim": u"Let us remember him...",
    }

    ES_7DL_SECTIONS = [("mi", u"Miku"), ("dv", u"Alisa"), ("sl", u"Slavya"), ("un", u"Lena"),
        ("mt", u"Olga Dmitrievna"), ("us", u"Ulyana"), ("me", u"Semyon"), ("va", u"Miscellaneous")]

    def es_7dl_image_text(name):
        # English name of a caption picture, or failing that its own text.
        if not name:
            return u""
        parts = []
        try:
            d = renpy.display.image.images.get(tuple(name.split()))
            def visit(x):
                if isinstance(x, renpy.text.text.Text):
                    parts.append(u"".join(t for t in x.text if isinstance(t, __builtin__.basestring)))
            d.visit_all(visit)
        except Exception:
            pass
        own = es.clean(u" ".join(parts))
        # The English translation of the mod has its own English text; the
        # Russian original gets ours.
        if own and not re.search(u"[Ѐ-ӿ]", own):
            return own
        return ES_7DL_ACHV_TEXT.get(name) or own or name

    def es_7dl_ending_name(achv):
        # The caption plus the title on its "achievement unlocked" banner.
        name = es_7dl_image_text(achv.get_text())
        banner = ES_DESCRIPTIONS.get(achv.get_icon() or u"", u"")
        if banner.startswith(u"Achievement banner: "):
            name += u", titled " + banner[len(u"Achievement banner: "):].rstrip(u".")
        return name

    def es_7dl_requirements(achv):
        out = []
        for pre in achv.get_prerequisites() or []:
            if pre.check_conditions():
                continue
            names = [es_7dl_ending_name(a) for a in (pre.get_achievements() or [])]
            text = es_7dl_image_text(pre.get_text())
            if names:
                text += u": " + u" or ".join(names)
            out.append(text)
        return u"; ".join(out)

    def es_7dl_route_counts(route):
        got = total = 0
        for a in route.get_achv_arr():
            total += 1
            if getattr(persistent, a.get_persistent()):
                got += 1
        return got, total

    def es_7dl_set_route(engine, section, route):
        engine.set_cur_section(section)
        engine.run_func_out()
        engine.set_cur_route(route)
        engine.run_func_in()

    def es_7dl_char_adjust(engine):
        def adjust(delta):
            n = engine.get_chars_amount()
            if n < 2:
                return
            engine.cur_char_idx = (engine.get_cur_char_idx() + delta) % n
            renpy.restart_interaction()
            es.ui(es_7dl_char_label(engine))
        return adjust

    def es_7dl_char_label(engine):
        try:
            name = es_7dl_image_text(engine.get_cur_char().get_text()) or u"any hero"
        except Exception:
            name = u"any hero"
        return u"Showing endings for: {0}. Left and right arrows change hero.".format(name)

    def es_items_achievements_7dl(screen):
        engine = es_scope(screen, "engine") or getattr(store, "sdl_achv_engine", None)
        items = []
        exit_items = [i for i in es_scraped_items(es_screen("sdl_achv_section_selector") or screen)
            if i.text() == ES_ACTION_JUMP_LABELS["main_menu_7dl"]]
        route = engine.get_cur_route() if engine else None
        default = getattr(store, "sdl_achv_route_default", None)
        if engine is None or route is None or route is default:
            progress = getattr(store, "sdl_achv_progress", 0)
            items.append(ESItem(u"Endings unlocked: {0}%.".format(progress)))
            for sec, name in ES_7DL_SECTIONS:
                for r in store.sdl_achv_section_to_routes.get(sec, []):
                    got, total = es_7dl_route_counts(r)
                    label = u"{0}: {1}, {2}. {3} of {4} endings.".format(
                        name, es_7dl_image_text(r.get_title()), es_7dl_image_text(r.get_typology()), got, total)
                    if r.get_status() != "completed":
                        label += u" " + ES_7DL_ACHV_TEXT["sdl_achv_need_route"] + u"."
                    items.append(ESItem(label, Function(es_7dl_set_route, engine, sec, r)))
            items += exit_items
            return ESMode("achievements_7dl_routes", screen, items,
                u"Endings list. Choose a route to see its endings.")

        sec_name = dict(ES_7DL_SECTIONS).get(engine.get_cur_section(), u"")
        title = u"{0}: {1}".format(sec_name, es_7dl_image_text(route.get_title())).strip(u": ")
        try:
            mask = engine.get_cur_char().get_char_mask()
        except Exception:
            mask = 15
        if engine.get_chars_amount() > 1:
            items.append(ESItem(lambda: es_7dl_char_label(engine), adjust=es_7dl_char_adjust(engine)))
        hidden = getattr(store, "sdl_achv_hidden", [])
        scope_char = None
        try:
            scope_char = engine.get_cur_char().get_variable()
        except Exception:
            pass
        for achv in route.get_achv_arr():
            got = getattr(persistent, achv.get_persistent())
            if achv.get_persistent() in hidden and not got:
                continue
            name = u"Caption: " + es_7dl_ending_name(achv)
            if not achv.check_mask(mask):
                items.append(ESItem(name + u". Not available with this hero."))
                continue
            if got:
                label = name + u". Unlocked."
                action = None
                if achv.get_replay() is not None:
                    label += u" Enter replays it."
                    action = [Replay("sdl_replay", scope=sdl_add_to_dict(achv.get_replay().get_scope(), "cur_char", scope_char), locked=False),
                              Play("music", get_playing_7dl(), fadein=5)]
                items.append(ESItem(label, action))
                if achv.get_postscriptum() is not None and persistent.alt_binder:
                    items.append(ESItem(name + u". Postscript. Enter plays it.",
                        [Replay("sdl_replay", scope=sdl_add_to_dict(achv.get_postscriptum().get_scope(), "cur_char", scope_char), locked=False),
                         Play("music", get_playing_7dl(), fadein=5)]))
            else:
                req = es_7dl_requirements(achv)
                items.append(ESItem(name + u". Locked." + (u" " + req + u"." if req else u"")))
        items.append(ESItem(u"Back to the list of routes", Function(engine.set_cur_section, None)))
        items += exit_items
        return ESMode("achievements_7dl_endings", screen, items, title + u". Endings.",
            escape=Function(engine.set_cur_section, None))

    # Before some replays 7 Days of Summer asks how earlier choices went:
    # flags, points, one-of-several settings and short lists. The names are
    # read as the mod writes them.
    def es_replay_var_item(var):
        kind = var.get_type()
        text = es.clean(var.get_text())
        if kind == 0:
            return ESItem(lambda: u"{0}: {1}".format(text, u"yes" if var.get_cur_value() else u"no"),
                Function(var.toggle_value), adjust=lambda d: var.toggle_value())
        if kind == 1:
            def adjust(d):
                if d > 0 and var.get_cur_value() < var.get_range():
                    var.cur_val_inc()
                elif d < 0 and var.get_cur_value() > 0:
                    var.cur_val_dec()
                es.ui(__builtin__.str(var.get_cur_value()))
            return ESItem(lambda: u"{0}: {1} of {2}. Left and right arrows change it.".format(
                text, var.get_cur_value(), var.get_range()), adjust=adjust)
        if kind == 2:
            def adjust(d):
                if d > 0 and var.get_cur_val_idx() < var.get_values_amount() - 1:
                    var.cur_val_idx_inc()
                elif d < 0 and var.get_cur_val_idx() > 0:
                    var.cur_val_idx_dec()
                es.ui(es.clean(var.get_cur_descr()))
            return ESItem(lambda: u"{0}: {1}. Left and right arrows change it.".format(
                text, es.clean(var.get_cur_descr())), adjust=adjust)
        return None

    def es_items_replay_vars(screen):
        items = []
        for var in es_scope(screen, "vars") or []:
            if var.get_type() == 3:
                for value, label in var.get_values():
                    def toggle(var=var, value=value):
                        if value in var.get_cur_value():
                            var.del_value(value)
                        elif not var.is_full():
                            var.add_value(value)
                        else:
                            es.ui(u"Already full. Clear another choice first.")
                    items.append(ESItem(renpy.curry(lambda var, value, label: u"{0}, {1}: {2}".format(
                        es.clean(var.get_text()), es.clean(label),
                        u"chosen" if value in var.get_cur_value() else u"not chosen"))(var, value, label),
                        Function(toggle)))
                continue
            if var is getattr(store, "sdl_var_i_me_neu_answ", None) and not persistent.alt_binder:
                continue
            item = es_replay_var_item(var)
            if item is not None:
                items.append(item)
        items.append(ESItem(u"Start the replay", [Hide("sdl_replay_vars", transition=Dissolve(0.5)), Return()]))
        return ESMode("replay_vars_7dl", screen, items,
            u"Replay settings: set how earlier choices went, then choose Start the replay.")

    # The animated opening of 7 Days of Summer, described from its frames.
    ES_7DL_OPENING = [
        u"Night. A young man sits alone at a computer in a dark room, his face lit by the screen.",
        u"A phone alarm rings at 19:00, then a call comes in.",
        u"He pulls on a coat at home under a poster, then stands by a railing on a snowy embankment, city lights behind him.",
        u"He rides a dark, empty bus. Figures in the snow, a man in a long coat, car lights in the night.",
        u"In a bright office, a man in black points a gun at a bearded man.",
        u"A hand reaches out in the dark.",
        u"Summer at the camp: Alisa plays an acoustic guitar on a log; she smiles, eyes closed, a twig in her mouth.",
        u"Lena chews on a paintbrush; later she sits on the steps of a cabin at night, and a jetty stretches into dark water.",
        u"Slavya stands in blazing sunlight, then smiles while a pioneer walks past behind her.",
        u"Miku closes her eyes, her teal twin tails falling over her shoulders.",
        u"On a red bus, the young man looks up wide-eyed. Through the window, the camp gates with their pioneer statue.",
        u"He stands in the open bus doorway, then faces you, calm.",
        u"In grey, an empty bus stop and an old bus among the trees, and the title: 7 Days of Summer.",
    ]

    def es_items_movie_7dl(screen):
        items = [ESItem(t) for t in ES_7DL_OPENING]
        items.append(ESItem(u"Skip the video", Return(0)))
        return ESMode("movie_7dl", screen, items,
            u"7 Days of Summer opening video, about two minutes, with a song. Arrow down to read what it shows. Enter on Skip skips it.")

    def es_items_alt_700(screen):
        items = es_notice_lines(es_scope(screen, "alt_text")) + [ESItem(u"OK", Return(True))]
        return ESMode("alt_700", screen, items, u"Notice.", escape=Return(True))

    def es_items_alt_copy_saves(screen):
        fnkt = es_scope(screen, "fnkt")
        items = [
            ESItem(u"Yes", [
                Hide("alt_copy_saves", Dissolve(0.5)),
                Function(fnkt) if fnkt is not None else NullAction(),
                Show("alt_confirm_reload", Dissolve(0.5), True)
            ]),
            ESItem(u"No", [
                Hide("alt_copy_saves", Dissolve(0.5)),
                Show("alt_confirm_reload", Dissolve(0.5), False)
            ]),
        ]
        return ESMode("alt_copy_saves", screen, items, u"Copy saves?",
                      escape=Hide("alt_copy_saves", Dissolve(0.5)))

    def es_items_alt_confirm_reload(screen):
        items = [ESItem(u"OK", [Function(renpy.music.stop), Function(renpy.utter_restart)])]
        return ESMode("alt_confirm_reload", screen, items, u"Game will be restarted.",
                      escape=[Function(renpy.music.stop), Function(renpy.utter_restart)])

    def es_items_contacts_7dl(screen):
        items = [
            ESItem(u"Boosty", OpenURL("https://boosty.to/7dlla")),
            ESItem(u"VKontakte", OpenURL("https://vk.com/bl_7dl")),
            ESItem(u"Telegram", OpenURL("https://t.me/sevendaysofbeer")),
            ESItem(u"Discord", OpenURL("https://discord.com/invite/qd8drECDHp")),
            ESItem(u"YouTube", OpenURL("https://www.youtube.com/@7dlLA")),
            ESItem(u"Steam Workshop", OpenURL("https://steamcommunity.com/sharedfiles/filedetails/?id=441054187")),
            ESItem(u"Back", Hide("contacts_7dl", transition=Dissolve(0.2))),
        ]
        return ESMode("contacts_7dl", screen, items, u"Contacts.",
                      escape=Hide("contacts_7dl", transition=Dissolve(0.2)))

    def es_items_media_7dl(screen):
        items = [
            ESItem(u"Gallery", [
                Hide("media_7dl", transition=Dissolve(0.2)),
                Hide("menu_7dl", transition=Dissolve(0.2)),
                Jump("sdl_gall_start")
            ]),
            ESItem(u"Music player", [
                Hide("media_7dl", transition=Dissolve(0.2)),
                Function(sdl_mus_progress_calc),
                Show("music_7dl", transition=Dissolve(0.2), default_music=get_menu_track_7dl())
            ]),
            ESItem(u"Back", Hide("media_7dl", transition=Dissolve(0.2))),
        ]
        return ESMode("media_7dl", screen, items, u"Media.",
                      escape=Hide("media_7dl", transition=Dissolve(0.2)))

    # ------------------------------------------------------------------
    # 7DL Stories ("Истории")
    # ------------------------------------------------------------------

    def es_start_story(label):
        return [
            Hide("stories_main_7dl", transition=Dissolve(0.2)),
            Stop('music', fadeout=1),
            SetField(sdl_mus_engine, "is_active", False),
            Start(label) if getattr(persistent, "pivo_default_7dl", False) else Jump(label)
        ]

    def es_items_stories_main_7dl(screen):
        mode = getattr(store, "stories_mode_7dl", "") or "moments"
        items = []
        if mode != "moments":
            items.append(ESItem(u"Moments (Memory Forest)", [
                SetVariable("stories_mode_7dl", "moments"),
                Hide("stories_main_7dl", transition=Dissolve(0.2)),
                Jump("alt_stories_start")
            ]))
        else:
            items.append(ESItem(u"Moments (Memory Forest), current section"))
        if mode != "road":
            items.append(ESItem(u"The Old Road", [
                SetVariable("stories_mode_7dl", "road"),
                Hide("stories_main_7dl", transition=Dissolve(0.2)),
                Jump("alt_stories_start")
            ]))
        else:
            items.append(ESItem(u"The Old Road, current section"))
        items.append(ESItem(u"Exit to main menu", [
            Hide("stories_main_7dl", transition=Dissolve(0.2)),
            SetVariable("stories_mode_7dl", ""),
            Jump("main_menu_7dl")
        ]))
        intro = u"Stories. Current section: {0}.".format(
            u"Moments" if mode == "moments" else u"The Old Road" if mode == "road" else u"none")
        return ESMode("stories_main_7dl", screen, items, intro,
                      escape=[Hide("stories_main_7dl", transition=Dissolve(0.2)),
                              SetVariable("stories_mode_7dl", ""), Jump("main_menu_7dl")])

    def es_items_stories_exit_7dl(screen):
        items = [ESItem(u"Exit to main menu", [
            Hide("stories_main_7dl", transition=Dissolve(0.2)),
            SetVariable("stories_mode_7dl", ""),
            Jump("main_menu_7dl")
        ])]
        return ESMode("stories_exit_7dl", screen, items, u"Exit Stories.",
                      escape=[Hide("stories_main_7dl", transition=Dissolve(0.2)),
                              SetVariable("stories_mode_7dl", ""), Jump("main_menu_7dl")])

    def es_items_road_main_7dl(screen):
        items = [
            ESItem(u"7DS fanfics", ShowTransient("road_fanfics_1_7dl", transition=Dissolve(0.2))),
        ]
        if getattr(persistent, "alt_binder", False):
            items.append(ESItem(u"Old endings", ShowTransient("old_ends_7dl", transition=Dissolve(0.2))))
            items.append(ESItem(u"Other stuff", ShowTransient("unreleased_1_7dl", transition=Dissolve(0.2))))
        else:
            items.append(ESItem(u"Old endings (locked — need heart puzzle)",
                                Show("alt_need_binder", transition=Dissolve(0.2))))
            items.append(ESItem(u"Other stuff (locked — need heart puzzle)",
                                Show("alt_need_binder", transition=Dissolve(0.2))))
        items.append(ESItem(u"Back to Stories tabs", [
            SetVariable("stories_mode_7dl", "moments"),
            Hide("road_main_7dl", transition=Dissolve(0.2)),
            Hide("stories_main_7dl", transition=Dissolve(0.2)),
            Jump("alt_stories_start")
        ]))
        items.append(ESItem(u"Exit to main menu", [
            Hide("stories_main_7dl", transition=Dissolve(0.2)),
            SetVariable("stories_mode_7dl", ""),
            Jump("main_menu_7dl")
        ]))
        return ESMode("road_main_7dl", screen, items,
            u"The Old Road. Non-canon scenarios.",
            escape=[SetVariable("stories_mode_7dl", "moments"),
                    Hide("road_main_7dl", transition=Dissolve(0.2)),
                    Hide("stories_main_7dl", transition=Dissolve(0.2)),
                    Jump("alt_stories_start")])

    def es_items_road_main_info_7dl(screen):
        items = [ESItem(
            u"The Old Road features non-canon scenarios for 7DS:LA. "
            u"They were either created with outdated concepts or without established canon."
        )]
        return ESMode("road_main_info_7dl", screen, items, u"About The Old Road.")

    def es_items_road_fanfics_1_7dl(screen):
        items = [
            ESItem(u"Cat route (Cat team)", es_start_story("alt_day4_start_uvao")),
            ESItem(u"Blood on the snow (N. Ilyin)", es_start_story("kns_start")),
            ESItem(u"Colors (G. Polski)", es_start_story("alt_colors_7dl")),
            ESItem(u"New Year miracle", es_start_story("alt_chudo_novogodnee")),
            ESItem(u"Rebirth", es_start_story("alt_chudesa_byvayut")),
            ESItem(u"A piece of soul", es_start_story("alt_bit_of_soul")),
            ESItem(u"Ghost of a sad girl", es_start_story("the_ghost_of_a_sad_girl")),
            ESItem(u"Scary stories in the library (F. Lopatin)", es_start_story("fedor_scary_story")),
            ESItem(u"Camp scary story (ranger)", es_start_story("ranger_scary_story")),
            ESItem(u"Perfect weapon (Slavya-witch)", es_start_story("ultimate_weapon_sl_vedma")),
            ESItem(u"Next page", [
                Hide("road_fanfics_1_7dl", transition=Dissolve(0.2)),
                ShowTransient("road_fanfics_2_7dl", transition=Dissolve(0.2))
            ]),
            ESItem(u"Back", Hide("road_fanfics_1_7dl", transition=Dissolve(0.2))),
        ]
        return ESMode("road_fanfics_1_7dl", screen, items, u"7DS fanfics, page 1.",
                      escape=Hide("road_fanfics_1_7dl", transition=Dissolve(0.2)))

    def es_items_road_fanfics_2_7dl(screen):
        items = [
            ESItem(u"My Sychik (Broni)", es_start_story("sl_sychik")),
            ESItem(u"Previous page", [
                Hide("road_fanfics_2_7dl", transition=Dissolve(0.2)),
                ShowTransient("road_fanfics_1_7dl", transition=Dissolve(0.2))
            ]),
            ESItem(u"Back", Hide("road_fanfics_2_7dl", transition=Dissolve(0.2))),
        ]
        return ESMode("road_fanfics_2_7dl", screen, items, u"7DS fanfics, page 2.",
                      escape=Hide("road_fanfics_2_7dl", transition=Dissolve(0.2)))

    def es_items_old_ends_7dl(screen):
        items = [
            ESItem(u"Miku endings", [
                Hide("old_ends_7dl", transition=Dissolve(0.2)),
                ShowTransient("old_ends_mi_7dl", transition=Dissolve(0.2))
            ]),
            ESItem(u"Old postscripts", [
                Hide("old_ends_7dl", transition=Dissolve(0.2)),
                ShowTransient("old_ends_ps_7dl", transition=Dissolve(0.2))
            ]),
            ESItem(u"Septima endings", [
                Hide("old_ends_7dl", transition=Dissolve(0.2)),
                ShowTransient("old_ends_sept_7dl", transition=Dissolve(0.2))
            ]),
            ESItem(u"Other endings", [
                Hide("old_ends_7dl", transition=Dissolve(0.2)),
                ShowTransient("old_ends_other_7dl", transition=Dissolve(0.2))
            ]),
            ESItem(u"Back", Hide("old_ends_7dl", transition=Dissolve(0.2))),
        ]
        return ESMode("old_ends_7dl", screen, items, u"Old endings.",
                      escape=Hide("old_ends_7dl", transition=Dissolve(0.2)))

    def es_items_old_ends_mi_7dl(screen):
        items = [
            ESItem(u"Declared unfit", es_start_story("alt_day4_mi2sl_transit2")),
            ESItem(u"Sparkle (old version)", es_start_story("alt_day7_mi_7dl_sparkle")),
            ESItem(u"May I? (old version)", es_start_story("alt_day7_mi_7dl_vatashi")),
            ESItem(u"Thank you (old version)", es_start_story("alt_day7_mi_7dl_reject")),
            ESItem(u"Back", [
                Hide("old_ends_mi_7dl", transition=Dissolve(0.2)),
                ShowTransient("old_ends_7dl", transition=Dissolve(0.2))
            ]),
        ]
        return ESMode("old_ends_mi_7dl", screen, items, u"Miku old endings.",
                      escape=[Hide("old_ends_mi_7dl", transition=Dissolve(0.2)),
                              ShowTransient("old_ends_7dl", transition=Dissolve(0.2))])

    def es_items_old_ends_ps_7dl(screen):
        items = [
            ESItem(u"Miku-DJ postscript", es_start_story("alt_day7_mi_dj_good_rf_ps_old")),
            ESItem(u"Alisa-7dl postscript", es_start_story("alt_day7_dv_7dl_good_rf_ps_old")),
            ESItem(u"Lena-7dl postscript", es_start_story("alt_day7_un_7dl_good_rf_ps_old")),
            ESItem(u"Back", [
                Hide("old_ends_ps_7dl", transition=Dissolve(0.2)),
                ShowTransient("old_ends_7dl", transition=Dissolve(0.2))
            ]),
        ]
        return ESMode("old_ends_ps_7dl", screen, items, u"Old postscripts.",
                      escape=[Hide("old_ends_ps_7dl", transition=Dissolve(0.2)),
                              ShowTransient("old_ends_7dl", transition=Dissolve(0.2))])

    def es_items_old_ends_sept_7dl(screen):
        items = [
            ESItem(u"I will definitely find (Alisa)", es_start_story("alt_day7_dv_7dl_sept")),
            ESItem(u"No miracles (Slavya)", es_start_story("alt_day7_sl_7dl_sept")),
            ESItem(u"The search continues (Lena)", es_start_story("alt_day7_un_7dl_sept")),
            ESItem(u"Gleam of summer (Ulyana)", es_start_story("alt_day7_us_px_sept")),
            ESItem(u"Strange people (Olga)", es_start_story("alt_day7_mt_7dl_sept")),
            ESItem(u"Bitter truth (Miku)", es_start_story("alt_day7_mi_7dl_sept")),
            ESItem(u"Faceless hands (Loner)", es_start_story("alt_day7_me_neu_sept")),
            ESItem(u"Back", [
                Hide("old_ends_sept_7dl", transition=Dissolve(0.2)),
                ShowTransient("old_ends_7dl", transition=Dissolve(0.2))
            ]),
        ]
        return ESMode("old_ends_sept_7dl", screen, items, u"Septima endings.",
                      escape=[Hide("old_ends_sept_7dl", transition=Dissolve(0.2)),
                              ShowTransient("old_ends_7dl", transition=Dissolve(0.2))])

    def es_items_old_ends_other_7dl(screen):
        items = [
            ESItem(u"Old loner bad ending", es_start_story("alt_day7_me_neu_bad_old")),
            ESItem(u"Old Loki neutral", es_start_story("alt_day7_me_neu_loki_neu_old")),
            ESItem(u"Old Drisch neutral", es_start_story("alt_day7_me_neu_dr_neu_old")),
            ESItem(u"Old Ulyana bad", es_start_story("alt_day7_us_7dl_verses2")),
            ESItem(u"It was quiet here once (Lena-7dl reject)", es_start_story("alt_day7_un_7dl_rej_old")),
            ESItem(u"Back", [
                Hide("old_ends_other_7dl", transition=Dissolve(0.2)),
                ShowTransient("old_ends_7dl", transition=Dissolve(0.2))
            ]),
        ]
        return ESMode("old_ends_other_7dl", screen, items, u"Other old endings.",
                      escape=[Hide("old_ends_other_7dl", transition=Dissolve(0.2)),
                              ShowTransient("old_ends_7dl", transition=Dissolve(0.2))])

    def es_items_unreleased_1_7dl(screen):
        items = [
            ESItem(u"Demiurge Trio (2014)", es_start_story("alt_day4_start_neutral_ending")),
            ESItem(u"Mysterious door (Slavya-CL)", es_start_story("alt_day7_sl_cl_square1")),
            ESItem(u"Shurik's AI (Slavya-CL)", es_start_story("alt_day7_sl_cl_ps")),
            ESItem(u"Phone in the old camp (Slavya-7dl)", es_start_story("alt_day4_sl_7dl_old_phone")),
            ESItem(u"Cherry-berry (old Lena-FZ)", es_start_story("alt_cherry_berry")),
            ESItem(u"Abyss of anal destruction (Old Loner D.6)", es_start_story("alt_uvao_hentai")),
            ESItem(u"Old sex scenes (Lena7DS)", es_start_story("alt_day4_un_7dl_hentai_old")),
            ESItem(u"Date with Miku on the beach", es_start_story("alt_day4_beach_night_mi")),
            ESItem(u"Next page", [
                Hide("unreleased_1_7dl", transition=Dissolve(0.2)),
                ShowTransient("unreleased_2_7dl", transition=Dissolve(0.2))
            ]),
            ESItem(u"Back", Hide("unreleased_1_7dl", transition=Dissolve(0.2))),
        ]
        return ESMode("unreleased_1_7dl", screen, items, u"Other stuff, page 1.",
                      escape=Hide("unreleased_1_7dl", transition=Dissolve(0.2)))

    def es_items_unreleased_2_7dl(screen):
        items = [
            ESItem(u"Lena-classic days 3-4", es_start_story("alt_day3_un_cl_start")),
            ESItem(u"Old Lena-FZ day 4", es_start_story("alt_day4_un_fz_start_old")),
            ESItem(u"Miku-classic day 4", es_start_story("alt_day4_mi_cl_start")),
            ESItem(u"Alisa-classic start", es_start_story("alt_day4_dv_cl_start")),
            ESItem(u"Slavya-witch start", es_start_story("alt_day4_sl_wh_start")),
            ESItem(u"Deleted scenes from Slavya-CL intelligence branch",
                   es_start_story("alt_day6_sl_cl_narcomania")),
            ESItem(u"Previous page", [
                Hide("unreleased_2_7dl", transition=Dissolve(0.2)),
                ShowTransient("unreleased_1_7dl", transition=Dissolve(0.2))
            ]),
            ESItem(u"Next page", [
                Hide("unreleased_2_7dl", transition=Dissolve(0.2)),
                ShowTransient("unreleased_3_7dl", transition=Dissolve(0.2))
            ]),
            ESItem(u"Back", Hide("unreleased_2_7dl", transition=Dissolve(0.2))),
        ]
        return ESMode("unreleased_2_7dl", screen, items, u"Other stuff, page 2.",
                      escape=Hide("unreleased_2_7dl", transition=Dissolve(0.2)))

    def es_items_unreleased_3_7dl(screen):
        items = [
            ESItem(u"Old Sych day 6", es_start_story("alt_day6_me_neu_start_old")),
            ESItem(u"Old Sych day 7", es_start_story("alt_day7_me_neu_start_old")),
            ESItem(u"First Septima prologue", es_start_story("alt_septim_prologue_old")),
            ESItem(u"Second Septima prologue", es_start_story("alt_septim_prologue")),
            ESItem(u"Septima route start", es_start_story("alt_day1_me_d3_start")),
            ESItem(u"Noir day 4", es_start_story("alt_day4_no_start")),
            ESItem(u"Previous page", [
                Hide("unreleased_3_7dl", transition=Dissolve(0.2)),
                ShowTransient("unreleased_2_7dl", transition=Dissolve(0.2))
            ]),
            ESItem(u"Back", Hide("unreleased_3_7dl", transition=Dissolve(0.2))),
        ]
        return ESMode("unreleased_3_7dl", screen, items, u"Other stuff, page 3.",
                      escape=Hide("unreleased_3_7dl", transition=Dissolve(0.2)))

    def es_items_alt_need_binder(screen):
        items = [ESItem(u"OK", Hide("alt_need_binder"))]
        return ESMode("alt_need_binder", screen, items,
            u"You must complete a heart puzzle to access this section.",
            escape=Hide("alt_need_binder"))

    # ------------------------------------------------------------------
    # 7DL Gallery
    # ------------------------------------------------------------------

    def es_items_sdl_gall_main(screen):
        mode = getattr(store, "sdl_gall_mode", "") or ""
        items = []
        if mode != "bgs":
            items.append(ESItem(u"Backgrounds", [
                SetVariable("sdl_gall_mode", "bgs"),
                SetVariable("sdl_gall_page", 1),
                Function(sdl_gal_set_list),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
                Show("sdl_gall_bw", transition=Dissolve(0.2)),
                Show("sdl_gall_fw", transition=Dissolve(0.2)),
                Show("sdl_gall_sshow", transition=Dissolve(0.2)),
            ]))
        else:
            items.append(ESItem(u"Backgrounds, current"))
        if mode != "arts":
            items.append(ESItem(u"Arts / CGs", [
                SetVariable("sdl_gall_mode", "arts"),
                SetVariable("sdl_gall_page", 1),
                Function(sdl_gal_set_list),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
                Show("sdl_gall_bw", transition=Dissolve(0.2)),
                Show("sdl_gall_fw", transition=Dissolve(0.2)),
                Show("sdl_gall_sshow", transition=Dissolve(0.2)),
            ]))
        else:
            items.append(ESItem(u"Arts / CGs, current"))
        if mode not in ("bgs", "filter"):
            items.append(ESItem(u"Filter by character", [
                Hide("sdl_gall_sshow", transition=Dissolve(0.2)),
                Hide("sdl_gall_bw", transition=Dissolve(0.2)),
                Hide("sdl_gall_fw", transition=Dissolve(0.2)),
                SetVariable("sdl_gall_mode", "filter"),
                SetVariable("sdl_gall_page", 1),
                Show("sdl_gall_filter", transition=Dissolve(0.2)),
            ]))
        items.append(ESItem(u"Exit gallery", [
            Hide("sdl_gall_photos", transition=Dissolve(0.2)),
            Hide("sdl_gall_bw", transition=Dissolve(0.2)),
            Hide("sdl_gall_fw", transition=Dissolve(0.2)),
            Hide("sdl_gall_sshow", transition=Dissolve(0.2)),
            Hide("sdl_gall_exit", transition=Dissolve(0.2)),
            Hide("sdl_gall_page_input", transition=Dissolve(0.2)),
            SetVariable("sdl_gall_mode", ""),
            SetVariable("sdl_gall_page", 1),
            Jump("main_menu_7dl")
        ]))
        progress = getattr(store, "sdl_gall_progress", 0)
        return ESMode("sdl_gall_main", screen, items,
            u"Gallery. Progress {0}%.".format(progress),
            escape=[Hide("sdl_gall_photos", transition=Dissolve(0.2)),
                    Hide("sdl_gall_bw", transition=Dissolve(0.2)),
                    Hide("sdl_gall_fw", transition=Dissolve(0.2)),
                    Hide("sdl_gall_sshow", transition=Dissolve(0.2)),
                    Hide("sdl_gall_exit", transition=Dissolve(0.2)),
                    SetVariable("sdl_gall_mode", ""),
                    SetVariable("sdl_gall_page", 1),
                    Jump("main_menu_7dl")])

    def es_items_sdl_gall_photos(screen):
        mode = getattr(store, "sdl_gall_mode", "") or "arts"
        page = int(getattr(store, "sdl_gall_page", 1) or 1)
        curr = __builtin__.list(getattr(store, "sdl_gall_curr_list", []) or [])
        total_pages = __builtin__.max(1,(len(curr) - 1) // 6 + 1) if curr else 1
        progress = getattr(store, "sdl_gall_progress", 0)
        items = [
            ESItem(u"Page {0} of {1}. Progress {2}%. Section: {3}.".format(
                page, total_pages, progress,
                u"backgrounds" if mode == "bgs" else (
                    u"arts" if mode == "arts" else u"filter {0}".format(mode)))),
        ]
        # Section switches (stay inside photos; do not jump to main which auto-reopens)
        if mode != "bgs":
            items.append(ESItem(u"Switch to backgrounds", [
                SetVariable("sdl_gall_mode", "bgs"),
                SetVariable("sdl_gall_page", 1),
                Function(sdl_gal_set_list),
                Hide("sdl_gall_photos", transition=Dissolve(0.2)),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
            ]))
        if mode != "arts":
            items.append(ESItem(u"Switch to arts", [
                SetVariable("sdl_gall_mode", "arts"),
                SetVariable("sdl_gall_page", 1),
                Function(sdl_gal_set_list),
                Hide("sdl_gall_photos", transition=Dissolve(0.2)),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
            ]))
        items.append(ESItem(u"Filter by character", [
            Hide("sdl_gall_sshow", transition=Dissolve(0.2)),
            Hide("sdl_gall_bw", transition=Dissolve(0.2)),
            Hide("sdl_gall_fw", transition=Dissolve(0.2)),
            Hide("sdl_gall_photos", transition=Dissolve(0.2)),
            SetVariable("sdl_gall_mode", "filter"),
            SetVariable("sdl_gall_page", 1),
            Show("sdl_gall_filter", transition=Dissolve(0.2)),
        ]))

        start_i = (page - 1) * 6
        slice_ = curr[start_i:start_i + 6]
        for i, img in enumerate(slice_):
            try:
                seen = sdl_gal_check_seen(img)
            except Exception:
                seen = False
            try:
                name = img.get_img()
            except Exception:
                name = u"image"
            if seen:
                hentai_ok = True
                try:
                    if mode == "arts" or mode in getattr(store, "sdl_gall_girls_list", []):
                        hentai_ok = getattr(persistent, "hentai_graphics_7dl", False) or (not img.get_hent())
                except Exception:
                    pass
                if hentai_ok:
                    items.append(ESItem(
                        u"Image {0}: {1}".format(start_i + i + 1, name),
                        [
                            Hide("sdl_gall_photos", transition=Dissolve(0.2)),
                            Hide("sdl_gall_bw", transition=Dissolve(0.2)),
                            Hide("sdl_gall_fw", transition=Dissolve(0.2)),
                            Hide("sdl_gall_sshow", transition=Dissolve(0.2)),
                            Hide("sdl_gall_exit", transition=Dissolve(0.2)),
                            Call("sdl_gall_show_imgs", img),
                        ]))
                else:
                    items.append(ESItem(u"Image {0}: locked (18+ disabled)".format(start_i + i + 1)))
            else:
                items.append(ESItem(u"Image {0}: locked".format(start_i + i + 1)))
        if page > 1:
            items.append(ESItem(u"Previous page", [
                SetVariable("sdl_gall_page", page - 1),
                Hide("sdl_gall_photos", transition=Dissolve(0.2)),
                Function(sdl_gal_set_list),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
            ]))
        if page < total_pages:
            items.append(ESItem(u"Next page", [
                SetVariable("sdl_gall_page", page + 1),
                Hide("sdl_gall_photos", transition=Dissolve(0.2)),
                Function(sdl_gal_set_list),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
            ]))
        items.append(ESItem(u"Slideshow", [
            Hide("sdl_gall_photos", transition=Dissolve(0.2)),
            Hide("sdl_gall_bw", transition=Dissolve(0.2)),
            Hide("sdl_gall_fw", transition=Dissolve(0.2)),
            Hide("sdl_gall_sshow", transition=Dissolve(0.2)),
            Jump("sdl_gall_sshow_imgs"),
        ]))
        items.append(ESItem(u"Exit gallery", [
            Hide("sdl_gall_photos", transition=Dissolve(0.2)),
            Hide("sdl_gall_bw", transition=Dissolve(0.2)),
            Hide("sdl_gall_fw", transition=Dissolve(0.2)),
            Hide("sdl_gall_sshow", transition=Dissolve(0.2)),
            Hide("sdl_gall_exit", transition=Dissolve(0.2)),
            Hide("sdl_gall_page_input", transition=Dissolve(0.2)),
            SetVariable("sdl_gall_mode", ""),
            SetVariable("sdl_gall_page", 1),
            SetVariable("sdl_gall_sshow", False),
            Jump("main_menu_7dl"),
        ]))
        return ESMode("sdl_gall_photos", screen, items,
            u"Gallery.",
            escape=[
                Hide("sdl_gall_photos", transition=Dissolve(0.2)),
                Hide("sdl_gall_bw", transition=Dissolve(0.2)),
                Hide("sdl_gall_fw", transition=Dissolve(0.2)),
                Hide("sdl_gall_sshow", transition=Dissolve(0.2)),
                Hide("sdl_gall_exit", transition=Dissolve(0.2)),
                SetVariable("sdl_gall_mode", ""),
                SetVariable("sdl_gall_page", 1),
                SetVariable("sdl_gall_sshow", False),
                Jump("main_menu_7dl"),
            ])


    def es_items_sdl_gall_filter(screen):
        items = [
            ESItem(u"Miku", [
                Hide("sdl_gall_filter", transition=Dissolve(0.2)),
                SetVariable("sdl_gall_mode", "mi"),
                SetVariable("sdl_gall_page", 1),
                Function(sdl_gal_set_list),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
                Show("sdl_gall_bw", transition=Dissolve(0.2)),
                Show("sdl_gall_fw", transition=Dissolve(0.2)),
            ]),
            ESItem(u"Alisa", [
                Hide("sdl_gall_filter", transition=Dissolve(0.2)),
                SetVariable("sdl_gall_mode", "dv"),
                SetVariable("sdl_gall_page", 1),
                Function(sdl_gal_set_list),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
                Show("sdl_gall_bw", transition=Dissolve(0.2)),
                Show("sdl_gall_fw", transition=Dissolve(0.2)),
            ]),
            ESItem(u"Slavya", [
                Hide("sdl_gall_filter", transition=Dissolve(0.2)),
                SetVariable("sdl_gall_mode", "sl"),
                SetVariable("sdl_gall_page", 1),
                Function(sdl_gal_set_list),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
                Show("sdl_gall_bw", transition=Dissolve(0.2)),
                Show("sdl_gall_fw", transition=Dissolve(0.2)),
            ]),
            ESItem(u"Lena", [
                Hide("sdl_gall_filter", transition=Dissolve(0.2)),
                SetVariable("sdl_gall_mode", "un"),
                SetVariable("sdl_gall_page", 1),
                Function(sdl_gal_set_list),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
                Show("sdl_gall_bw", transition=Dissolve(0.2)),
                Show("sdl_gall_fw", transition=Dissolve(0.2)),
            ]),
            ESItem(u"Olga", [
                Hide("sdl_gall_filter", transition=Dissolve(0.2)),
                SetVariable("sdl_gall_mode", "mt"),
                SetVariable("sdl_gall_page", 1),
                Function(sdl_gal_set_list),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
                Show("sdl_gall_bw", transition=Dissolve(0.2)),
                Show("sdl_gall_fw", transition=Dissolve(0.2)),
            ]),
            ESItem(u"Ulyana", [
                Hide("sdl_gall_filter", transition=Dissolve(0.2)),
                SetVariable("sdl_gall_mode", "us"),
                SetVariable("sdl_gall_page", 1),
                Function(sdl_gal_set_list),
                Show("sdl_gall_photos", transition=Dissolve(0.2)),
                Show("sdl_gall_bw", transition=Dissolve(0.2)),
                Show("sdl_gall_fw", transition=Dissolve(0.2)),
            ]),
            ESItem(u"Back", [
                Hide("sdl_gall_filter", transition=Dissolve(0.2)),
                SetVariable("sdl_gall_mode", ""),
                SetVariable("sdl_gall_page", 1),
                Jump("main_menu_7dl"),
            ]),
        ]
        return ESMode("sdl_gall_filter", screen, items, u"Filter gallery by character.",
                      escape=[Hide("sdl_gall_filter", transition=Dissolve(0.2)),
                              SetVariable("sdl_gall_mode", ""),
                              Jump("main_menu_7dl")])

    def es_items_sdl_gall_exit(screen):
        items = [ESItem(u"Exit gallery", [
            Hide("sdl_gall_photos", transition=Dissolve(0.2)),
            Hide("sdl_gall_bw", transition=Dissolve(0.2)),
            Hide("sdl_gall_fw", transition=Dissolve(0.2)),
            Hide("sdl_gall_sshow", transition=Dissolve(0.2)),
            Hide("sdl_gall_exit", transition=Dissolve(0.2)),
            Hide("sdl_gall_page_input", transition=Dissolve(0.2)),
            SetVariable("sdl_gall_mode", ""),
            SetVariable("sdl_gall_page", 1),
            SetVariable("sdl_gall_sshow", False),
            Jump("main_menu_7dl"),
        ])]
        return ESMode("sdl_gall_exit", screen, items, u"Exit gallery.",
                      escape=[Hide("sdl_gall_exit", transition=Dissolve(0.2)),
                              SetVariable("sdl_gall_mode", ""),
                              SetVariable("sdl_gall_sshow", False),
                              Jump("main_menu_7dl")])

    # ------------------------------------------------------------------
    # Working out the current mode.
    # ------------------------------------------------------------------

    ES_SCREEN_MODES = [
        # 7 Days of Summer prompts that sit on top of everything else.
        ("alt_load_warning", es_items_7dl_save_warning),
        ("alt_incompatible_release", es_items_7dl_save_warning),
        ("alt_changelog", es_items_alt_changelog),
        ("alt_700", es_items_alt_700),
        ("alt_timer", es_items_alt_timer),
        ("sdl_replay_vars", es_items_replay_vars),
        ("alt_movie_screen", es_items_movie_7dl),
        ("alt_day0_charsel", es_items_charsel),
        ("alt_day0_charsel_am", lambda s: es_items_charsel(s, True)),
        ("dlc_actsel", es_items_dlc_actsel),
        ("alt_un_cl_selector", es_items_un_cl_selector),
        ("music_7dl", es_items_music_7dl),
        ("sdl_achvlist_main", es_items_achievements_7dl),
        # 7DL Stories — list overlays first; do NOT register stories_exit_7dl
        # (it is always shown as a transient and would hide Moments/Road).
        ("road_fanfics_1_7dl", es_items_road_fanfics_1_7dl),
        ("road_fanfics_2_7dl", es_items_road_fanfics_2_7dl),
        ("old_ends_mi_7dl", es_items_old_ends_mi_7dl),
        ("old_ends_ps_7dl", es_items_old_ends_ps_7dl),
        ("old_ends_sept_7dl", es_items_old_ends_sept_7dl),
        ("old_ends_other_7dl", es_items_old_ends_other_7dl),
        ("old_ends_7dl", es_items_old_ends_7dl),
        ("unreleased_1_7dl", es_items_unreleased_1_7dl),
        ("unreleased_2_7dl", es_items_unreleased_2_7dl),
        ("unreleased_3_7dl", es_items_unreleased_3_7dl),
        ("alt_need_binder", es_items_alt_need_binder),
        ("road_main_7dl", es_items_road_main_7dl),
        ("sdl_replays_main", es_items_replays_7dl),
        ("stories_main_7dl", es_items_stories_main_7dl),
        # 7DL Gallery — photos/filter only (main/exit auto-show and steal focus)
        ("sdl_gall_filter", es_items_sdl_gall_filter),
        ("sdl_gall_photos", es_items_sdl_gall_photos),
        # 7 Days of Summer — overlays MUST come before menu_7dl,
        # because settings/contacts/media are shown on top of menu_7dl
        # without hiding it.
        ("settings_7dl", es_items_settings_7dl),
        ("contacts_7dl", es_items_contacts_7dl),
        ("media_7dl", es_items_media_7dl),
        ("alt_preferences", es_items_alt_preferences),
        ("alt_game_menu_selector", es_items_alt_game_menu),
        ("alt_save", es_items_alt_save),
        ("alt_load", es_items_alt_load),
        ("alt_quit", es_items_alt_quit),
        ("alt_copy_saves", es_items_alt_copy_saves),
        ("alt_confirm_reload", es_items_alt_confirm_reload),
        ("menu_7dl", es_items_menu_7dl),
        # Everlasting Summer stock screens
        ("yesno_prompt", es_items_yesno),
        ("quit", es_items_quit),
        ("_gallery", es_items_gallery_image),
        ("language_menu", es_items_language_menu),
        ("sprite_menu", es_items_sprite_menu),
        ("cardgame_results", es_items_cardgame_results),
        ("license", es_items_license),
        ("support", es_items_support),
        ("main_menu", es_items_main_menu),
        ("game_menu_selector", es_items_game_menu),
        ("save", lambda s: es_items_file(s, True)),
        ("load", lambda s: es_items_file(s, False)),
        ("preferences", es_items_preferences),
        ("mods", es_items_mods),
        ("filters", es_items_filters),
        ("history", es_items_history),
        ("gallery", es_items_gallery),
        ("gallery_sp", es_items_gallery_sp),
        ("music_room", es_items_music_room),
        ("text_history_screen", es_items_text_log),
        ("help", es_items_help),
        ("choice", es_items_choice),
    ]

    def es_items_nvl_choice(nvl):
        heading, items = es_choice_items(es_scope(nvl, "items"))
        return ESMode("choice", nvl, items, u" ".join(heading) or u"Choose.")

    # Screens that change what they show without being replaced.
    ES_IDENTITY_EXTRA = {
        "sdl_achvlist_main": lambda s: id(store.sdl_achv_engine.get_cur_route()),
    }

    def es_detect():
        # Returns (identity, builder) without building the item list, so the
        # periodic check stays cheap.
        for name, builder in ES_SCREEN_MODES:
            screen = es_screen(name)
            if screen is not None:
                extra = None
                if name in ES_IDENTITY_EXTRA:
                    try:
                        extra = ES_IDENTITY_EXTRA[name](screen)
                    except Exception:
                        pass
                return (name, id(screen), extra), renpy.curry(builder)(screen)

        nvl = es_screen("nvl")
        if nvl is not None and es_scope(nvl, "items"):
            return ("nvl_choice", id(nvl)), renpy.curry(es_items_nvl_choice)(nvl)

        if getattr(store, "map_enabled", False):
            return ("map", id(getattr(store, "global_zones", None))), es_items_map

        if es_card_game_active():
            return ("cards", store.cards_state, store.cycles_left, store.changes_left, store.result_status), es_items_cards

        if not persistent.lan_chosen:
            return ("first_language",), es_items_first_language

        if es_screen("say") is not None or nvl is not None:
            return ("story",), lambda: ESMode("story", story=True)

        return ("none",), lambda: ESMode("none")

    def es_current_mode():
        try:
            return es_detect()[1]()
        except Exception:
            es_log_exc("es_current_mode")
        return ESMode("none")

    # ------------------------------------------------------------------
    # List navigation.
    # ------------------------------------------------------------------

    def _es_clamp(mode):
        idx = es.nav_index.get(mode.name, mode.start)
        if idx >= len(mode.items):
            idx = len(mode.items) - 1
        if idx < 0:
            idx = 0
        es.nav_index[mode.name] = idx
        return idx

    def es_nav_current(mode=None):
        mode = mode or es_current_mode()
        if not mode.items:
            return mode, None
        return mode, mode.items[_es_clamp(mode)]

    def es_nav_move(delta):
        mode = es_current_mode()
        if not mode.items:
            return
        idx = (_es_clamp(mode) + delta) % len(mode.items)
        es.nav_index[mode.name] = idx
        es.ui(mode.items[idx].text())

    def es_nav_jump(last):
        mode = es_current_mode()
        if not mode.items:
            return
        es.nav_index[mode.name] = len(mode.items) - 1 if last else 0
        es.ui(mode.items[es.nav_index[mode.name]].text())

    def es_nav_adjust(delta):
        mode, item = es_nav_current()
        if item is None:
            return
        if item.adjust is None:
            return es_nav_move(delta)
        try:
            return item.adjust(delta)
        except Exception:
            es_log_exc("es_nav_adjust")

    def es_nav_activate():
        mode, item = es_nav_current()
        if item is None:
            return
        if item.action is None:
            es.ui(item.text())
            return
        try:
            if not renpy.display.behavior.is_sensitive(item.action):
                es.ui(u"Unavailable.")
                return
            rv = renpy.run(item.action)
            if item.after is not None:
                item.after()
            return rv
        except renpy.game.CONTROL_EXCEPTIONS:
            raise
        except Exception:
            es_log_exc("es_nav_activate")
            es.ui(u"That did not work.")

    def es_nav_delete():
        mode, item = es_nav_current()
        if item is not None and item.delete is not None:
            if not renpy.display.behavior.is_sensitive(item.delete):
                es.ui(u"Nothing to delete.")
                return
            return renpy.run(item.delete)

    def es_nav_escape():
        mode = es_current_mode()
        if mode.escape is not None:
            return renpy.run(mode.escape)

    def es_nav_repeat():
        mode, item = es_nav_current()
        if item is not None:
            es.ui(item.text())

    def es_nav_intro():
        mode, item = es_nav_current()
        parts = [mode.intro] if mode.intro else []
        if item is not None:
            parts.append(item.text())
        es.ui(u" ".join(parts))

    def es_help_key():
        mode = es_current_mode()
        if mode.story or mode.name == "none":
            es_help_story()
        elif mode.name == "cards":
            es.ui(ES_CARD_HELP)
        else:
            es.ui(u"Up and Down arrows move, Left and Right change values, Enter selects, Escape goes back. "
                u"R repeats the current item, Home and End jump to the first and last. "
                u"In the story, F1 lists the story keys.")

    # ------------------------------------------------------------------
    # Announcements when the screen changes, checked several times a
    # second. A prompt closing returns to the item that was selected.
    # ------------------------------------------------------------------

    def es_unstick_modifiers():
        # Alt+Tab can leave SDL thinking Alt is still held, and Ren'Py then
        # ignores every plain key. Clear modifiers nobody is holding.
        try:
            _es_unstick()
        except Exception:
            if not getattr(es, "unstick_failed", False):
                es.unstick_failed = True
                es_log_exc("es_unstick_modifiers")

    def _es_unstick():
        import pygame_sdl2 as pygame
        mods = pygame.key.get_mods()
        if not mods & (pygame.KMOD_ALT | pygame.KMOD_CTRL | pygame.KMOD_SHIFT | pygame.KMOD_META):
            return
        pressed = pygame.key.get_pressed()
        held = 0
        for keys, flag in (
                ((pygame.K_LALT, pygame.K_RALT), pygame.KMOD_ALT),
                ((pygame.K_LCTRL, pygame.K_RCTRL), pygame.KMOD_CTRL),
                ((pygame.K_LSHIFT, pygame.K_RSHIFT), pygame.KMOD_SHIFT),
                ((pygame.K_LGUI, pygame.K_RGUI), pygame.KMOD_META)):
            if __builtin__.any(pressed[k] for k in keys):
                held |= mods & flag
        if held != mods & (pygame.KMOD_ALT | pygame.KMOD_CTRL | pygame.KMOD_SHIFT | pygame.KMOD_META):
            pygame.key.set_mods((mods & ~(pygame.KMOD_ALT | pygame.KMOD_CTRL | pygame.KMOD_SHIFT | pygame.KMOD_META)) | held)

    def es_tick():
        try:
            es_unstick_modifiers()
            if _preferences.self_voicing:
                # Ren'Py's own SAPI voice talks over Prism.
                _preferences.self_voicing = False
            skipping = bool(config.skipping)
            if skipping != es.last_skipping:
                es.last_skipping = skipping
                es.ui(u"Skipping." if skipping else u"Skipping stopped.")

            identity, builder = es_detect()
            if identity == es.nav_identity:
                return
            previous = es.nav_identity
            es.nav_identity = identity
            mode = builder()

            if es.just_loaded and mode.story:
                es.just_loaded = False
                es_rebuild_present()
                desc = u""
                if es.current_scene and es.current_scene not in ES_SILENT_IMAGES:
                    desc = es_describe_image(es.current_scene) or es_scene_label(es.current_scene)
                es.ui(u"Game loaded. " + desc)
                if es.last_line:
                    es.speak(es.last_line, False)
                return

            if not mode.items:
                return

            if previous is not None and identity == es.nav_previous:
                # Back from a prompt shown over this screen.
                es.nav_previous = None
                es_nav_repeat()
                return
            if mode.name in ("yesno",):
                es.nav_previous = previous
            else:
                es.nav_previous = None
            defend = ("me_defend_1", "me_defend_2")
            if not (mode.name == "cards" and getattr(es, "cards_state", None) in defend
                    and store.cards_state in defend):
                # Swapping two cards keeps the cursor where it was.
                es.nav_index[mode.name] = mode.start
            if mode.name in ("choice", "cards", "map"):
                # Queue behind the line or description that led up to it.
                mode2, item = es_nav_current(mode)
                intro = mode.intro
                if mode.name == "cards":
                    news = es_card_news()
                    if u"Choose again" in news:
                        intro = u""
                    intro = (news + u" " + intro).strip()
                text = (intro + u" " if intro else u"") + (item.text() if item else u"")
                es.speak(text, False)
                es.pending = False
            else:
                es_nav_intro()
        except Exception:
            es_log_exc("es_tick")

    def es_ensure_global_screen():
        try:
            if renpy.get_screen("es_a11y_global") is None:
                renpy.show_screen("es_a11y_global")
        except Exception:
            es_log_exc("es_ensure_global_screen")

    def es_periodic():
        es_tick()

    config.start_interact_callbacks.append(es_ensure_global_screen)
    config.periodic_callbacks.append(es_periodic)


# Kept on top in every context. Keys are only bound when the current mode
# needs them, so everything else reaches the game as usual.
screen es_a11y_global():
    zorder 2000
    $ _es_mode = es_current_mode()

    key "K_F1" action Function(es_help_key, _update_screens=False)

    if _es_mode.nav:
        key "K_UP" action Function(es_nav_move, -1, _update_screens=False)
        key "repeat_K_UP" action Function(es_nav_move, -1, _update_screens=False)
        key "K_DOWN" action Function(es_nav_move, 1, _update_screens=False)
        key "repeat_K_DOWN" action Function(es_nav_move, 1, _update_screens=False)
        key "K_LEFT" action Function(es_nav_adjust, -1)
        key "repeat_K_LEFT" action Function(es_nav_adjust, -1)
        key "K_RIGHT" action Function(es_nav_adjust, 1)
        key "repeat_K_RIGHT" action Function(es_nav_adjust, 1)
        key "K_HOME" action Function(es_nav_jump, False, _update_screens=False)
        key "K_END" action Function(es_nav_jump, True, _update_screens=False)
        key "K_RETURN" action Function(es_nav_activate)
        key "K_KP_ENTER" action Function(es_nav_activate)
        key "K_SPACE" action Function(es_nav_activate)
        key "K_DELETE" action Function(es_nav_delete)
        key "K_r" action Function(es_nav_repeat, _update_screens=False)
        if _es_mode.escape is not None:
            key "K_ESCAPE" action Function(es_nav_escape)
            key "mouseup_3" action Function(es_nav_escape)

    else:
        # Story keys work whenever no list is open, including while the game
        # shows a picture with the text window hidden.
        if _es_mode.story:
            # Left and Right would otherwise move focus onto the text box
            # buttons, so that Enter presses a button instead of advancing.
            key "K_LEFT" action NullAction()
            key "K_RIGHT" action NullAction()
        key "K_UP" action Function(es_review, -1, _update_screens=False)
        key "repeat_K_UP" action Function(es_review, -1, _update_screens=False)
        key "K_DOWN" action Function(es_review, 1, _update_screens=False)
        key "repeat_K_DOWN" action Function(es_review, 1, _update_screens=False)
        key "K_HOME" action Function(es_review_edge, False, _update_screens=False)
        key "K_END" action Function(es_review_edge, True, _update_screens=False)
        key "K_r" action Function(es_repeat, _update_screens=False)
        key "K_d" action Function(es_describe_scene, _update_screens=False)
        key "K_w" action Function(es_who, _update_screens=False)
        key "K_l" action ShowMenu("text_history_screen")

# 7 Days of Summer's quick-time event gives two seconds to press 7, too little
# for a screen reader to finish the prompt. This screen takes its place with
# the same outcome and more time.
screen es_7dl_alt_timer():
    modal True
    key "7" action [Hide("alt_timer"), Return()]
    key "K_KP7" action [Hide("alt_timer"), Return()]
    timer ES_7DL_QTE_SECONDS action [Hide("alt_timer"), SetVariable("alt_day_catapult", True), Return()]

init 1000 python:
    ES_7DL_QTE_SECONDS = 8.0
    if ("alt_timer", None) in renpy.display.screen.screens:
        renpy.display.screen.screens[("alt_timer", None)] = renpy.display.screen.screens[("es_7dl_alt_timer", None)]
