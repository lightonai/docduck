"""Download Google Fonts and organize them by ISO-15924 script.

Fetches a curated set of popular families per script from the `google/fonts`
GitHub mirror into `./fonts/<script>/<family>/*.ttf`, then writes a
fontconfig override that makes them visible to Pango / `fc-list` without
touching system font state.

Usage:

    python -m docduck.cli.download_fonts               # default curated set
    python -m docduck.cli.download_fonts --scripts Latn Arab Hani
    python -m docduck.cli.download_fonts --target ~/.cache/docduck/fonts
    python -m docduck.cli.download_fonts --add-family ofl/spectral Latn
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Curated per-script family list. Each entry is (family_slug, license_dir).
# license_dir is the top-level folder in google/fonts: "ofl" | "apache" | "ufl".
# Keep this list small and high-quality; users can `--add-family` more.
CURATED: dict[str, list[tuple[str, str]]] = {
    "Latn": [
        ("roboto", "apache"),
        ("opensans", "apache"),
        ("lato", "ofl"),
        ("merriweather", "ofl"),
        ("sourceserif4", "ofl"),
        ("ebgaramond", "ofl"),
        ("playfairdisplay", "ofl"),
        ("crimsonpro", "ofl"),
        ("ibmplexsans", "ofl"),
        ("ibmplexserif", "ofl"),
        ("ibmplexmono", "ofl"),
        ("inter", "ofl"),
    ],
    "Arab": [
        ("notosansarabic", "ofl"),
        ("amiri", "ofl"),
        ("cairo", "ofl"),
        ("tajawal", "ofl"),
    ],
    # Han (simplified + traditional Chinese); Noto also covers some Japanese kanji.
    "Hani": [
        ("notosanssc", "ofl"),
        ("notoserifsc", "ofl"),
        ("notosanstc", "ofl"),
    ],
    "Jpan": [
        ("notosansjp", "ofl"),
        ("notoserifjp", "ofl"),
    ],
    "Kore": [
        ("notosanskr", "ofl"),
        ("notoserifkr", "ofl"),
    ],
    "Deva": [
        ("notosansdevanagari", "ofl"),
        ("hind", "ofl"),
    ],
    "Cyrl": [
        ("ptsans", "apache"),
        ("ptserif", "apache"),
    ],
    "Thai": [
        ("notosansthai", "ofl"),
        ("sarabun", "ofl"),
    ],
    "Hebr": [
        ("notosanshebrew", "ofl"),
        ("davidlibre", "ofl"),
    ],
}

GH_API = "https://api.github.com/repos/google/fonts/contents"


def _gh_get(url: str) -> list[dict] | dict:
    """GitHub contents API call. Passes GITHUB_TOKEN as bearer if set."""
    req = urllib.request.Request(url, headers={"User-Agent": "docduck-fonts"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _download(url: str, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest.stat().st_size  # already fetched
    req = urllib.request.Request(url, headers={"User-Agent": "docduck-fonts"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    dest.write_bytes(data)
    return len(data)


def fetch_family(script: str, family: str, license_dir: str, target: Path) -> list[Path]:
    """Download every .ttf for a family into `target/<script>/<family>/`.

    Lists the directory via the contents API (rate-limited: 60/hr anonymous,
    5000/hr with GITHUB_TOKEN), then pulls TTFs from raw.githubusercontent.com
    (no rate limit).
    """
    out_dir = target / script / family
    out_dir.mkdir(parents=True, exist_ok=True)
    listing_url = f"{GH_API}/{license_dir}/{family}"
    try:
        listing = _gh_get(listing_url)
    except urllib.error.HTTPError as e:
        print(f"  [{script}/{family}] listing failed: HTTP {e.code}", file=sys.stderr)
        return []
    if isinstance(listing, dict):
        # A `message` key typically means "Not Found" or a rate-limit error.
        print(f"  [{script}/{family}] {listing.get('message', 'listing error')}", file=sys.stderr)
        return []
    ttfs = [f for f in listing if f["name"].lower().endswith((".ttf", ".otf"))]
    # If the family uses variable fonts, also grab the static/ subdir.
    if not ttfs:
        static = [f for f in listing if f["type"] == "dir" and f["name"] == "static"]
        if static:
            try:
                listing = _gh_get(f"{listing_url}/static")
                ttfs = [f for f in listing if f["name"].lower().endswith((".ttf", ".otf"))]
            except Exception as e:
                print(f"  [{script}/{family}] static/ listing failed: {e}", file=sys.stderr)
    saved = []
    for f in ttfs:
        url = f["download_url"]  # already points at raw.githubusercontent.com
        dest = out_dir / f["name"]
        try:
            n = _download(url, dest)
        except Exception as e:
            print(f"    skip {f['name']}: {e}", file=sys.stderr)
            continue
        saved.append(dest)
        print(f"    {f['name']:40s} {n / 1024:6.0f} KB")
    return saved


def write_fontconfig(font_dir: Path) -> Path:
    """Write a fontconfig file that inherits the user's defaults and adds
    `font_dir` to the search path. Returns the config path that callers set
    as FONTCONFIG_FILE for Pango / fc-list to discover the new fonts.
    """
    cfg_dir = Path.home() / ".cache" / "docduck"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "fontconfig.conf"
    cfg_path.write_text(f"""\
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <!-- Inherit the system's default config (/etc/fonts/fonts.conf on linux,
       /opt/homebrew/etc/fonts/fonts.conf on macOS). -->
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <include ignore_missing="yes">/opt/homebrew/etc/fonts/fonts.conf</include>
  <include ignore_missing="yes">/usr/local/etc/fonts/fonts.conf</include>
  <!-- Docduck downloaded fonts. Walked recursively. -->
  <dir>{font_dir.resolve()}</dir>
</fontconfig>
""")
    return cfg_path


def main():
    parser = argparse.ArgumentParser(
        description="Download Google Fonts by script into a local directory"
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("./fonts"),
        help="Output directory (default: ./fonts)",
    )
    parser.add_argument(
        "--scripts",
        nargs="+",
        default=list(CURATED.keys()),
        help=f"ISO-15924 scripts to fetch. Default: {' '.join(CURATED.keys())}",
    )
    parser.add_argument(
        "--add-family",
        nargs=2,
        metavar=("LICENSE/FAMILY", "SCRIPT"),
        action="append",
        default=[],
        help="Add extra family to fetch, e.g. --add-family ofl/spectral Latn. Repeatable.",
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        help="Skip writing the fontconfig override.",
    )
    args = parser.parse_args()

    plan: dict[str, list[tuple[str, str]]] = {s: list(CURATED.get(s, [])) for s in args.scripts}
    for lf, script in args.add_family:
        try:
            lic, fam = lf.split("/", 1)
        except ValueError:
            print(f"error: --add-family expects LICENSE/FAMILY, got {lf!r}", file=sys.stderr)
            sys.exit(2)
        plan.setdefault(script, []).append((fam, lic))

    print(f"Downloading Google Fonts → {args.target}")
    total_files = 0
    for script, families in plan.items():
        print(f"\n[{script}]")
        for family, lic in families:
            saved = fetch_family(script, family, lic, args.target)
            total_files += len(saved)
    print(f"\nDone. {total_files} files saved under {args.target}/<script>/<family>/")

    if not args.no_config:
        cfg = write_fontconfig(args.target)
        print(f"\nWrote fontconfig override: {cfg}")
        print(f"Point Pango / fc-list at it:\n  export FONTCONFIG_FILE={cfg}")


if __name__ == "__main__":
    main()
