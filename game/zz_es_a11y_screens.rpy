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

    ES_PAGES = ["auto"] + [str(i) for i in range(1, 10)]

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
        for i in range(1, 13):
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
            for lbl, name in sorted(store.mods.iteritems()):
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
        for name, track in sorted(music_box.iteritems()):
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
        names = [n for n in ES_ZONE_ORDER if n in zones] + sorted(n for n in zones if n not in ES_ZONE_ORDER)
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
            if state in ("me_defend_1", "me_defend_2", "me_select_1", "me_select_2", "results"):
                return True
            if state == "rival_select" and isinstance(store.rival, CardGameRivalUs):
                return True
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
        for value, count in sorted(counts.items(), key=lambda kv: -kv[1]):
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
        gained = [k for k in counts for n in range(counts[k] - old.get(k, 0))]
        lost = [k for k in old for n in range(old[k] - counts.get(k, 0))]
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
    # Working out the current mode.
    # ------------------------------------------------------------------

    ES_SCREEN_MODES = [
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

    def es_detect():
        # Returns (identity, builder) without building the item list, so the
        # periodic check stays cheap.
        for name, builder in ES_SCREEN_MODES:
            screen = es_screen(name)
            if screen is not None:
                return (name, id(screen)), renpy.curry(builder)(screen)

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
            if any(pressed[k] for k in keys):
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
