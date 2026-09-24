# Apple TV Discord Rich Presence

Show what you're watching in the **Apple TV desktop app** as a "Watching" activity on your Discord profile, with the title, an elapsed/progress timer, and a poster.

> Runs locally on your computer. It reads playback info from your own machine and talks to your local Discord client. Nothing is sent to any server except poster lookups (see [How it works](#how-it-works)).

## Features

- "Watching Apple TV" activity with the show or movie title
- Timer, or a progress bar when the app reports the position and duration
- Poster shown as the large image, looked up automatically from the title
- Clears the presence when you stop or close the app
- Manual title option for when the app doesn't expose what's playing
- Works on Windows and macOS

## Requirements

- Python 3.9 or newer
- Discord **desktop** app running (not the browser version)
- The Apple TV desktop app (Windows or macOS)

## Setup

### 1. Create a Discord application

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. Name it **Apple TV**. Discord shows this name as "Watching Apple TV".
3. Copy the **Application ID** from the General Information page.
4. Open `appletv_discord_rpc.py` and paste it into `CLIENT_ID`:

   ```python
   CLIENT_ID = "123456789012345678"
   ```

### 2. Install dependencies

Run this in a normal terminal (Command Prompt, PowerShell, or Terminal), **not** inside the Python `>>>` prompt.

```bash
pip install -r requirements.txt
```

If `pip` isn't recognized on Windows, use `py -m pip install -r requirements.txt`.

### 3. Turn off Discord's automatic game entry (recommended)

In Discord, go to **User Settings → Registered Games** (or **Activity Privacy → Registered Games**) and switch off the auto-detected "Apple TV" entry. Otherwise you may see two activities.

## Usage

Open the Apple TV app, then run:

```bash
python appletv_discord_rpc.py
```

On Windows you can also use `py appletv_discord_rpc.py`.

| Command | What it does |
|---|---|
| `python appletv_discord_rpc.py` | Run normally |
| `python appletv_discord_rpc.py --title "Severance S2E3"` | Use a title you type instead of auto-detecting |
| `python appletv_discord_rpc.py --list` | (Windows) List the media sessions Windows can see, for debugging |
| `python appletv_discord_rpc.py --test-art "Dark Matter"` | Test the poster lookup for a title without running Discord |

Press `Ctrl+C` to stop. The presence is cleared on exit.

## How it works

1. **Reading what's playing**
   - **Windows:** reads the system media session (the same source as the volume overlay) for an app whose ID contains "apple". If none is found, it falls back to the Apple TV window title, or to a generic "In the Apple TV app" presence.
   - **macOS:** asks the TV app for the current title, show, season, episode and position through AppleScript. You may be prompted to allow automation permissions.
2. **Finding a poster:** it searches [TVmaze](https://www.tvmaze.com/api) first, then the [iTunes Search API](https://performance-partners.apple.com/search-api), using the title text. No API keys are needed.
3. **Updating Discord:** it uses [pypresence](https://github.com/qwertyquerty/pypresence) to update your local Discord client. Updates are only sent when the title changes or you seek, to stay within Discord's rate limits.

## Limitations

- **The Apple TV app may not report what's playing.** Whether the Windows app exposes its title to the system depends on the app version. If `--list` doesn't show an Apple entry while a video is playing, use the window-title fallback or `--title`.
- **Progress and episode info** only appear when the app reports them. The window-title fallback can't provide them.
- **Poster matching is by title text**, so common titles may get the wrong poster, and some titles may not be found. If that happens the default image is kept.
- **Discord shows the large image as a square**, so tall posters are cropped slightly.
- The macOS AppleScript path is written against the TV app's scripting interface and hasn't been tested on every macOS version.

## Troubleshooting

**`pip install` says `SyntaxError` or shows `>>>`**
You're inside the Python interpreter. Type `exit()` and run the command in a normal terminal.

**`winsdk` fails to build on Windows**
`winsdk` has no prebuilt package for newer Python versions (for example 3.14) and tries to compile from source, which needs Visual Studio. Use the prebuilt `winrt-*` packages in `requirements.txt` instead. On Python 3.12, `pip install winsdk` also works.

**`ModuleNotFoundError: No module named 'winrt'`**
The dependencies aren't installed for the Python you're running. Install and run with the same launcher (`py -m pip ...` with `py script.py`).

**Nothing appears in Discord**
- Discord desktop must be running, and **Settings → Activity Privacy → Share your detected activities** must be on.
- Check that `CLIENT_ID` is correct.
- Make sure only one copy of the script is running.

**Shows the Apple TV logo instead of a poster**
Run `--test-art "Your Title"`. If it prints `No poster found`, the title didn't match a database entry. Try the show's exact name.

## Disclaimer

This is an unofficial hobby project. It is not affiliated with, endorsed by, or sponsored by Apple Inc. or Discord Inc. Apple TV and the Apple logo are trademarks of Apple Inc. Discord is a trademark of Discord Inc. Poster data comes from TVmaze and the iTunes Search API, subject to their terms.

## License

 `LICENSE`
