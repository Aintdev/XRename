# XRename

XRename is a Windows tool for batch-renaming TV episodes and movies with a consistent naming scheme.

## Current Version

- 1.3.5

## What It Does

- Renames TV episode files when names contain an `SxxExx` pattern.
- Renames movie files using metadata from `.nfo` files, OMDb lookup (optional), filename parsing, or manual input.
- Renames matching `.nfo` files alongside movie files.
- Stores rename history and supports undo for the latest session.
- Can install/remove a Windows context menu for quick right-click usage.
- Can check for updates when running as a compiled `.exe`.

## Supported File Types

- `.mkv`
- `.mp4`
- `.avi`
- `.avm`

## Command Line Usage

```
XRename.exe --s "C:\Path\To\Series"
XRename.exe --m "C:\Path\To\Movies"
XRename.exe --undo
XRename.exe --remove
```

Arguments:

- `--s {PATH}`: Rename series/episode files in a file or folder.
- `--m {PATH}`: Rename movie files in a file or folder.
- `--undo`: Undo the latest recorded rename session from `history.json`.
- `--remove`: Remove XRename context menu entries from the current user registry.

If the path is invalid or missing, XRename prints argument help.

## Series Mode

- Detects patterns like `s01e02` (case-insensitive).
- Builds a cleaner show title from the part before the episode token.
- Preserves the file extension.
- Asks for confirmation when more than 50 files are queued.

Example:

```
MY_SHOW.s01e02.1080p.mkv -> My Show s01e02.mkv
```

## Movie Mode

For each movie file, XRename uses this fallback order:

1. Read adjacent `.nfo` and extract IMDb ID (`tt...`) -> query OMDb.
2. Parse title/year from `.nfo` content.
3. Parse title/year from filename.
4. Ask for manual input in `Title, Year` format.

Output format:

```
Title (Year).ext
```

If a matching `.nfo` exists (`same-base-name.nfo`), it is renamed to the same `Title (Year).nfo` pattern.

## Windows Context Menu

When running as a compiled `.exe`, XRename can auto-install context menu entries under current user registry:

- `Rename Series/Episodes`
- `Rename Movie`

Registry roots:

- `HKEY_CURRENT_USER\Software\Classes\*\shell\XRename`
- `HKEY_CURRENT_USER\Software\Classes\Directory\shell\XRename`

## OMDb API Key

OMDb is optional, but recommended for best movie title/year accuracy from IMDb IDs.

- XRename stores the key in Windows Credential Manager via `keyring` (service: `xrename`, key: `omdb`).
- If no valid key is available, you can skip and continue with non-API fallbacks.
- Get a key: https://www.omdbapi.com/apikey.aspx

## Update Behavior

When running as `.exe`, XRename checks:

- Version source: `version.txt` from the GitHub repository
- Download target: latest release `XRename.exe`

If a newer version is found, XRename prompts before downloading and replacing the executable.

## Files Used by XRename

- `XRename.py`: Main source script.
- `XRename.spec`: PyInstaller spec.
- `history.json`: Rename history for undo (created automatically).
- `version.txt`: Latest version marker for updater.

## Build (PyInstaller)

```
pyinstaller XRename.spec
```

## Notes

- Create a backup before large rename batches.
- Existing target files are not overwritten.
- Windows-only features: context menu integration, credential storage behavior, and executable self-update flow.
