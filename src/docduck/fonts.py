"""Font management: discover system fonts, ensure variety across a batch."""

import os
import random
import subprocess
from functools import lru_cache
from pathlib import Path


def _auto_register_docduck_fonts() -> None:
    """If the user has run `docduck-fonts` (downloader) and a `./fonts/` or
    `$DOCDUCK_FONTS_DIR` directory exists, point fontconfig at it for this
    process. Idempotent: no-op if FONTCONFIG_FILE is already set or neither
    location exists.
    """
    if os.environ.get("FONTCONFIG_FILE"):
        return
    candidates = []
    override = os.environ.get("DOCDUCK_FONTS_DIR")
    if override:
        candidates.append(Path(override))
    candidates.append(Path.cwd() / "fonts")
    cfg = Path.home() / ".cache" / "docduck" / "fontconfig.conf"
    for font_dir in candidates:
        if font_dir.is_dir() and cfg.exists():
            os.environ["FONTCONFIG_FILE"] = str(cfg)
            return


_auto_register_docduck_fonts()

# Fonts that look broken or inappropriate for document rendering
_FONT_BLOCKLIST = {
    ".LastResort",
    ".Keyboard",
    "Apple Symbols",
    "Apple Color Emoji",
    ".Apple Color Emoji UI",
    "Wingdings",
    "Wingdings 2",
    "Wingdings 3",
    "Webdings",
    "Zapf Dingbats",
    "Symbol",
}

# Font name substrings that indicate weight/width variants Pango can't resolve cleanly
_VARIANT_BLOCKLIST = [
    "condensed",
    "compressed",
    "narrow",
    "black",
    "heavy",
    "ultra light",
    "ultra",
    "thin",
    "light oblique",
    "book oblique",
    "black oblique",
]


@lru_cache(maxsize=32)
def get_system_fonts(lang="en"):
    """Discover available font families for a language, categorized by style.

    Uses fc-list :lang=<code> to only include fonts that actually cover
    the target script's Unicode range. Falls back to all fonts on error.
    """
    try:
        result = subprocess.run(
            ["fc-list", f":lang={lang}", "--format", "%{family}|%{style}|%{file}\n"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = result.stdout.strip().split("\n")
    except Exception:
        return _fallback_fonts()

    serif = set()
    sans = set()
    mono = set()
    all_fonts = set()

    for line in lines:
        parts = line.split("|")
        if len(parts) < 2:
            continue
        families = [f.strip() for f in parts[0].split(",")]
        fpath = parts[2] if len(parts) > 2 else ""

        for family in families:
            if not family or len(family) < 2:
                continue
            if family in _FONT_BLOCKLIST or family.startswith("."):
                continue
            if any(v in family.lower() for v in _VARIANT_BLOCKLIST):
                continue

            all_fonts.add(family)
            fl = family.lower()
            fp = fpath.lower()

            if any(
                k in fl or k in fp for k in ["mono", "courier", "console", "fixed", "typewriter"]
            ):
                mono.add(family)
            elif any(
                k in fl or k in fp
                for k in [
                    "serif",
                    "roman",
                    "times",
                    "georgia",
                    "garamond",
                    "palatino",
                    "bookman",
                    "charter",
                    "nimbus roman",
                    "cambria",
                    "athelas",
                    "iowan",
                    "cochin",
                    "baskerville",
                    "caslon",
                    # Popular Google Fonts serifs whose names don't include "serif"
                    "merriweather",
                    "playfair",
                    "crimson",
                    "lora",
                    "eb garamond",
                    "cormorant",
                    "libre",
                    "spectral",
                    "source serif",
                    "amiri",  # Arabic serif
                    "davidlibre",
                    "noto serif",
                ]
            ):
                if "sans" not in fl:
                    serif.add(family)
                else:
                    sans.add(family)
            elif any(
                k in fl or k in fp
                for k in [
                    "sans",
                    "gothic",
                    "arial",
                    "helvetica",
                    "verdana",
                    "calibri",
                    "tahoma",
                    "avenir",
                    "futura",
                    "gill",
                    "optima",
                    "lucida grande",
                    # Popular Google Fonts sans-serifs
                    "roboto",
                    "open sans",
                    "opensans",
                    "lato",
                    "inter",
                    "montserrat",
                    "poppins",
                    "work sans",
                    "nunito",
                    "rubik",
                    "cairo",
                    "tajawal",
                    "hind",
                    "sarabun",
                    "heebo",
                    "ptsans",
                    "pt sans",
                ]
            ):
                sans.add(family)

    if len(serif) < 2:
        serif.update(["DejaVu Serif", "Liberation Serif", "FreeSerif"])
    if len(sans) < 2:
        sans.update(["DejaVu Sans", "Liberation Sans", "FreeSans"])
    if len(mono) < 2:
        mono.update(["DejaVu Sans Mono", "Liberation Mono", "FreeMono"])

    return {
        "serif": sorted(serif),
        "sans": sorted(sans),
        "mono": sorted(mono),
        "all": sorted(all_fonts),
    }


def _fallback_fonts():
    return {
        "serif": ["DejaVu Serif", "Liberation Serif", "FreeSerif"],
        "sans": ["DejaVu Sans", "Liberation Sans", "FreeSans"],
        "mono": ["DejaVu Sans Mono", "Liberation Mono", "FreeMono"],
        "all": [],
    }


class FontPalette:
    """A specific combination of fonts for one page, ensuring internal consistency
    while varying across pages in a batch.

    Each page gets a font palette drawn from a different combination so the
    batch doesn't look uniform.
    """

    def __init__(self, serif=None, sans=None, mono=None):
        fonts = get_system_fonts()
        self.serif = serif or random.choice(fonts["serif"])
        self.sans = sans or random.choice(fonts["sans"])
        self.mono = mono or random.choice(fonts["mono"])

    def get(self, category, size, bold=False, italic=False):
        """Build a Pango font description string."""
        base = {"serif": self.serif, "sans": self.sans, "mono": self.mono}[category]
        parts = [base]
        if bold:
            parts.append("Bold")
        if italic:
            parts.append("Italic")
        parts.append(str(size))
        return " ".join(parts)

    def __repr__(self):
        return f"FontPalette(serif={self.serif!r}, sans={self.sans!r}, mono={self.mono!r})"


class BatchFontScheduler:
    """Ensures font diversity across a batch by cycling through available fonts
    and avoiding repeating the same palette too often."""

    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
        fonts = get_system_fonts()
        self.serif_pool = list(fonts["serif"])
        self.sans_pool = list(fonts["sans"])
        self.mono_pool = list(fonts["mono"])
        random.shuffle(self.serif_pool)
        random.shuffle(self.sans_pool)
        random.shuffle(self.mono_pool)
        self._idx = 0

    def next_palette(self):
        """Return the next font palette, cycling through combinations."""
        s = self.serif_pool[self._idx % len(self.serif_pool)]
        a = self.sans_pool[self._idx % len(self.sans_pool)]
        m = self.mono_pool[self._idx % len(self.mono_pool)]
        self._idx += 1
        return FontPalette(serif=s, sans=a, mono=m)
