"""
Fetches and caches the `exporter.py` module from the gg-web-engine project's own Blender
add-on (github.com/AndyGura/gg-web-engine, `blender-addon/gg_web_engine_exporter/exporter.py`),
so `scenes.py` can import it inside the generated Blender script instead of vendoring a copy of
its GLB+.meta export logic. That add-on's headless CLI entry point
(`blender-addon/scripts/export_cli.py`) is built the same way - its docstring explicitly says a
project that used to vendor a copy of this logic should point at `exporter.py` instead of copying
it again, which is exactly what this module does.

`exporter.py` only touches `bpy`/`rna_prop_ui` (both built into Blender) and has no relative
imports, so it can be dropped into any directory and imported standalone - no add-on
install/registration inside Blender's preferences is needed, matching how the upstream headless
CLI script itself uses it.
"""
import json
import logging
import os
import time
import urllib.error
import urllib.request

_RAW_BASE_URL = "https://raw.githubusercontent.com/AndyGura/gg-web-engine/main/blender-addon/gg_web_engine_exporter"
_EXPORTER_URL = f"{_RAW_BASE_URL}/exporter.py"

# Local cache: one directory holding a copy of exporter.py plus a small marker file recording when
# it was last checked against the URL above, so a whole batch of conversions - or repeated app runs
# within the same day - cost at most one network request, not one per file/run.
_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".nfs-resources-converter", "gg_web_engine_exporter")
_META_FILE = os.path.join(_CACHE_DIR, ".meta.json")
_EXPORTER_FILE = os.path.join(_CACHE_DIR, "exporter.py")

_CHECK_TTL_SECONDS = 24 * 60 * 60
_REQUEST_TIMEOUT_SECONDS = 5


def _read_meta() -> dict:
    try:
        with open(_META_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _write_meta(meta: dict) -> None:
    tmp_path = _META_FILE + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(meta, f)
    os.replace(tmp_path, _META_FILE)


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "nfs-resources-converter"})
    with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
        return response.read()


def ensure_gg_web_engine_exporter_installed() -> str:
    """
    Make sure a local copy of gg-web-engine's Blender `exporter.py` is available and reasonably
    fresh, downloading/updating it from the engine repo if needed. Returns the directory it lives
    in, to be added to `sys.path` by the generated Blender script, which then does
    `import exporter`.

    Never blocks a conversion on network access when a cached copy already exists and was checked
    recently: a fetch failure just logs a warning and falls back to whatever is on disk. Only
    raises if there is no cached copy at all and the fetch also failed, since there is then
    nothing usable to return.
    """
    os.makedirs(_CACHE_DIR, exist_ok=True)
    meta = _read_meta()
    has_cached_copy = os.path.isfile(_EXPORTER_FILE)
    is_stale = time.time() - meta.get("checked_at", 0) > _CHECK_TTL_SECONDS
    if has_cached_copy and not is_stale:
        return _CACHE_DIR

    try:
        exporter_source = _fetch(_EXPORTER_URL)
    except (urllib.error.URLError, OSError) as e:
        if has_cached_copy:
            logging.warning(f"Could not check gg-web-engine for exporter updates, using cached copy: {e}")
            return _CACHE_DIR
        raise RuntimeError(
            f"Failed to download the gg-web-engine Blender exporter from {_EXPORTER_URL} and no "
            "cached copy is available. Check your internet connection, or disable "
            '"Export to GG Web Engine".'
        ) from e

    previous_source = None
    if has_cached_copy:
        with open(_EXPORTER_FILE, "rb") as f:
            previous_source = f.read()
    if exporter_source != previous_source:
        tmp_path = _EXPORTER_FILE + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(exporter_source)
        os.replace(tmp_path, _EXPORTER_FILE)
        logging.info("gg-web-engine Blender exporter installed" if previous_source is None
                     else "gg-web-engine Blender exporter updated to a newer version")
    _write_meta({"checked_at": time.time()})
    return _CACHE_DIR
