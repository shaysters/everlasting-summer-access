# Installs the Everlasting Summer accessibility mod into the Steam game folder.
# Files from the older Tolk-based mod are moved to old_tolk_mod_backup in a
# "<this folder>_backup" folder beside this one, because the two mods would
# fight over the same keys.
param(
    [string]$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\Everlasting Summer"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $GameDir "game"
if (-not (Test-Path (Join-Path $target "screens.rpyc"))) {
    throw "Everlasting Summer not found at $GameDir"
}

$old = @(
    "zz_everlasting_summer_tolk_tts.rpy", "zz_everlasting_summer_tolk_tts.rpyc",
    "Tolk32.dll", "Tolk64.dll", "nvdaControllerClient32.dll", "nvdaControllerClient64.dll",
    "es_tts_debug.log"
)
$backup = Join-Path ($here + "_backup") "old_tolk_mod_backup"
foreach ($name in $old) {
    $path = Join-Path $target $name
    if (Test-Path $path) {
        New-Item -ItemType Directory -Force $backup | Out-Null
        Move-Item -Force $path (Join-Path $backup $name)
        Write-Output "Moved old mod file $name to $backup"
    }
}

# Earlier builds of this mod kept Prism in a subfolder.
$oldPrism = Join-Path $target "es_a11y_prism"
if (Test-Path $oldPrism) { Remove-Item -Recurse -Force $oldPrism }

Copy-Item -Recurse -Force (Join-Path $here "game\*") $target
# Test-only switches must never ship.
foreach ($flag in "es_a11y_mute.txt", "es_a11y_debug.txt") {
    $path = Join-Path $target $flag
    if (Test-Path $path) { Remove-Item -Force $path }
}
Write-Output "Installed to $target"
