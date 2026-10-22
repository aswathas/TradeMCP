#!/usr/bin/env python
"""Regenerate the "Malevolent Shrine" web assets from the source art in ``Assets for ui/``.

Run from the repository root::

    .venv\\Scripts\\python.exe scripts\\make_shrine_assets.py

Outputs (into ``showcase/site/assets/shrine/``)::

    shrine-fang-frame.png   demon fang/jaw frame, white studio background keyed out
    slash-divider.png       red slash divider            (source already has alpha)
    seal-badge.png          spiky sun/seal badge          (source already has alpha)
    corner-bracket.png      red corner bracket + triangle (source already has alpha)
    panel-frame.png         orange/red panel frame        (source already has alpha)

The shrine roof is no longer on the page. Its master is still rebuilt, into
``showcase/sources/shrine/shrine-roof-banner.png``, but nothing is published
for it - putting it back is one ``publish=True`` away.

Background-removal method (the two large plates)
-------------------------------------------------
Both plates are flat-colour paintings that still carry their studio background,
so they are keyed with the same Pillow-only routine:

1.  A per-pixel "distance from the background colour" scalar ``s`` is built from
    the source RGB:  white plate -> ``s = 255 - min(R, G, B)`` (0 == pure white)
                      black plate -> ``s = max(R, G, B)``       (0 == pure black)
2.  The background is found with a **border flood fill**
    (``PIL.ImageDraw.floodfill``) over the pixels whose ``s`` stays within a
    threshold of the border seed, so only the region that is connected to the
    image border is treated as background.  This connectivity test is what keeps
    the roof's near-black shadowed tiles and the fang frame's white tooth
    highlights intact - a plain luminance threshold would punch holes in them.
3.  The boundary is feathered with a smooth ramp
    ``alpha = clamp((s - S_ZERO) / (S_HIGH - S_ZERO), 0, 1)`` evaluated inside the
    flooded region only, so the soft, glowing edges fade out instead of getting
    a hard jaggy cut.
4.  Per-plate clean-up:
      * the roof plate additionally drops isolated opaque debris (a stray grey
        sparkle that the image generator left in the black background) by
        keeping only the largest connected blob;
      * the fang plate keeps its blood-splatter specks, which are part of the
        artwork, and its enclosed black "mouth" void, which the connectivity
        test leaves untouched.

Only Pillow is used - no new dependency is added to the project.
"""

from __future__ import annotations

import io
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "Assets for ui"
MASTER_DIR = ROOT / "showcase" / "sources" / "shrine"
OUT_DIR = ROOT / "showcase" / "site" / "assets" / "shrine"

MAX_SIDE = 1600
MAX_BYTES = 400 * 1024
WEBP_QUALITY = 88

# Impossible in the greyscale copy used for flood filling, so "was this pixel
# filled?" can be answered exactly.
FILL_MARKER = (255, 0, 255)

SOURCE_FANG = "Gemini_Generated_Image_8fvh6t8fvh6t8fvh (1).png"
SOURCE_ROOF = "Gemini_Generated_Image_8fvh6t8fvh6t8fvh.png"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def scalar_key(img: Image.Image, mode: str) -> Image.Image:
    """Per-pixel distance from the studio background colour (0 == pure background)."""
    r, g, b = img.convert("RGB").split()
    if mode == "white":
        # 255 - min(R, G, B): 0 for pure white, large for saturated colour.
        return ImageChops.invert(ImageChops.darker(ImageChops.darker(r, g), b))
    if mode == "black":
        # max(R, G, B): 0 for pure black, large for a lit pixel.
        return ImageChops.lighter(ImageChops.lighter(r, g), b)
    raise ValueError(f"unknown key mode: {mode!r}")


def border_flood(scalar: Image.Image, tolerance: int, seed: tuple[int, int] = (0, 0)) -> Image.Image:
    """Flood fill from ``seed`` over pixels within ``tolerance`` of the seed value.

    Returns a 0/255 mask: 255 where the pixel belongs to the connected
    background region.
    """
    work = Image.merge("RGB", (scalar, scalar, scalar))
    # RGB flood filling compares the sum of the per-band deltas, hence 3x.
    ImageDraw.floodfill(work, seed, FILL_MARKER, thresh=3 * tolerance)
    diff = ImageChops.difference(work, Image.new("RGB", work.size, FILL_MARKER))
    r, g, b = diff.split()
    worst = ImageChops.lighter(ImageChops.lighter(r, g), b)
    return worst.point(lambda v: 255 if v == 0 else 0)


