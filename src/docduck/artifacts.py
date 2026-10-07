"""Post-processing to simulate scanning/printing artifacts.

Two presets, both reproducible via seed:

- `mild` (default): clean office scan: light noise, subtle vignette, a few
  dust specks. Near-invisible; useful as a generic training variation.
- `photocopy`, `fax`, `extreme`: qualitatively harder. They add contrast
  saturation, ink dropout, denser speckle, and (for `extreme`) JPEG
  recompression. These regimes actually degrade modern OCR: the mild
  preset does not (empirically, OCR accuracy is unchanged at intensity=10).
"""

import io
import random

import cairo
import numpy as np
from PIL import Image

# Parameter regimes for each preset. `intensity` (0..1) further scales
# within a regime. Keys map to effects in `apply_artifacts`.
_PRESETS = {
    # `blur` is the primary axis: empirically OCR is near-ceiling (>99%) on
    # everything except blur, so the preset knob that actually matters is
    # optical blur radius. `noise`, `specks`, `dropout`, `jpeg_q` are
    # secondary realism touches. Numbers calibrated against LightOnOCR at
    # 200 DPI rendering; reduce `blur` proportionally if you render smaller.
    # Calibrated to stay HUMAN-READABLE while degrading OCR. Blur is the
    # dominant axis; anything above ~4.5 turns small-font tables into
    # unreadable smears (body text is still fine but glyphs packed tighter
    # than the blur radius merge). Dropout range is also kept conservative
    # to avoid erasing table text that blur has already softened into grays.
    "mild": dict(
        noise=2.0,
        vignette=0.06,
        grain=1.5,
        specks=15,
        dropout=0.0,
        contrast=0.0,
        blur=0.0,
        jpeg_q=None,
    ),
    "photocopy": dict(
        noise=4.0,
        vignette=0.18,
        grain=2.5,
        specks=60,
        dropout=0.08,
        contrast=0.30,
        blur=1.0,
        jpeg_q=None,
    ),
    "fax": dict(
        noise=7.0,
        vignette=0.28,
        grain=3.5,
        specks=150,
        dropout=0.10,
        contrast=0.45,
        blur=1.8,
        jpeg_q=None,
    ),
    "extreme": dict(
        noise=11.0,
        vignette=0.38,
        grain=5.0,
        specks=260,
        dropout=0.14,
        contrast=0.60,
        blur=2.5,
        jpeg_q=40,
    ),
}


