<p align="center">
  <img src="icons/tailslab-256.png" alt="TailsLab logo" width="160" />
</p>

<h1 align="center">TailsLab</h1>

<p align="center">
  <b>A growing library of reverse-engineered old game file formats, with an editor, a converter and specs for each.</b><br/>
  <i>Formerly known as <b>NFS Resources Converter</b>.</i>
</p>

---

TailsLab is a library of file formats from old games, reverse-engineered one by one and described down to the
byte. Every format in the library can be opened and edited in a desktop editor, converted to formats any modern tool
opens, and read as a precise specification to build your own tools on. Files outside the library are not supported:
TailsLab does not guess unknown formats.

Right now the lab works on **EA's Need for Speed series 1 to 9**, from The Need for Speed (1994) to NFS Most Wanted
(2005). Many EA Canada formats (FSH images, FFN fonts, QFS compression...) are shared across other EA titles of that
era too.

## Why TailsLab

- 📖 **Every format is documented, and the documentation is the parser.** Each file format is described once, in
  Python. That one description reads the file, writes it back, drives the editor and generates the
  [format specs](resources/README.md). The docs can't drift away from the code, because they are the code.
- 🛠️ **A modding tool.** Open a game file, change it, save it, play it. The game reads it back, byte-exact where you
  changed nothing.
- 🧩 **Or build your own tools.** The specs are complete enough to write a parser from them alone, in any language.
  AI agents can do it too: point one at a spec and it writes a working reader.
- 🔄 **A converter.** Get the game's content out in widely used formats, in bulk or one file at a time.

## The editor

Full featured editors, made for the format:

| Format | What you get |
|---|---|
| **FSH / QFS** image archives | View, replace, add and export images, palettes, hot spots; import a PNG folder back; convert to 8-bit; DXT textures (NFS6) |
| **FFN** bitmap fonts | Glyphs, kerning pairs and the font bitmap, with live glyph and text previews; export to fnt + png and back |
| **PBS / PDN** TNFS car specs | Car physics and AI on charts: torque and power, gearing, grip, brakes, top speed, corner slowdown |

And more is coming down the road. Rich viewers are already there for 3D cars and tracks of most games, TNFS track
maps, sound banks and audio.

Every other supported file opens in the **generic editor**, built automatically from the format description: a tree
of every field with its description, editable in place. It might or might not be enough for what you want to do, but
you always see the whole file.

## Games and formats

| Game | Highlights |
|---|---|
| **The Need for Speed** (SE PC, 3DO) | Cars (CFM), tracks (TRI, FAM), car specs (PBS, PDN, 3DO BigSpecsFam), images (FSH, QFS), fonts (FFN), audio (BNK, ASF, EAS), videos (TGV), replays (RPL), saved config |
| **NFS II / II SE** | Cars (GEO), tracks (TRK, COL), archives (VIV, MSK), images, fonts, sound banks, videos (UV) |
| **NFS III Hot Pursuit** | Cars (FCE in VIV), tracks (FRD, COL), images, fonts, sound banks |
| **NFS High Stakes** | Cars (FCE4), tracks (FRD), images, fonts, sound banks |
| **NFS Porsche Unleashed** | Cars and tracks (CRP), images (FSH, ENV), fonts, sound banks |
| **NFS Hot Pursuit 2** | Cars with their skins, tracks and race routes, DXT images, fonts, sound banks |
| **NFS Underground / Underground 2 / Most Wanted** | City maps (Olympic City, Bayview, Rockport), car models, texture packs |

