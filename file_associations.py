# Single source of truth for supported NFS file extensions and their human-readable names.
#
# Every platform-specific build configuration (macOS bundle document types, Windows installer
# registry associations, Linux MIME database + .desktop entry) is derived from this list.
# Add or edit a supported extension here and regenerate the build configs with
# `python generate_build_configs.py` to keep all platforms in sync.
#
# Each entry:
#   - extension: lowercase file extension without the leading dot (e.g. "fsh")
#   - name:      human-readable description shown to the user (e.g. "FSH Image Archive File")

FILE_ASSOCIATIONS = [
    # {"extension": "as4", "name": "AS4 Audio File"},
    # {"extension": "asf", "name": "ASF Audio File"},
    # {"extension": "bnk", "name": "BNK Sound Bank File"},
    # {"extension": "cfm", "name": "CFM Car 3D Model File"},
    # {"extension": "col", "name": "COL Track Data File"},
    # {"extension": "eas", "name": "EAS Audio File"},
    # {"extension": "env", "name": "ENV Image Archive File"},
    # {"extension": "fam", "name": "FAM Archive File"},
    {"extension": "ffn", "name": "FFN Bitmap Font File"},
    # {"extension": "frd", "name": "FRD Track File"},
    {"extension": "fsh", "name": "FSH Image Archive File"},
    # {"extension": "geo", "name": "GEO Car 3D Model File"},
    # {"extension": "msk", "name": "MSK Archive File"},
    # {"extension": "pbs", "name": "PBS Car Physics File"},
    # {"extension": "pdn", "name": "PDN Car Characteristic File"},
    # {"extension": "qfs", "name": "QFS Compressed Image Archive File"},
    # {"extension": "tgv", "name": "TGV Video File"},
    # {"extension": "tri", "name": "TRI Track File"},
    # {"extension": "trk", "name": "TRK Track File"},
    # {"extension": "uv", "name": "UV Video File"},
    # {"extension": "viv", "name": "VIV Archive File"},
    # {"extension": "crp", "name": "CRP Geometry File"},
]


def mime_type(ext: str) -> str:
    return f"application/x-{ext}"


def prog_id(ext: str) -> str:
    return f"NFSResourcesConverter.{ext}"
