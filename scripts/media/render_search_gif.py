"""Render a search replay to an animated GIF with the standard library alone.

Reads ``docs/benchmarks/lab-trace.json`` (produced by
``scripts/bench/routing_benchmark.py --export-lab-trace``) and draws the A* and
Dijkstra searches expanding side by side over the same delivery route in
central São Paulo, then encodes the frames as GIF89a: an indexed-colour raster,
a 3x5 bitmap font for the counters, and a minimal LZW encoder.

Everything is drawn in palette indices, so there is no quantisation step and no
image library anywhere in the pipeline.

Usage:
    python scripts/media/render_search_gif.py
    python scripts/media/render_search_gif.py --frames 80 --delay 7
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PALETTE: list[tuple[int, int, int]] = [
    (11, 18, 32),  # 0  page background
    (30, 41, 59),  # 1  street
    (45, 74, 110),  # 2  fast street
    (245, 158, 11),  # 3  A* expansion
    (56, 132, 255),  # 4  Dijkstra expansion
    (34, 197, 94),  # 5  final route
    (226, 232, 240),  # 6  text
    (168, 85, 247),  # 7  destination marker
    (250, 250, 250),  # 8  origin marker
    (148, 163, 184),  # 9  panel frame
    (15, 23, 42),  # 10 panel background
]

BACKGROUND, STREET, FAST_STREET = 0, 1, 2
ASTAR_DOT, DIJKSTRA_DOT, ROUTE = 3, 4, 5
TEXT, DESTINATION, ORIGIN, FRAME_LINE, PANEL = 6, 7, 8, 9, 10

# 3x5 glyphs: digits, panel letters and the two separators used in counters.
FONT: dict[str, tuple[str, ...]] = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "A": ("111", "101", "111", "101", "101"),
    "D": ("110", "101", "101", "101", "110"),
    "L": ("100", "100", "100", "100", "111"),
    "T": ("111", "010", "010", "010", "010"),
    "*": ("101", "010", "111", "010", "101"),
    "/": ("001", "001", "010", "100", "100"),
    " ": ("000", "000", "000", "000", "000"),
}


class Raster:
    """Index-colour pixel buffer with the few primitives the replay needs."""

    def __init__(self, width: int, height: int, fill: int = BACKGROUND) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray([fill]) * (width * height)

    def clear(self) -> None:
        self.pixels = bytearray([BACKGROUND]) * (self.width * self.height)

    def copy_from(self, other: Raster) -> None:
        self.pixels[:] = other.pixels

    def set(self, x: int, y: int, color: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y * self.width + x] = color

    def rect(self, x0: int, y0: int, x1: int, y1: int, color: int) -> None:
        for y in range(y0, y1 + 1):
            if not 0 <= y < self.height:
                continue
            row = y * self.width
            for x in range(max(0, x0), min(self.width, x1 + 1)):
                self.pixels[row + x] = color

    def line(self, x0: int, y0: int, x1: int, y1: int, color: int) -> None:
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        error = dx - dy
        while True:
            self.set(x0, y0, color)
            if x0 == x1 and y0 == y1:
                return
            doubled = 2 * error
            if doubled > -dy:
                error -= dy
                x0 += sx
            if doubled < dx:
                error += dx
                y0 += sy

    def dot(self, x: int, y: int, radius: int, color: int) -> None:
        self.rect(x - radius, y - radius, x + radius, y + radius, color)

    def text(self, x: int, y: int, value: str, color: int = TEXT, scale: int = 1) -> None:
        cursor = x
        for character in value:
            glyph = FONT.get(character.upper(), FONT[" "])
            for row, line in enumerate(glyph):
                for column, bit in enumerate(line):
                    if bit == "1":
                        self.rect(
                            cursor + column * scale,
                            y + row * scale,
                            cursor + column * scale + scale - 1,
                            y + row * scale + scale - 1,
                            color,
                        )
            cursor += 4 * scale


class BitWriter:
    """LSB-first bit packing, the order GIF's LZW expects."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.bits = 0
        self.count = 0

    def write(self, code: int, size: int) -> None:
        self.bits |= code << self.count
        self.count += size
        while self.count >= 8:
            self.data.append(self.bits & 0xFF)
            self.bits >>= 8
            self.count -= 8

    def flush(self) -> bytes:
        if self.count > 0:
            self.data.append(self.bits & 0xFF)
            self.bits = 0
            self.count = 0
        return bytes(self.data)


