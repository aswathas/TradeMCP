"""Generate the manga screentone tiles as real PNG plates.

Pure stdlib PNG writer: 8-bit greyscale, no filtering, zlib compressed.
Tiles are 45 degree dot lattices at three densities.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "showcase" / "site" / "assets" / "plates"

TILE = 8


def png_bytes(pixels: list[list[tuple[int, int, int, int]]]) -> bytes:
    """Encode an 8-bit RGBA PNG from a square pixel matrix."""
    height = len(pixels)
    width = len(pixels[0])

    raw = b"".join(
        b"\x00" + b"".join(bytes(pixel) for pixel in row) for row in pixels
    )

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    # colour type 6 = RGBA, so the tone composites over any page colour.
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def tone_tile(dot: int, ink: tuple[int, int, int], alpha: int, pitch: int = 4):
    """A 45 degree dot lattice: `dot` px squares on a `pitch` lattice."""
    pixels = [[(0, 0, 0, 0) for _ in range(TILE)] for _ in range(TILE)]
    span = TILE // pitch + 2
    for i in range(-span, span + 1):
        for j in range(-span, span + 1):
            cx = (i * pitch + j * pitch) % TILE
            cy = (i * pitch - j * pitch) % TILE
            for dx in range(dot):
                for dy in range(dot):
                    x, y = (cx + dx) % TILE, (cy + dy) % TILE
                    pixels[y][x] = (ink[0], ink[1], ink[2], alpha)
    return pixels


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # Ink dots for the paper theme, pale dots for the night theme.
    sets = (("tone", (16, 15, 16)), ("tone-night", (236, 237, 240)))
    # Alpha keeps the tone behind the text instead of fighting it.
    densities = (("light", 1, 70), ("mid", 2, 110), ("dark", 3, 170))
    for prefix, ink in sets:
        for name, dot, alpha in densities:
            path = OUT / f"{prefix}-{name}.png"
            path.write_bytes(png_bytes(tone_tile(dot, ink, alpha)))
            print(f"{path.name}: {path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
