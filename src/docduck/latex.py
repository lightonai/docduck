"""LaTeX equation renderer using a real TeX engine.

Compiles LaTeX to PDF via pdflatex, crops, and converts to a Cairo-compatible
BGRA numpy array for compositing onto document pages.

Falls back to matplotlib mathtext if pdflatex is not available.
"""

import hashlib
import os
import shutil
import subprocess
import tempfile
from functools import lru_cache

import cairo
import numpy as np


@lru_cache(maxsize=1)
def _has_pdflatex():
    """Check if pdflatex is available."""
    return shutil.which("pdflatex") is not None


# On-disk cache to avoid re-compiling the same equation
_CACHE_DIR = os.path.join(tempfile.gettempdir(), "docduck_latex_cache")


def render_latex(tex, *, color=(0, 0, 0), dpi=150, fontsize=11):
    """Render LaTeX to a premultiplied BGRA numpy array.

    Args:
        tex: Raw LaTeX math string (no $ delimiters).
        color: (r, g, b) float tuple in 0-1 range.
        dpi: Output resolution.
        fontsize: Base font size in pt.

    Returns:
        (arr, depth) where arr is H×W×4 uint8 BGRA, depth is baseline offset.
        Returns None if rendering fails.
    """
    if not _has_pdflatex():
        return None

    cache_key = hashlib.md5(f"{tex}:{dpi}:{fontsize}".encode()).hexdigest()
    os.makedirs(_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(_CACHE_DIR, f"{cache_key}.png")

    if not os.path.exists(cache_path):
        ok = _compile_and_crop(tex, cache_path, dpi, fontsize)
        if not ok:
            return None

    try:
        surface = cairo.ImageSurface.create_from_png(cache_path)
    except Exception:
        return None

    w = surface.get_width()
    h = surface.get_height()
    buf = surface.get_data()
    arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, surface.get_stride() // 4, 4)
    arr = arr[:, :w, :].copy()

    # The PNG is black-on-white from pdflatex. Extract as grayscale mask
    # (dark pixels = ink). Convert to alpha mask.
    # Cairo BGRA: arr[:,:,0]=B, arr[:,:,1]=G, arr[:,:,2]=R, arr[:,:,3]=A
    gray = 1.0 - (arr[:, :, 0].astype(np.float32) / 255.0)  # invert: black→1, white→0

    r, g, b = color
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[:, :, 0] = (b * gray * 255).astype(np.uint8)
    out[:, :, 1] = (g * gray * 255).astype(np.uint8)
    out[:, :, 2] = (r * gray * 255).astype(np.uint8)
    out[:, :, 3] = (gray * 255).astype(np.uint8)

    return out, 0


def _compile_and_crop(tex, output_png, dpi, fontsize):
    """Compile LaTeX to PDF, crop whitespace, convert to PNG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "eq.tex")
        pdf_path = os.path.join(tmpdir, "eq.pdf")

        doc = f"""\\documentclass[{fontsize}pt]{{article}}
\\usepackage{{amsmath,amssymb,amsfonts}}
\\usepackage[active,tightpage]{{preview}}
\\pagestyle{{empty}}
\\begin{{document}}
\\begin{{preview}}
$\\displaystyle {tex}$
\\end{{preview}}
\\end{{document}}
"""
        with open(tex_path, "w") as f:
            f.write(doc)

        try:
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "eq.tex"],
                cwd=tmpdir,
                capture_output=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

        if not os.path.exists(pdf_path):
            return False

        try:
            # Use sips on macOS or pdftoppm if available
            if shutil.which("pdftoppm"):
                subprocess.run(
                    [
                        "pdftoppm",
                        "-png",
                        "-r",
                        str(dpi),
                        "-singlefile",
                        pdf_path,
                        os.path.join(tmpdir, "out"),
                    ],
                    capture_output=True,
                    timeout=5,
                )
                png_src = os.path.join(tmpdir, "out.png")
            elif shutil.which("sips"):
                png_src = os.path.join(tmpdir, "eq.png")
                subprocess.run(
                    [
                        "sips",
                        "-s",
                        "format",
                        "png",
                        "-s",
                        "dpiWidth",
                        str(dpi),
                        "-s",
                        "dpiHeight",
                        str(dpi),
                        pdf_path,
                        "--out",
                        png_src,
                    ],
                    capture_output=True,
                    timeout=5,
                )
            else:
                return False

            if os.path.exists(png_src):
                shutil.copy2(png_src, output_png)
                return True
        except Exception:
            pass

        return False