def lzw_encode(indices: bytes, min_code_size: int) -> bytes:
    clear = 1 << min_code_size
    end = clear + 1
    code_size = min_code_size + 1
    table = {bytes([value]): value for value in range(clear)}
    next_code = end + 1
    writer = BitWriter()
    writer.write(clear, code_size)
    buffer = b""
    for value in indices:
        candidate = buffer + bytes([value])
        if candidate in table:
            buffer = candidate
            continue
        writer.write(table[buffer], code_size)
        table[candidate] = next_code
        next_code += 1
        if next_code > (1 << code_size):
            if code_size < 12:
                code_size += 1
            else:
                writer.write(clear, code_size)
                table = {bytes([i]): i for i in range(clear)}
                next_code = end + 1
                code_size = min_code_size + 1
        buffer = bytes([value])
    if buffer:
        writer.write(table[buffer], code_size)
    writer.write(end, code_size)
    return writer.flush()


def _sub_blocks(payload: bytes) -> bytes:
    out = bytearray()
    for start in range(0, len(payload), 255):
        chunk = payload[start : start + 255]
        out.append(len(chunk))
        out.extend(chunk)
    out.append(0)
    return bytes(out)


def encode_gif(
    frames: list[Raster], palette: list[tuple[int, int, int]], delay_cs: int, path: Path
) -> int:
    width, height = frames[0].width, frames[0].height
    size_bits = max(1, (len(palette) - 1).bit_length())  # 2**(bits+1) colours
    table_size = 1 << (size_bits + 1)
    min_code_size = max(2, size_bits + 1)

    out = bytearray(b"GIF89a")
    out += width.to_bytes(2, "little") + height.to_bytes(2, "little")
    out.append(0xF0 | (size_bits & 0x07))  # global table, 8-bit colour resolution
    out.append(BACKGROUND)
    out.append(0)
    for index in range(table_size):
        red, green, blue = palette[index] if index < len(palette) else (0, 0, 0)
        out += bytes((red, green, blue))
    # Loop forever.
    out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"

    for frame in frames:
        out += b"\x21\xf9\x04\x04" + delay_cs.to_bytes(2, "little") + b"\x00\x00"
        out += b"\x2c" + (0).to_bytes(2, "little") + (0).to_bytes(2, "little")
        out += width.to_bytes(2, "little") + height.to_bytes(2, "little") + b"\x00"
        out.append(min_code_size)
        out += _sub_blocks(lzw_encode(bytes(frame.pixels), min_code_size))
    out += b"\x3b"
    path.write_bytes(bytes(out))
    return len(out)


PANEL_W, PANEL_H = 300, 300
MARGIN = 12
TEXT_H = 16
WIDTH = MARGIN * 3 + PANEL_W * 2
HEIGHT = MARGIN * 3 + TEXT_H + PANEL_H


def _to_pixel(
    latitude: float,
    longitude: float,
    south: float,
    west: float,
    scale: float,
    panel: tuple[int, int],
) -> tuple[int, int]:
    origin_x, origin_y = panel
    return (
        int(origin_x + (longitude - west) * scale),
        int(origin_y + (latitude - south) * scale),
    )


