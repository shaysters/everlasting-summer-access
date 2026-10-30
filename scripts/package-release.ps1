# Builds the release zip into dist\EverlastingSummerAccess.zip.
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\package-release.ps1
#
# Layout: the mod's files under game\ (the installer routes them into the
# game's own game folder; by hand, that folder is merged into the game's),
# plus the README, CHANGELOG and Prism's license files at the top.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$files = @(
    "game\prism.dll",
    "game\zz_es_a11y_core.rpy",
    "game\zz_es_a11y_screens.rpy",
    "game\zz_es_a11y_descriptions.rpy",
    "README.md",
    "CHANGELOG.md",
    "prism_licenses"
)

$dist = Join-Path $root "dist"
New-Item -ItemType Directory -Path $dist -Force | Out-Null
$zip = Join-Path $dist "EverlastingSummerAccess.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }

# Write entries with forward slashes (Windows PowerShell's ZipFile writes backslashes).
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open($zip, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($entry in $files) {
        $source = Join-Path $root $entry
        if (-not (Test-Path $source)) { throw "Missing release file: $source" }
        $items = if ((Get-Item $source).PSIsContainer) { Get-ChildItem $source -Recurse -File } else { @(Get-Item $source) }
        foreach ($item in $items) {
            $name = $item.FullName.Substring($root.Length + 1).Replace([char]92, [char]47)
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $item.FullName, $name) | Out-Null
        }
    }
} finally {
    $archive.Dispose()
}
Write-Host "Built: $zip"