def ramp_alpha(scalar: Image.Image, region: Image.Image, s_zero: int, s_high: int) -> Image.Image:
    """Smooth alpha ramp evaluated inside ``region`` only; opaque outside it."""
    if s_high <= s_zero:
        raise ValueError("s_high must be greater than s_zero")
    lut = []
    for v in range(256):
        if v <= s_zero:
            a = 0
        elif v >= s_high:
            a = 255
        else:
            a = int(round(255 * (v - s_zero) / (s_high - s_zero)))
        lut.append(a)
    ramp = scalar.point(lut)
    alpha = ImageChops.multiply(ramp, region)
    return ImageChops.lighter(alpha, ImageChops.invert(region))


def first_nonzero(img: Image.Image):
    """Top-most, left-most non-zero pixel of a binary image, or None."""
    bbox = img.getbbox()
    if bbox is None:
        return None
    x0, y0, x1, y1 = bbox
    for y in range(y0, y1):
        row = img.crop((x0, y, x1, y + 1))
        rb = row.getbbox()
        if rb is not None:
            return x0 + rb[0], y
    return None


def drop_small_blobs(alpha: Image.Image, min_area: int) -> Image.Image:
    """Drop tiny isolated opaque specks (e.g. generator debris) from the artwork.

    Components at or above ``min_area`` are kept, so genuinely separate parts of
    the artwork (the roof's detached skulls) survive.
    """
    mask = alpha.point(lambda v: 255 if v > 0 else 0)
    work = mask.copy()
    keep = mask.copy()
    while True:
        seed = first_nonzero(work)
        if seed is None:
            break
        comp = work.copy()
        ImageDraw.floodfill(comp, seed, 128, thresh=1)
        comp_mask = comp.point(lambda v: 255 if v == 128 else 0)
        area = comp_mask.histogram()[255]
        work = ImageChops.subtract(work, comp_mask)
        if area < min_area:
            keep = ImageChops.subtract(keep, comp_mask)
    return ImageChops.multiply(alpha, keep)


def components(alpha: Image.Image):
    """Label the opaque regions of ``alpha``; yield (area, bbox) per region."""
    mask = alpha.point(lambda v: 255 if v > 8 else 0)
    work = mask.copy()
    while True:
        seed = first_nonzero(work)
        if seed is None:
            return
        comp = work.copy()
        ImageDraw.floodfill(comp, seed, 128, thresh=1)
        comp_mask = comp.point(lambda v: 255 if v == 128 else 0)
        area = comp_mask.histogram()[255]
        bbox = comp_mask.getbbox()
        work = ImageChops.subtract(work, comp_mask)
        if area and bbox:
            yield area, bbox