def build_frames(trace: dict, frame_count: int) -> list[Raster]:
    solvers = trace["solvers"]
    # ALT landmarks are the honest headline on a one-way street network: the
    # straight-line heuristic barely beats Dijkstra there.
    order = [("alt", "ALT", ASTAR_DOT), ("dijkstra", "D", DIJKSTRA_DOT)]

    base = Raster(WIDTH, HEIGHT)
    base.rect(0, 0, WIDTH - 1, HEIGHT - 1, BACKGROUND)
    panels: dict[str, tuple[int, int, float, float, float]] = {}
    for index, (name, _label, _colour) in enumerate(order):
        panel_x = MARGIN + index * (PANEL_W + MARGIN)
        panel_y = MARGIN + TEXT_H
        south, west, scale = _project_for(trace, panel_x, panel_y)
        panels[name] = (panel_x, panel_y, south, west, scale)
        base.rect(panel_x, panel_y, panel_x + PANEL_W, panel_y + PANEL_H, PANEL)
        base.rect(panel_x, panel_y, panel_x + PANEL_W, panel_y + PANEL_H, FRAME_LINE)
        base.rect(panel_x + 1, panel_y + 1, panel_x + PANEL_W - 1, panel_y + PANEL_H - 1, PANEL)
        for from_index, to_index, speed in trace["edges"]:
            from_node, to_node = trace["nodes"][from_index], trace["nodes"][to_index]
            colour = FAST_STREET if speed >= 45 else STREET
            base.line(
                *_to_pixel(from_node[0], from_node[1], south, west, scale, (panel_x, panel_y)),
                *_to_pixel(to_node[0], to_node[1], south, west, scale, (panel_x, panel_y)),
                colour,
            )

    totals = {name: len(solvers[name]["expanded_order"]) for name, _, _ in order}
    peak = max(totals.values())
    paths = {
        name: [
            _to_pixel(
                trace["nodes"][node][0],
                trace["nodes"][node][1],
                panels[name][2],
                panels[name][3],
                panels[name][4],
                (panels[name][0], panels[name][1]),
            )
            for node in solvers[name]["node_path"]
        ]
        for name, _, _ in order
    }
    origin = trace["origin"]
    destination = trace["destination"]

    frames: list[Raster] = []
    for frame_index in range(frame_count + 1):
        progress = round(peak * frame_index / frame_count)
        frame = Raster(WIDTH, HEIGHT)
        frame.copy_from(base)
        for panel_index, (name, label, colour) in enumerate(order):
            panel_x, panel_y, south, west, scale = panels[name]
            expanded = solvers[name]["expanded_order"]
            shown = min(progress, len(expanded))
            frame.text(
                panel_x + 4,
                MARGIN,
                f"{label} {shown}/{len(expanded)}",
                scale=2,
            )
            for node in expanded[:shown]:
                latitude, longitude = trace["nodes"][node]
                x, y = _to_pixel(latitude, longitude, south, west, scale, (panel_x, panel_y))
                frame.dot(x, y, 1, colour)
            if shown >= len(expanded):
                for start in range(len(paths[name]) - 1):
                    frame.line(*paths[name][start], *paths[name][start + 1], ROUTE)
            for node, marker in ((origin, ORIGIN), (destination, DESTINATION)):
                latitude, longitude = trace["nodes"][node]
                x, y = _to_pixel(latitude, longitude, south, west, scale, (panel_x, panel_y))
                frame.dot(x, y, 3, marker)
            frame.text(
                panel_x + 4,
                panel_y + PANEL_H + 3,
                f"{label} {totals[name]}",
            )
        frames.append(frame)
    return frames


def _project_for(trace: dict, panel_x: int, panel_y: int) -> tuple[float, float, float]:
    nodes = trace["nodes"]
    latitudes = [node[0] for node in nodes]
    longitudes = [node[1] for node in nodes]
    latitude_span = max(max(latitudes) - min(latitudes), 1e-5)
    longitude_span = max(max(longitudes) - min(longitudes), 1e-5)
    span = max(latitude_span, longitude_span)
    pad = 0.06
    centre_latitude = (min(latitudes) + max(latitudes)) / 2
    centre_longitude = (min(longitudes) + max(longitudes)) / 2
    south = centre_latitude - span * (0.5 + pad)
    west = centre_longitude - span * (0.5 + pad)
    scale = min(PANEL_W, PANEL_H) / (span * (1 + 2 * pad))
    # Shift so the drawn area is centred inside the panel.
    length = span * (1 + 2 * pad) * scale
    south -= (PANEL_H - length) / 2 / scale
    west -= (PANEL_W - length) / 2 / scale
    return south, west, scale


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace", default=str(ROOT / "docs" / "benchmarks" / "lab-trace.json")
    )
    parser.add_argument(
        "--out", default=str(ROOT / "docs" / "media" / "lab-alt-vs-dijkstra.gif")
    )
    parser.add_argument("--frames", type=int, default=64)
    parser.add_argument("--delay", type=int, default=8, help="Frame delay in centiseconds")
    args = parser.parse_args()

    trace_path = Path(args.trace)
    if not trace_path.exists():
        raise SystemExit(
            f"Trace not found at {trace_path}; run "
            "'python scripts/bench/routing_benchmark.py --export-lab-trace' first."
        )
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    frames = build_frames(trace, args.frames)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    size = encode_gif(frames, PALETTE, args.delay, out)
    panels = trace["solvers"]
    summary = " vs ".join(
        f"{name} {len(panels[name]['expanded_order'])}" for name in ("alt", "dijkstra")
    )
    print(
        f"Wrote {out.as_posix()} — {len(frames)} frames, {size / 1_048_576:.2f} MB "
        f"({summary} expansions on the demo route)"
    )


if __name__ == "__main__":
    main()
