The goal of this project is to implement parsers for uncommon game files and save them in widely used format. Supports a variety of files for EA games Need For Speed series 1 - 6. Right now I'm focused on The Need For Speed SE (1996) game only, however some files, like FSH, were used even in NFS HP 2 (2002)

Output files are directly used in my project [The Need For Speed Web](https://tnfsw.guraklgames.com/)

All the supported resources have an [auto-generated format specs](resources/README.md)

Feel free to contribute

<h1>Installation:</h1>

0) install python 3.9, pip, ffmpeg, blender
1) make sure that `blender` and `ffmpeg` commands work in terminal (cmd). If not, either fix your system environment variable PATH, or reboot your system if software was just installed, or set an absolute path to executables in [settings.py](settings.py)
2) install dependencies `pip install -r requirements.txt`

<h2>Features:</h2>

<h3>Converter</h3>

Converter will save parsed data to common file formats (png, txt, mp4, blend etc.)

Usage:
`python run.py convert /media/fast/NFSSE --out /tmp/NFSSE_PARSED`

**WARNING**: please do not set as output existing directory with some data, it can be deleted!

<h3>GUI resource file editor (experimental)</h3>

Opens GUI with editor of supported resource. Has ability to edit values, run custom commands if defined (check TRI files), and save file back

Usage:
`python run.py gui /media/fast/NFSSE/SIMDATA/MISC/AL1.TRI`

**WARNING**: Script does not make backups and saved file consistency not guaranteed! Use only on copied file

<h3>Custom commands</h3>

<h3>*.TRI: flatten track</h3>
Makes open track fully flat. I use it for testing car acceleration/deceleration dynamics. Can be launched from GUI on TRI file, or:

`python run.py custom_command --custom-command flatten_track examples/maps/TR3.TRI --out examples/maps/flat/`

<h3>*.TRI: reverse track</h3>

Makes track go backwards. They have a bunch of issues and glitches for now. All reversed NFSSE tracks can be found [here](https://drive.google.com/drive/folders/10nhqRrZ2Vvm6yYrIEfxjlNsltoewNTrS?usp=sharing)

`python run.py custom_command --custom-command reverse_track examples/maps/TR3.TRI --out examples/maps/reversed/`

<h2>Run tests:</h2>

`python -m unittest`

<h1>Supported resources</h1>

<h2>The Need For Speed</h2>

- **\*INFO** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/100) track settings with unknown purpose
- **\*.AS4** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/100) audio + loop settings
- **\*.ASF** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/100) audio + loop settings
- **\*.BNK** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/90) sound banks. *Some sounds are off: RX7 engine sound keeps switching left and right channel*
- **\*.CFM** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/90) car 3D model. *Some unknown info is skipped*
- **\*.DAT** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/0) binary configs
- **\*.EAS** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/100) audio + loop settings
- **\*.FAM** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/80) track textures, 3D props + auto-convert horizon to approximate spherical sky texture. *FSH issues, some props couldn't be found. Skybox positioning hardcoded and tested only for ETRACKFM/\*.FAM files.*
- **\*.FFN** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/93) bitmap font. *Exported font works, but have hardcoded line height*
- **\*.FMM** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/3) something for car interior. *Parses archive header only*
- **\*.FSH** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/98) image archive + palettes + image position on screen. *Some textures have broken transparency or wrong palette used*
- **\*.INV** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/0) some info about elements on the screen?
- **\*.PBS** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/45) car physics. *Decompression works, many values known*
- **\*.PDN** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/20) car characteristic for unknown purpose. *Decompression works, some values known*
- **\*.QFS** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/100) compressed image archive
- **\*.RPL** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/0) replay files
- **\*.TGV** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/100) video
- **\*.TRI** ![](https://us-central1-progress-markdown.cloudfunctions.net/progress/90) tracks. *Produces track, which have enough info for conversion to another game. Some data is skipped, some props are missed due to absence in FAM file*

<h1>Output file formats</h1>

- 3D models: **blend**
- archives: **directory**
- audio: **mp3**
- fonts: **fnt + png** (raster Windows Font)
- images: **png**
- info files (palette, positions, skipped resources etc.): **txt**
- metadata: **json**
- videos: **mp4**

