The goal of this project is to implement parsers for uncommon game files and save them in widely used format. Supports a variety of files for EA games Need For Speed series 1 - 6. Right now I'm focused on The Need For Speed SE (1996) game only, however some files, like FSH, were used even in NFS HP 2 (2002)

Feel free to contribute

# 3-in-1 solution
This project, apart from file parsers themselves, provides:

## 1. Conversion of resources to common widely used format
Various kinds of game resources can be easily converted to formats:
- 3D models: **obj**, **blend**, **glb**
- archives: **directory**
- audio: **wav**
- fonts: **fnt + png** (raster Windows Font). Nice edit tool: https://snowb.org/
- images: **png**
- info files (palette, positions, skipped resources etc.): **txt**
- metadata: **json**
- videos: **mp4**

Output files are directly used in my project [The Need For Speed Web](https://tnfsw.guraklgames.com/)


## 2. Knowledge base of resource formats
At this moment, this repo contains the fullest publicly available documentation of formats, used in TNFS SE (PC version). 
The documentation is auto-generated from this repo's parsers source code

### [Observe documentation](resources/README.md)

## 3. GUI application
Project provides a full-featured GUI application where you can:
- Open and view any supported game resource file
- Edit resource files (experimental feature - use with caution)
- Convert resources to common formats with customizable settings
- Configure system settings (paths to Blender and FFmpeg executables)
- Run custom commands on specific file types

# Installation:

0) Install Python 3.9+, pip, ffmpeg, blender (version 4+)
1) Make sure that `blender` and `ffmpeg` commands work in terminal (cmd). If not, either fix your system environment variable PATH, or reboot your system if software was just installed, or set an absolute path to executables in the settings file (use `python run.py show_settings` to find its location)
2) Install dependencies `pip install -r requirements.txt`

# Usage:

## GUI Application (Main Entry Point)
```
python run.py gui
```

This command launches the GUI application, which is now the main interface for the project. The GUI provides:

- **File Management**: Open, close, save, and reload resource files
- **Resource Viewer/Editor**: View and edit the contents of supported game resource files
- **Converter**: Convert game resources to common formats with customizable settings
- **System Configuration**: Configure paths to external tools (Blender, FFmpeg)

You can also open a specific file directly:

```
python run.py gui NFSSE/SIMDATA/MISC/AL1.TRI
```

**WARNING**: The editor does not make backups and saved file consistency is not guaranteed! Use only on copied files.

## Command Line Tools
The following command line tools are still available for those who prefer terminal usage:

### Converter
```
python run.py convert /media/fast/NFSSE --out /tmp/NFSSE_PARSED
```

This command will recursively walk over the `/media/fast/NFSSE` directory, parse all supported resources and save them 
in common formats in the `/tmp/NFSSE_PARSED` directory. Output directory will have the same structure as input one.
You can also point the script to a single file to convert just that file.

**WARNING**: Please do not set as output an existing directory with important data, as it can be overwritten!

### Show Settings Location
```
python run.py show_settings
```

This command displays the full path to the settings file used by the application. The settings file is stored in your home directory.

### Custom Commands
Custom commands are more complex scripts that can be run on particular resource files. They are available in the GUI 
through the block actions menu (flash icon at the top).

#### *.TRI: flatten track
Makes open track fully flat. Useful for testing car acceleration/deceleration dynamics.

```
python run.py custom_command --custom-command flatten_track examples/maps/TR3.TRI --out examples/maps/flat/
```

#### *.TRI: reverse track
Makes track go backwards. Note that reversed tracks may have some issues and glitches.

```
python run.py custom_command --custom-command reverse_track examples/maps/TR3.TRI --out examples/maps/reversed/
```

#### *.TRI: scale track
Scales track length without affecting road width, props etc.
Scale with factor 0.5 (make track 2x shorter):

```
python run.py custom_command --custom-command scale_track --custom-command-args=0.5 /media/fast/AL1.TRI --out /media/fast/AL1_SCALED.TRI
```

# Support me
You can support project by:
- giving any feedback, bug report, feature request, providing missed info about resources to [Issues](https://github.com/AndyGura/nfs-resources-converter/issues) 
- fork & submit a [Pull Request](https://github.com/AndyGura/nfs-resources-converter/pulls)
- [!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/andygura)
