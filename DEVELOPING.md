# Everlasting Summer Access: developer notes

A drop-in Ren'Py mod for Everlasting Summer (Ren'Py 7.4, 64-bit Python 2.7). There is nothing to compile: the game loads the `.rpy` files in `game` and builds its own `.rpyc` files from them.

## Files

| Path | Purpose |
|---|---|
| `game/zz_es_a11y_core.rpy` | Speech (Prism through ctypes), settings, keys, the log and the version number (`ES_VERSION`). |
| `game/zz_es_a11y_screens.rpy` | One overlay screen, shown in every context, that works out which game screen is up and builds a keyboard list for it. The game's own screens are untouched. |
| `game/zz_es_a11y_descriptions.rpy` | Descriptions of the backgrounds and illustrations. |
| `game/prism.dll` | Prism, 64-bit only. |
| `prism_licenses/` | Prism's license and the licenses of the libraries it uses. |

To test, copy the `game` folder into the game folder as described in the README and start the game. The mod writes `es_a11y_log.txt` next to `Everlasting Summer.exe`.

Things to know:

- The game replaces `config.keymap` without some of Ren'Py's default bindings, so those defaults leak through. The mod blanks them (A, Alt+Shift+V, Shift+G, hide windows and self-voicing).
- The game overwrites the store names `min`, `type` and `map`; use `__builtin__.min` and so on.
- Ren'Py modules survive a restart (for example a language change), so hooks must unwrap themselves before wrapping again.
- Uninstalling must delete the `.rpyc` files too, or Ren'Py keeps loading them.

## Packaging and releasing

Build the release zip into `dist\EverlastingSummerAccess.zip`:

```
powershell -ExecutionPolicy Bypass -File scripts\package-release.ps1
```

To publish a release:

1. Update `ES_VERSION` in `zz_es_a11y_core.rpy`, `changes-latest.md` and `CHANGELOG.md`.
2. Build the zip.
3. Create a draft GitHub release with the zip attached:

   ```
   gh release create vX.Y.Z --draft --notes-file changes-latest.md dist\EverlastingSummerAccess.zip
   ```

4. Run the **Release** workflow from the Actions tab with the same tag. It builds the installer, writes `loadstone-release.json`, and publishes the release. Publish it as a normal release, not a pre-release: the installer only looks at the latest normal release.

The installer's package files are in `loadstone-packages`, and its settings are in `installer\profile.json`. The installer reads the package files straight from this repository, so changes to them reach players a few minutes after they're pushed.