def trim_to_content(img: Image.Image) -> Image.Image:
    """Cut the plate down to the artwork it actually contains.

    The generator leaves a wide margin of empty background around the roof,
    and a small stray sparkle in the corner that the debris filter is too
    lenient to catch. Every region is measured; anything far smaller than
    the main subject is dropped, and the rest is cropped to their union so
    the plate sits tight against its own edges.
    """
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    found = sorted(components(alpha), reverse=True)
    if not found:
        return rgba
    biggest = found[0][0]
    floor = max(2000, biggest // 40)
    keep = [(area, box) for area, box in found if area >= floor]
    if not keep:
        keep = [found[0]]

    x0 = min(box[0] for _, box in keep)
    y0 = min(box[1] for _, box in keep)
    x1 = max(box[2] for _, box in keep)
    y1 = max(box[3] for _, box in keep)
    cropped = rgba.crop((x0, y0, x1, y1))
    return cropped


def feather_band(core: Image.Image, scalar: Image.Image, s_edge: int, width: int) -> Image.Image:
    """Thin band of fringe pixels around the flood-filled core background.

    The band never reaches further than ``width`` pixels into the artwork, so a
    plate whose artwork contains large near-background areas (the roof's
    shadowed tiles) cannot be eaten away by the background key.
    """
    band = core
    for _ in range(max(0, width)):
        band = band.filter(ImageFilter.MaxFilter(3))
    limit = scalar.point(lambda v: 255 if v <= s_edge else 0)
    return ImageChops.multiply(band, limit)


def downscale(img: Image.Image, max_side: int = MAX_SIDE) -> Image.Image:
    """Resize to at most ``max_side`` on the longest side (no-op when smaller)."""
    longest = max(img.size)
    if longest <= max_side:
        return img
    scale = max_side / longest
    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    return img.resize(size, Image.LANCZOS)


def fit_alpha(rgb: Image.Image, alpha: Image.Image) -> Image.Image:
    """Scale colour and alpha separately so transparent pixels cannot bleed."""
    if rgb.size != alpha.size:
        rgb = rgb.resize(alpha.size, Image.LANCZOS)
    return Image.merge("RGBA", (*rgb.convert("RGB").split(), alpha))


def flatten_transparent_rgb(rgba: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    """Give fully transparent pixels one flat colour.

    Those pixels are invisible, but keeping the noisy source colour there makes
    the PNG several times larger for no visual gain.
    """
    r, g, b, a = rgba.split()
    mask = a.point(lambda v: 255 if v == 0 else 0)
    # Image.composite takes image2 where the mask is 255.
    flat = Image.composite(Image.new("RGB", rgba.size, color), Image.merge("RGB", (r, g, b)), mask)
    return Image.merge("RGBA", (*flat.split(), a))


def save_asset(img: Image.Image, stem: str, publish: bool = True) -> dict:
    """Write the lossless master and the file the page actually loads.

    The master PNG lands in showcase/sources/shrine so the art survives in the
    repo without the published site carrying megabytes of files no page ever
    requests. The site copy is whichever of WebP and PNG is smaller.

    ``publish=False`` writes the master only. A plate the page no longer shows
    keeps its art in the repo - restoring it is one line - and stops costing
    the site a download.

    The PNG is always a real PNG: serving WebP bytes under a .png name makes
    the server send the wrong Content-Type and the file is a lie.
    """
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    master = MASTER_DIR / f"{stem}.png"
    img.save(master, "PNG", optimize=True)
    size = master.stat().st_size

    if not publish:
        return {"bytes": size, "note": "master only", "master": master, "site": None}

    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=WEBP_QUALITY, method=6)
    webp_bytes = buf.getvalue()

    if len(webp_bytes) <= size // 2:
        site = OUT_DIR / f"{stem}.webp"
        site.write_bytes(webp_bytes)
        note = f"webp {len(webp_bytes)} B"
    else:
        site = OUT_DIR / f"{stem}.png"
        shutil.copyfile(master, site)
        note = "webp not smaller; png only"

    return {"bytes": size, "note": note, "master": master, "site": site}


def verify(path: Path) -> dict:
    with Image.open(path) as im:
        im.load()
        info = {
            "size": im.size,
            "mode": im.mode,
            "has_alpha": im.mode in ("RGBA", "LA") or "transparency" in im.info,
            "bytes": path.stat().st_size,
        }
        if info["has_alpha"]:
            info["corner"] = im.convert("RGBA").getpixel((0, 0))[3]
    return info


# --------------------------------------------------------------------------- #
# plate processing
# --------------------------------------------------------------------------- #
def process_plate(
    source: str,
    stem: str,
    mode: str,
    tol_core: int,
    tol_edge: int,
    s_zero: int,
    s_high: int,
    flat_rgb: tuple[int, int, int],
    band_px: int = 0,
    min_blob_area: int = 0,
    publish: bool = True,
) -> Path | None:
    """Key out a studio background and write a transparent PNG.

    ``band_px`` > 0 feathers only a thin fringe around the flood-filled core
    (used for the black plate, whose artwork contains large near-black areas);
    ``band_px`` == 0 feathers the whole background-connected pale region (used
    for the white plate, whose glow is a broad but shallow halo).

    ``publish=False`` keeps the master in the repo and writes no site copy.
    """
    src_path = SRC_DIR / source
    img = Image.open(src_path).convert("RGB")

    scalar = scalar_key(img, mode)
    core = border_flood(scalar, tol_core)           # definitely background
    if band_px:
        region = feather_band(core, scalar, tol_edge, band_px)
    else:
        region = border_flood(scalar, tol_edge)     # background + soft glow fringe
    alpha = ramp_alpha(scalar, region, s_zero, s_high)
    # The core background is always fully transparent, whatever the ramp says.
    alpha = ImageChops.multiply(alpha, ImageChops.invert(core))
    if min_blob_area:
        alpha = drop_small_blobs(alpha, min_blob_area)

    rgba = fit_alpha(img, alpha)
    rgba = flatten_transparent_rgb(rgba, flat_rgb)
    rgba = trim_to_content(rgba)
    small = downscale(rgba)
    small = flatten_transparent_rgb(small, flat_rgb)
    meta = save_asset(small, stem, publish=publish)
    print(
        f"{stem:24s} {meta['bytes']:>8d} B  {small.size[0]}x{small.size[1]} px"
        + (f"  [{meta['note']}]" if meta["note"] else "")
    )
    return meta["site"]


def process_plain(source: str, stem: str) -> Path:
    """Copy an asset that already ships with an alpha channel."""
    src_path = SRC_DIR / source
    with Image.open(src_path) as im:
        rgba = im.convert("RGBA")
    small = downscale(rgba)
    small = flatten_transparent_rgb(small, (0, 0, 0))
    meta = save_asset(small, stem)
    print(
        f"{stem:24s} {meta['bytes']:>8d} B  {small.size[0]}x{small.size[1]} px"
        + (f"  [{meta['note']}]" if meta["note"] else "")
    )
    return meta["site"]


def main() -> None:
    # The site folder holds exactly the files the page loads. Wipe it so a
    # renamed or retired plate cannot linger as a dead request.
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MASTER_DIR.mkdir(parents=True, exist_ok=True)

    print("building shrine assets")
    print("-" * 62)
    # White plate: near-white is transparent.  Connected flood fill from the
    # borders keeps the enclosed black mouth void and the white tooth
    # highlights opaque; the ramp fades the pale glow around the frame.
    process_plate(
        SOURCE_FANG,
        "shrine-fang-frame",
        mode="white",
        tol_core=10,
        tol_edge=60,
        s_zero=8,
        s_high=60,
        flat_rgb=(255, 255, 255),
    )
    # Black plate: near-black is transparent, but the roof artwork contains
    # near-black shadowed tiles, so only what is connected to the image border
    # is treated as background and the feather is limited to a thin fringe.
    # The roof was taken off the page, so only the master is written - the art
    # stays in the repo and the site stops serving a file nobody loads.
    process_plate(
        SOURCE_ROOF,
        "shrine-roof-banner",
        mode="black",
        tol_core=12,
        tol_edge=45,
        s_zero=3,
        s_high=45,
        flat_rgb=(0, 0, 0),
        band_px=3,
        min_blob_area=1000,
        publish=False,
    )
    print("-" * 62)
    process_plain("Code_Generated_Image (2).png", "slash-divider")
    process_plain("Code_Generated_Image (1).png", "seal-badge")
    process_plain("Code_Generated_Image.png", "corner-bracket")
    process_plain("Code_Generated_Image (3).png", "panel-frame")

    print("-" * 62)
    print("verification")
    for stem in (
        "shrine-fang-frame",
        "shrine-roof-banner",
        "slash-divider",
        "seal-badge",
        "corner-bracket",
        "panel-frame",
    ):
        master = MASTER_DIR / f"{stem}.png"
        info = verify(master)
        alpha_note = "" if "corner" not in info else f"  corner alpha={info['corner']}"
        print(
            f"master {stem:22s} {info['size'][0]}x{info['size'][1]} px  mode={info['mode']}  "
            f"alpha={info['has_alpha']}  {info['bytes']:>8d} B{alpha_note}"
        )
        site = OUT_DIR / f"{stem}.webp"
        if not site.exists():
            site = OUT_DIR / f"{stem}.png"
        if not site.exists():
            # a plate the page does not show keeps its master only
            print(f"  site {stem:22s} (not published)")
            continue
        magic = site.read_bytes()[:4]
        if site.suffix == ".webp" and magic != b"RIFF":
            raise SystemExit(f"{site.name} is not a real webp")
        if site.suffix == ".png" and magic != b"\x89PNG":
            raise SystemExit(f"{site.name} is not a real png")
        print(
            f"  site {site.name:22s} {site.stat().st_size:>8d} B  "
            f"{'webp' if site.suffix == '.webp' else 'png'}"
        )
    published = sorted(p.name for p in OUT_DIR.iterdir())
    if len(published) != 5:
        raise SystemExit(f"site folder should hold exactly 5 files, holds {len(published)}: {published}")


if __name__ == "__main__":
    main()
