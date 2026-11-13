# Everlasting Summer Access

Everlasting Summer Access is a mod that makes Everlasting Summer, the visual novel by Soviet Games, playable with a screen reader. It reads dialogue, choices and every menu, and guides you through the camp map and the card game. It also describes every background and illustration, and tells you when characters arrive or leave.

It works with NVDA, JAWS and other Windows screen readers, and falls back to Windows' built-in voices if no screen reader is running. You play with the keyboard.

- Join the Discord to chat, get help or report problems: <https://discord.gg/KNDXhztGGK>
- Support shaysters on Ko-fi: <https://ko-fi.com/shaysters>

## Requirements

- Everlasting Summer for Windows, from Steam: <https://store.steampowered.com/app/331470/Everlasting_Summer/>
- A screen reader such as NVDA or JAWS (optional; without one, the mod uses Windows' built-in speech).

## Installing

1. Close Everlasting Summer if it's running.
2. Download **EverlastingSummerAccessInstaller.exe** from the [latest release](https://github.com/shaysters/everlasting-summer-access/releases/latest).
3. Run it. It finds your Steam copy of Everlasting Summer by itself. If it can't, use the Browse button next to the game folder and choose the folder that contains `Everlasting Summer.exe`.
4. Choose **Install**.
5. Start Everlasting Summer from Steam as usual. The mod starts speaking straight away.

If the installer won't start and mentions `VCRUNTIME140.dll`, install the [Microsoft Visual C++ Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe) and try again.

The first time you start the game it asks for a language. The mod reads the list; choose English with Enter. The game then shows its license (Up and Down to read it, Enter on "Yes" to accept) and a disclaimer, which the mod reads. Press Enter to continue past the disclaimer; the game shows it every time it starts.

### Updating and uninstalling

Keep the installer. Run it again to update to the newest version, or to uninstall. Close the game first. The installer says on its first page when an update is available, and the mod tells you too, once the main menu has been read.

### Installing by hand

If you'd rather not use the installer, download **EverlastingSummerAccess.zip** from the same release and extract it anywhere. Copy the `game` folder from it into the game's folder, the one that contains `Everlasting Summer.exe`, and let it merge with the game's own `game` folder. On a default Steam install that's:

```
C:\Program Files (x86)\Steam\steamapps\common\Everlasting Summer
```

To uninstall a manual install, delete these files from the game's `game` folder: `prism.dll`, and every file starting with `zz_es_a11y_` (the `.rpy` files and the `.rpyc` files the game makes from them). The mod doesn't change any of the game's own files.

### Upgrading from the older Tolk mod

An earlier version of this mod used Tolk. The two can't be installed together. The installer removes the old files for you. If you install by hand, first delete these from the game's `game` folder: `zz_everlasting_summer_tolk_tts.rpy`, `zz_everlasting_summer_tolk_tts.rpyc`, `Tolk32.dll`, `Tolk64.dll`, `nvdaControllerClient32.dll` and `nvdaControllerClient64.dll`.

## Keys

| Key | Where | What it does |
|---|---|---|
| Enter or Space | Story | Continue to the next line. |
| Up and Down | Story | Review earlier lines, one at a time. |
| Home and End | Story | Jump to the oldest or newest line in the review. |
| R | Story | Repeat the last line. |
| D | Story | Describe the scene, and say who is in view. In 7 Days of Summer's card tournament, also read the tournament table. |
| W | Story | Say who is in view. |
| L | Story | Open the text log. |
| P | Story, 7 Days of Summer | Read 7 Days of Summer's on-screen widgets: your role, karma and points with each character, and the music playing. Turn them on in its settings (Widget (LP) and Widget (music)). |
| Tab | Story | Turn skipping on or off. Hold Ctrl to skip only while held. |
| Page Up | Story | Roll back to the previous line. |
| Escape | Story | Open the game menu. |
| Up and Down | Menus, choices, map, card game | Move between options. |
| Left and Right | Menus | Change a value: volume, text speed, save page, on and off settings. |
| Enter or Space | Menus, choices, map, card game | Select. |
| Home and End | Menus, choices, map, card game | Jump to the first or last option. |
| R | Menus, choices, map, card game | Repeat the current option. |
| Escape | Menus | Go back. |
| Delete | Save and load | Delete the save in the selected slot. |
| F1 | Everywhere | List the keys. In the card game, explain the rules. |

Notes:

- The story keys (D, W, R, Up and Down, L) also work while the game shows a picture with no text on screen.
- The mod switches off game and engine shortcuts that a screen reader user can't use and that would leave you stuck: H (hide the text window), A (Ren'Py's own accessibility menu), Shift+G (graphics renderer menu), and Ren'Py's own self-voicing, which talks over your screen reader with Windows speech.
- Choices you picked in an earlier playthrough say "chosen before".
- A line that is only "..." is read as "ellipsis", so you know someone said nothing.
- In the save and load menus, Enter on a slot saves or loads straight away. The game asks before overwriting, loading over unsaved progress, or deleting.
- On the camp map, each place says who is there and whether you've been there already.
- In the card game, the mod tells you which of your cards your opponent wants, and which cards you gave away and received after each exchange. The list also has your whole hand, with any pairs, threes and fours.
- Footnotes the game shows on screen, such as "Sovyonok means Owlet", are read as notes.

## 7 Days of Summer

7 Days of Summer (7DS:LA) is a large fan-made mod for Everlasting Summer, free on the Steam Workshop. It comes in two versions, and this mod supports both:

- **English:** <https://steamcommunity.com/sharedfiles/filedetails/?id=3010995687>. A community translation of the whole story, apart from some bonus content in the Old Road section (fan fiction and cut scenes). This is the one to get if you play in English.
- **Russian (the original):** <https://steamcommunity.com/sharedfiles/filedetails/?id=441054187>. A little newer, with a bonus story the English version doesn't have yet.

Subscribe to only one of them. The two can't be installed together: the game shows an error and won't start. If you switch, unsubscribe from the other first. Subscribe on Steam and it loads with the game; open it from the game's mods list.

**Content warning:** 7 Days of Summer is written for adults and has no warning of its own, so the mod shows one each time you start a new 7 Days of Summer story. Some routes contain disturbing violence, blood, death and murder, and frightening scenes, with mentions of suicide, sexual assault and abuse, and plenty of drinking and smoking. Choose Continue to start the story or Back to the menu.

This mod covers all of it:

- its main menu, settings, contacts, media, save and load, game menu and quit prompts
- the opening choice of hero (Loki, Herc or Drisch, and later the Major), and in the Russian version the bonus story's choice of act
- the opening video, described line by line, with Skip
- its notices and changelog, read in full, and the warning when you load a save from an older version
- the Stories section: the Moments replays, and the Old Road's fan fiction, old endings and unreleased material
- the endings list (its achievements): every route and ending by name, which you have, what a locked one needs, and Enter to replay one you've reached, including the settings it asks for first
- its camp maps: the places you can go, who is there, and Enter to go there
- its noir chapters, which use their own dialogue, choice and game menu screens
- its own save and load screens, when it's set to start with the game
- ending a replay: press Escape during one and choose End the replay
- the statistics page you unlock by finishing it
- the points and music widgets (press P)
- cheat codes: press the tilde key in its main menu and type the code; the mod stays quiet while you type
- the gallery and the music player
- day and chapter titles, lines it shows as text on screen (read as "Caption:"), and the "Achievement unlocked" banner when you reach an ending
- descriptions of all its backgrounds and illustrations, like the original game's

Its minigames:

- **Card tournament:** played just like the original game's card game. While the tournament table is on screen, press D to hear who plays whom and who won.
- **Rock, paper, scissors:** plays itself; the mod says what you and your opponent threw.
- **Rhyming with Miku:** an ordinary choice menu.
- **Quick-time event** (in one of the Old Road's old endings): press Enter or 7 when told. The mod gives you 8 seconds instead of the original 2.

In the Russian version the story is in Russian, and the mod reads it as written, so you'll need a Russian voice or a translation add-on for your screen reader. The mod's own menus, endings list and descriptions are in English with either version.

Follow the routes guide that 7 Days of Summer provides. Its routes are meant to be played in a set order, because the story follows a chronology: later routes build on events and reveals from earlier ones. Playing them out of order can spoil the story or leave parts of it confusing.

## Settings

The mod's settings are near the end of the game's own **Settings** menu (main menu, or Escape then Settings). Use Up and Down to move, and Enter or Left and Right to turn a setting on or off. Changes are saved immediately.

- **Describe scenes** (on by default): read a description of each background and illustration when it appears. A description is only read when the picture changes, not when the game redraws the same place; press D to hear it again.
- **Announce characters arriving and leaving** (on by default): also says when a character changes clothes, for example into a swimsuit.
- **Announce facial expressions** (off by default): say when a character's expression changes, for example "Alisa: smiling."
- **Read speaker names** (on by default): read who is speaking before each line.
- **Read footnotes** (on by default): read the game's pop-up footnotes.

The mod's menus and descriptions are in English. The story and choices follow the game's language setting.

## Troubleshooting

The mod keeps a log next to `Everlasting Summer.exe`:

```
C:\Program Files (x86)\Steam\steamapps\common\Everlasting Summer\es_a11y_log.txt
```

It says which speech output Prism found. If something goes wrong, include the log when you report it.

- **No speech at all:** make sure `prism.dll` and the `zz_es_a11y_` files are in the game's `game` folder, not the folder above it, and that the game was started after installing.
- **No speech, and the log mentions 32-bit:** start the game from Steam or with `Everlasting Summer.exe`. The mod only supports the 64-bit game, not `Everlasting Summer-32.exe`.
- **Keys stop working after Alt+Tab:** switch back to the game and press a key once more; the mod clears a stuck Alt key by itself within a moment. If it still doesn't respond, press Escape to open the game menu and Escape again to return.
- **A second voice (Windows speech) talks about self-voicing or the clipboard:** that is Ren'Py's own speech feature. The mod turns it off, so restarting the game with the current version stops it.
- **The game shows an error when it starts:** check for files left over from the older Tolk mod (see above) and delete them.

To report a problem or suggest something, open an issue on the [GitHub page](https://github.com/shaysters/everlasting-summer-access/issues).

## Credits

The mod's code, including the rewrite from the older Tolk mod and its fixes, was written by Claude, Anthropic's AI model, in Claude Code. The image descriptions were written by Claude too.

Douglas G added support for the 7 Days of Summer mod, including its extra stories, fan fiction and unreleased material.

The installer is built with [Loadstone](https://github.com/bradjrenshaw/loadstone) by [Bradley Renshaw](https://github.com/bradjrenshaw).

Speech is provided by [Prism](https://github.com/ethindp/prism) by Ethin Probst, under the MPL-2.0 license. Its license files are in the `prism_licenses` folder.

Everlasting Summer is made by Soviet Games. This mod isn't affiliated with or endorsed by Soviet Games.

## For developers

Release instructions are in [DEVELOPING.md](DEVELOPING.md).
