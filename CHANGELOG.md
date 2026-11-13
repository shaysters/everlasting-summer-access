# Changelog

## 0.10.3

- Descriptions are only read when something changes. When the game redraws the same place, or shows the same people, picture or caption again, the mod stays quiet instead of repeating it. A new place, someone arriving, a change of clothes or a new caption is still read. Press D to hear the scene again at any time.
- A content warning now appears each time you start a new 7 Days of Summer story, since it has none of its own: it covers disturbing violence, blood and death, frightening scenes, mentions of suicide, sexual assault and abuse, and drinking and smoking. Continue starts the story; Back to the menu returns.
- Captions that run over two lines are read as one sentence, without a full stop in the middle.

## 0.10.2

- Save and load slots read the date cleanly. Before, the month came out with a stray code in front of it, such as "{#month}November".

## 0.10.1

- 7 Days of Summer's camp maps work: the places you can go are listed, with who is there and any heart-puzzle piece, and Enter takes you there and carries on the story. Before, its maps weren't recognised at all. Thanks to Douglas G for finding and reporting this.
- 7 Days of Summer's noir chapters: their game menu now returns to the main menu properly, and settings opens the right screen.
- 7 Days of Summer's own save and load screens (when it's set to start with the game) now change between its own save pages.
- During a 7 Days of Summer replay, settings has End the replay.
- P reads 7 Days of Summer's points and music widgets when they're turned on.
- The statistics page 7 Days of Summer unlocks at the end is read in full, with ending and route names.
- Typing a 7 Days of Summer cheat code is no longer interrupted by the mod's own letter keys.

## 0.10.0

- Support for the 7 Days of Summer (7DS:LA) mod, added by Douglas G: its main menu, settings, contacts, media, save and load, game menu and quit prompts, the Stories section (fan fiction, old endings and unreleased material) and its gallery are all read.
- The card game is also read in 7 Days of Summer's tournament, where your opponent can be one of several kinds of player.
- 7 Days of Summer fixes and additions: the opening hero choice (Loki, Herc, Drisch and the hidden Major), the bonus story's act choice, its first-run and update notices (now read in full, and OK closes them), the warning when loading a save from an older version, the music player, the Moments replays, day and chapter titles, and lines it shows as on-screen text.
- Written descriptions of 7 Days of Summer's backgrounds and illustrations: about 800 pictures, covering all 1,000 or so it shows.
- 7 Days of Summer's endings list (its achievements) is fully readable: routes, endings by name, which you have, what locked ones need, and replaying them, including the replay settings screen.
- The "Achievement unlocked" banners 7 Days of Summer shows at its endings are read, with their titles in English.
- 7 Days of Summer minigames: the card tournament table is read with D, rock-paper-scissors throws are announced, and the quick-time event gives 8 seconds instead of 2.
- 7 Days of Summer's opening video is described, with Skip.
- Text the game shows on screen as captions is now read starting with "Caption:".
- Supports both versions of 7 Days of Summer: the English translation (Workshop item 3010995687) and the Russian original. With the English one, the endings list and ending banners use the translators' own English titles.
- Works around 7 Days of Summer replacing some of Python's built-in names, which would otherwise break the save and load menus.
- The README has a new 7 Days of Summer section, including why its routes guide matters.

## 0.9.2

- When the main menu has been read, the mod tells you if a newer version is out. Run the installer to update. R repeats the message until the story starts.

## 0.9.1

- New standalone installer, **EverlastingSummerAccessInstaller.exe**. It finds your Steam copy of the game, installs, updates and uninstalls the mod, and removes the older Tolk mod's files. It replaces install.ps1.
- The download zip now holds the mod's files in a `game` folder, ready to merge into the game's folder for a manual install.

## 0.9.0

First test release.

- Speech through Prism (NVDA, JAWS, other screen readers, or Windows speech), replacing the older Tolk mod. Ships the 64-bit Prism only.
- Reads dialogue with speaker names, choices (marking ones chosen before), and every menu: main menu, game menu, save and load, settings, language, gallery, sprite viewer, music room, endings, mods, filters, text log and prompts.
- About 400 written descriptions of backgrounds, illustrations and intro scenes. Announces characters arriving and leaving, outfit changes, and optionally facial expressions.
- The camp map lists where you can go, who is there and where you've been.
- The card game reads your hand, which card your opponent wants, and which cards you gave away and received.
- Lines that are only "..." are read as "ellipsis".
- Story keys (D to describe the scene, W for who's in view, R to repeat, Up and Down to review, L for the text log) also work while a picture is shown with no text.
- Switches off engine shortcuts a screen reader user can't use and that would leave them stuck: A (Ren'Py's own accessibility menu), H (hide the text window), Alt+Shift+V and Shift+G. Ren'Py's own Windows-speech self-voicing is kept off.
- Clears a stuck Alt key after Alt+Tab.
