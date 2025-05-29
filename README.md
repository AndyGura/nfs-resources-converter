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

## 3. GUI app (experimental)

Project provides GUI app where you can view and edit any supported resource. Edit feature is purely experimental, it 
is possible to break the file completely upon saving changes.

# Installation:

0) install python 3.9, pip, ffmpeg, blender (version 4+)
1) make sure that `blender` and `ffmpeg` commands work in terminal (cmd). If not, either fix your system environment variable PATH, or reboot your system if software was just installed, or set an absolute path to executables in [settings.py](settings.py)
2) install dependencies `pip install -r requirements.txt`

# Usage:
## Converter
`python run.py convert /media/fast/NFSSE --out /tmp/NFSSE_PARSED`

This command will recursively walk over the `/media/fast/NFSSE` directory, parse all supported resources and save them 
in common formats in the `/tmp/NFSSE_PARSED` directory. Output directory will have the same structure as input one.
Also you can point script to one file to convert single file. Check [settings.py](settings.py) to customize converter
behavior

**WARNING**: please do not set as output existing directory with some data, it can be deleted!

## GUI
`python run.py gui`

or to open some file immediately:

`python run.py gui NFSSE/SIMDATA/MISC/AL1.TRI`

**WARNING**: Script does not make backups and saved file consistency not guaranteed! Use only on copied file

## Custom commands
Custom commands are more complex scripts, which can be run on particular resource file. They are available in the GUI 
as flash icon at the top.

### *.TRI: flatten track
Makes open track fully flat. I use it for testing car acceleration/deceleration dynamics. Can be launched from GUI on TRI file, or:

`python run.py custom_command --custom-command flatten_track examples/maps/TR3.TRI --out examples/maps/flat/`

### *.TRI: reverse track

Makes track go backwards. They have a bunch of issues and glitches for now. All reversed NFSSE tracks can be found [here](https://drive.google.com/drive/folders/10nhqRrZ2Vvm6yYrIEfxjlNsltoewNTrS?usp=sharing)

`python run.py custom_command --custom-command reverse_track examples/maps/TR3.TRI --out examples/maps/reversed/`

### *.TRI: scale track

Scales track length. Does not affect road width, props etc.
Scale with factor 0.5 (make track 2x shorter):

`python run.py custom_command --custom-command scale_track --custom-command-args=0.5 /media/fast/AL1.TRI --out /media/fast/AL1_SCALED.TRI`


# Support me
You can support project by:
- giving any feedback, bug report, feature request, providing missed info about resources to [Issues](https://github.com/AndyGura/nfs-resources-converter/issues) 
- fork & submit a [Pull Request](https://github.com/AndyGura/nfs-resources-converter/pulls)
- [!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/andygura)