def apply_artifacts(surface, intensity=0.5, seed=None, preset="mild"):
    """Apply scanning/print artifacts to a Cairo ImageSurface.

    Args:
        surface: Cairo ImageSurface (read-only).
        intensity: 0.0 = none, 1.0 = full strength of the chosen preset.
        seed: Random seed for reproducibility.
        preset: "mild" | "photocopy" | "fax" | "extreme". `mild` matches the
            original behavior (near-invisible degradation). The harder presets
            add contrast saturation, ink dropout, and optional JPEG re-encoding
            - effects that actually challenge OCR.

    Returns:
        A new Cairo ImageSurface with the artifacts applied.
    """
    if preset not in _PRESETS:
        raise ValueError(f"unknown preset {preset!r}; known: {list(_PRESETS)}")
    p = _PRESETS[preset]
    rng = np.random.default_rng(seed)

    w = surface.get_width()
    h = surface.get_height()
    stride = surface.get_stride()

    buf = surface.get_data()
    arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, stride // 4, 4).copy()
    arr = arr[:, :w, :]

    # 1. Gaussian sensor noise
    if intensity > 0.1 and p["noise"] > 0:
        noise = rng.normal(0, intensity * p["noise"], arr[:, :, :3].shape)
        arr[:, :, :3] = np.clip(arr[:, :, :3].astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # 2. Uneven lighting vignette
    if intensity > 0.2 and p["vignette"] > 0:
        y_coords = np.linspace(0, 1, h)[:, None]
        x_coords = np.linspace(0, 1, w)[None, :]
        cx, cy = rng.uniform(0.2, 0.8), rng.uniform(0.2, 0.8)
        dist = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2)
        vignette = 1.0 - dist * intensity * p["vignette"]
        arr[:, :, :3] = np.clip(
            arr[:, :, :3].astype(np.float32) * vignette[:, :, None], 0, 255
        ).astype(np.uint8)

    # 3. Fine paper grain
    if intensity > 0.15 and p["grain"] > 0:
        grain_scale = 2
        grain_h = -(-h // grain_scale)
        grain_w = -(-w // grain_scale)
        grain = rng.normal(0, intensity * p["grain"], (grain_h, grain_w))
        grain = np.repeat(np.repeat(grain, grain_scale, axis=0), grain_scale, axis=1)
        grain = grain[:h, :w, None]
        arr[:, :, :3] = np.clip(arr[:, :, :3].astype(np.float32) + grain, 0, 255).astype(np.uint8)

    # 4. Specks (dust/dirt on scanner glass). Dark specks only: photocopy
    # dust lands on the drum and prints as dark blobs.
    if intensity > 0.3 and p["specks"] > 0:
        n_specks = int(intensity * p["specks"])
        for _ in range(n_specks):
            sx = int(rng.integers(0, w))
            sy = int(rng.integers(0, h))
            sr = int(rng.integers(1, 4))
            brightness = int(rng.integers(30, 120))
            y_lo, y_hi = max(0, sy - sr), min(h, sy + sr)
            x_lo, x_hi = max(0, sx - sr), min(w, sx + sr)
            arr[y_lo:y_hi, x_lo:x_hi, :3] = np.clip(
                arr[y_lo:y_hi, x_lo:x_hi, :3].astype(np.int16) - brightness, 0, 255
            ).astype(np.uint8)

    # 5. Contrast saturation: stretch around 128. Darks go darker, lights
    # go lighter. The classic "photocopy of a photocopy" look.
    if intensity > 0.2 and p["contrast"] > 0:
        gain = 1.0 + intensity * p["contrast"]
        rgb = arr[:, :, :3].astype(np.float32)
        rgb = (rgb - 128.0) * gain + 128.0
        arr[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)

    # 6. Ink dropout: near-white gray pixels (luma 160-220) randomly flip
    # to white, simulating photocopy drop-out of low-ink areas. Narrow range
    # keeps body text safe even after blur has softened its edges into grays.
    if intensity > 0.2 and p["dropout"] > 0:
        luma = arr[:, :, :3].mean(axis=2)
        faint = (luma > 160) & (luma < 220)
        mask = rng.random(faint.shape) < (intensity * p["dropout"])
        kill = faint & mask
        arr[kill, :3] = 255

    # 7. Optical blur: drum scanner + ink bleed. Attacks glyph shapes
    # directly, unlike additive noise which OCR models are well-trained to
    # ignore. Applied via Pillow's Gaussian filter.
    if intensity > 0.2 and p["blur"] > 0:
        from PIL import ImageFilter

        sigma = intensity * p["blur"]
        img = Image.fromarray(arr[:, :, [2, 1, 0]])
        img = img.filter(ImageFilter.GaussianBlur(radius=sigma))
        arr[:, :, [2, 1, 0]] = np.asarray(img)

    # 8. JPEG recompression: only for `extreme`. Round-trip via Pillow.
    if p["jpeg_q"] is not None and intensity > 0.3:
        q = max(10, int(p["jpeg_q"] + (1 - intensity) * 20))
        img = Image.fromarray(arr[:, :, [2, 1, 0]])  # BGRA → RGB
        buf_io = io.BytesIO()
        img.save(buf_io, format="JPEG", quality=q)
        buf_io.seek(0)
        reloaded = np.asarray(Image.open(buf_io).convert("RGB"))
        arr[:, :, [2, 1, 0]] = reloaded

    out = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    out_buf = out.get_data()
    out_arr = np.frombuffer(out_buf, dtype=np.uint8).reshape(h, out.get_stride() // 4, 4)
    out_arr[:, :w, :] = arr
    out.mark_dirty()
    return out


def apply_rotation(surface, max_degrees=0.5, seed=None):
    """Apply slight rotation to simulate scanner misalignment.

    Returns a new surface with the rotation applied.
    """
    if seed is not None:
        random.seed(seed)

    angle = random.uniform(-max_degrees, max_degrees) * (3.14159265 / 180.0)
    w = surface.get_width()
    h = surface.get_height()

    out = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(out)

    # Fill with the page's edge color (approximate from top-left pixel)
    buf = surface.get_data()
    if len(buf) >= 4:
        arr = np.frombuffer(buf, dtype=np.uint8)
        bg = (arr[2] / 255.0, arr[1] / 255.0, arr[0] / 255.0)
    else:
        bg = (1.0, 1.0, 1.0)
    ctx.set_source_rgb(*bg)
    ctx.paint()

    ctx.translate(w / 2, h / 2)
    ctx.rotate(angle)
    ctx.translate(-w / 2, -h / 2)
    ctx.set_source_surface(surface, 0, 0)
    ctx.paint()

    return out