The full list, with every field of every format, is in the [file specs](resources/README.md). Coverage differs
from file to file; if something you need is missing or wrong, [open an issue](https://github.com/AndyGura/nfs-resources-converter/issues).

## Conversion

| Content | Output |
|---|---|
| 3D models, tracks | **obj**, **blend**, **glb** |
| Images | **png** |
| Fonts | **fnt + png** (edit them with e.g. [SnowB](https://snowb.org/)) |
| Audio | **wav** |
| Videos | **mp4** |
| Archives | a **directory** of converted items |
| Metadata, palettes, settings | **json**, **txt** |

The output feeds [The Need For Speed Web](https://tnfsw.guraklgames.com/), a browser remake of TNFS.

# Installation

Converting audio and video needs `ffmpeg`, converting 3D models needs `blender` (version 4+). Set their paths in the
app's System Configuration if they are not on your `PATH`.

### Windows and macOS

Download the installer (`tailslab-windows-setup-<version>.exe` or `tailslab-macos-<version>.dmg`) from the
[Releases page](https://github.com/AndyGura/nfs-resources-converter/releases). The Windows installer also sets up
file associations (`*.fsh`, `*.qfs`, `*.ffn`, `*.pbs`, `*.pdn`...).

The builds are unsigned, so the system warns you the first time:

- **Windows (SmartScreen)**: click **More info**, then **Run anyway**.
- **macOS (Gatekeeper)**: in **Finder**, right-click the app and choose **Open**, then **Open** again. If it is still
  blocked, go to **System Settings > Privacy & Security** and click **Open Anyway**.

The app runs in a native web view (WebView2 on Windows, WebKit on macOS): no browser needed.

### From source (Linux, or anyone who wants the latest)

1. Install Python 3.14 and pip.
2. `pip install -r requirements.txt`
3. `python run.py`

On Linux the GUI opens in a Chrome / Chromium app window, so one of them needs to be installed. A pre-built Linux
binary is not available yet: the standalone build fails to launch, and help with it is very welcome.

# Usage

## GUI

```bash
python run.py                                  # or the installed app
python run.py NFSSE/SIMDATA/MISC/AL1.TRI       # open a file directly
```

**WARNING**: the editor does not make backups. Work on copies of your game files.

## Command line

Commands below use `python run.py`; the installed app's executable takes the same arguments.

### Convert

```bash
python run.py convert /media/fast/NFSSE --out /tmp/NFSSE_PARSED
```

Walks the input directory recursively, converts every supported file and writes the result to the output directory
with the same structure. The input can also be a single file. **Don't point the output at a directory with data you
care about**: it can be overwritten.

Conversion settings come from the settings file: the default ones (the `[Conversion]` section, "No preset" in the GUI
converter), or a user-defined preset created in the GUI converter. A preset also keeps input and output paths, used
when the command doesn't give them:

```bash
python run.py convert --preset "My Preset"
python run.py convert /media/fast/NFSSE --out /tmp/NFSSE_PARSED --preset "My Preset"
```

A preset is a `[Conversion: <name>]` section of the settings file. Its name has letters, digits, spaces, `-`, `_` and
`.` only; quote it if it has spaces.

### Show settings location

```bash
python run.py show_settings
```

Prints the path of the settings file (in your home directory) and the names of the conversion presets.

### Uncompress

```bash
python run.py uncompress /path/to/compressed/file.qfs
```

Writes the uncompressed data next to the original, with `_uncompressed` appended (`AL1.QFS` becomes
`AL1.QFS_uncompressed`).

### Custom commands

Scripts for particular file types, also available in the GUI from the block actions menu (flash icon at the top).

```bash
# TNFS *.TRI: make an open track fully flat (handy for testing acceleration)
python run.py custom_command --custom-command flatten_track examples/maps/TR3.TRI --out examples/maps/flat/

# TNFS *.TRI: make a track go backwards (may have glitches)
python run.py custom_command --custom-command reverse_track examples/maps/TR3.TRI --out examples/maps/reversed/

# TNFS *.TRI: scale track length without touching road width, props etc.
python run.py custom_command --custom-command scale_track --custom-command-args=0.5 /media/fast/AL1.TRI --out /media/fast/AL1_SCALED.TRI
```

# Development

Python tests: `python -m unittest`. Frontend (Angular, in `frontend/`): `npm install`, then
`npm run test -- --watch=false --browsers=ChromeHeadless`.

### Debugging the Angular frontend

The JavaScript ⟷ Python bridge (`window.pywebview.api`) only exists inside the app's native window, so development
mode points that window at the Angular dev server: live reload, source maps and DevTools, talking to the real backend.

1. Once: `cd frontend && npm install`.
2. Start the dev server from `frontend`: `npm run start`. It serves `http://localhost:4200` and its `proxy.conf.json`
   forwards `/eel.js` (the bridge shim) and `/resources` (serialized previews) to `http://127.0.0.1:8000`.
3. In another terminal, from the project root: `python run.py --dev` (optionally with a file to open, and
   `--dev-server http://localhost:4200` if you changed the port). It opens the native window with developer tools
   enabled and serves the shim and the previews on port `8000`.
4. Right-click in the window and choose **Inspect Element** for DevTools. Frontend edits reload instantly; Python
   edits need a restart of `python run.py --dev`.

**On Linux** the GUI runs on Eel (a Chrome app window) instead. In `--dev` mode it opens no window at all, only the
backend on port `8000`: open `http://localhost:4200` in a normal browser tab and use its DevTools.

# Contributing and support

- Feedback, bug reports, feature requests and anything you know about these formats:
  [Issues](https://github.com/AndyGura/nfs-resources-converter/issues)
- Fork and send a [Pull Request](https://github.com/AndyGura/nfs-resources-converter/pulls)
- [!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/andygura)
