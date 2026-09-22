"""
Best-effort auto-detection of the `ffmpeg`/`blender` executable paths, across Windows, macOS and Linux.

Detection only ever inspects `PATH` and a handful of well-known install locations per OS/tool - it
never runs the executable. Callers (the GUI "Test" button, or `ConversionAPI.test_executable`) are
responsible for verifying the returned path actually works.
"""
import glob
import os
import shutil
import sys
from typing import List, Optional


def _first_working_candidate(candidates: List[str]) -> Optional[str]:
    """Return the first candidate that resolves via PATH or exists as a file, expanding globs."""
    for candidate in candidates:
        if not candidate:
            continue
        # Candidates without path separators are looked up on PATH (handles bare command names,
        # e.g. "ffmpeg", "ffmpeg.exe")
        if os.sep not in candidate and (not os.altsep or os.altsep not in candidate):
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
            continue

        if any(ch in candidate for ch in '*?['):
            matches = sorted(glob.glob(candidate), reverse=True)  # reverse: prefer higher version numbers
            for match in matches:
                if os.path.isfile(match) and os.access(match, os.X_OK):
                    return match
            continue

        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _ffmpeg_candidates() -> List[str]:
    candidates = ["ffmpeg"]
    if sys.platform == "win32":
        candidates += [
            "ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            os.path.expandvars(r"%ProgramFiles%\ffmpeg\bin\ffmpeg.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\ffmpeg\bin\ffmpeg.exe"),
            os.path.expandvars(r"%ChocolateyInstall%\bin\ffmpeg.exe"),
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg*\bin\ffmpeg.exe"),
        ]
    elif sys.platform == "darwin":
        candidates += [
            "/opt/homebrew/bin/ffmpeg",  # Apple Silicon Homebrew
            "/usr/local/bin/ffmpeg",  # Intel Homebrew
            "/opt/local/bin/ffmpeg",  # MacPorts
        ]
    else:
        candidates += [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/snap/bin/ffmpeg",
            "/var/lib/flatpak/exports/bin/org.freedesktop.Platform.ffmpeg-full",
        ]
    return candidates


def _blender_candidates() -> List[str]:
    candidates = ["blender"]
    if sys.platform == "win32":
        candidates += [
            "blender.exe",
            os.path.expandvars(r"%ProgramFiles%\Blender Foundation\Blender*\blender.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Blender Foundation\Blender*\blender.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender Foundation\Blender*\blender.exe"),
            r"C:\Program Files\Steam\steamapps\common\Blender\blender.exe",
        ]
    elif sys.platform == "darwin":
        candidates += [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            "/Applications/Blender/Blender.app/Contents/MacOS/Blender",
            "/Applications/Blender *.app/Contents/MacOS/Blender",
        ]
    else:
        candidates += [
            "/usr/bin/blender",
            "/usr/local/bin/blender",
            "/snap/bin/blender",
            "/var/lib/flatpak/exports/bin/org.blender.Blender",
            os.path.expanduser("~/.local/share/flatpak/exports/bin/org.blender.Blender"),
        ]
    return candidates


def detect_ffmpeg_path() -> Optional[str]:
    """Best-effort search for a working `ffmpeg` executable. Returns None if none was found."""
    return _first_working_candidate(_ffmpeg_candidates())


def detect_blender_path() -> Optional[str]:
    """Best-effort search for a working `blender` executable. Returns None if none was found."""
    return _first_working_candidate(_blender_candidates())
