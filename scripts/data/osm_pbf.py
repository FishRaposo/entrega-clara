"""Minimal OpenStreetMap PBF reader — standard library only.

Implements just enough of the protobuf wire format and of the OSM PBF schema to
build a routing graph: dense and plain nodes inside a bounding box, and ways
whose tags name a road class. Relations are ignored. The point is scale: a
regional extract (hundreds of megabytes, tens of millions of nodes) is filtered
while it streams and nothing outside the bounding box is retained.

Reference: https://wiki.openstreetmap.org/wiki/PBF_Format

Only the tags the graph needs are materialised (``ROAD_KEYS``), and a way that
leaves and re-enters the box is split into contiguous segments, so no false
shortcut is created across the part that was filtered out.
"""

from __future__ import annotations

import zlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_VARINT, _64BIT, _LENGTH, _32BIT = 0, 1, 2, 5
#: Extracts that need a feature we do not implement are rejected loudly instead
#: of being silently misread. Geofabrik-style extracts use exactly these.
_SUPPORTED_FEATURES = {"OsmSchema-V0.6", "DenseNodes"}
ROAD_KEYS = ("highway", "oneway", "junction", "maxspeed")
NANO = 1e-9


class PbfError(ValueError):
    """The file is not a readable OSM PBF extract, or uses unsupported features."""


@dataclass(frozen=True)
class PbfStats:
    nodes_read: int = 0
    nodes_kept: int = 0
    ways_read: int = 0
    ways_kept: int = 0
    segments_kept: int = 0
    osm_base: int = 0
    features: tuple[str, ...] = ()


@dataclass(frozen=True)
class WaySegment:
    way_id: str
    tags: dict[str, str]
    refs: tuple[str, ...]


@dataclass
class Extract:
    nodes: dict[str, tuple[float, float]] = field(default_factory=dict)
    segments: list[WaySegment] = field(default_factory=list)
    stats: PbfStats = PbfStats()


def _varint(buffer: bytes, position: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        byte = buffer[position]
        position += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, position
        shift += 7
        if shift > 70:
            raise PbfError("varint overflow")


def _signed(value: int) -> int:
    """Interpret a 64-bit varint as a signed integer."""
    return value - (1 << 64) if value >= (1 << 63) else value


def _zigzag(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


def _fields(
    buffer: bytes, start: int = 0, end: int | None = None
) -> Iterator[tuple[int, int, Any]]:
    """Yield ``(field_number, wire_type, value)``; length-delimited values are spans."""
    position = start
    limit = len(buffer) if end is None else end
    while position < limit:
        key, position = _varint(buffer, position)
        field_number, wire = key >> 3, key & 0x07
        if wire == _VARINT:
            value, position = _varint(buffer, position)
            yield field_number, wire, value
        elif wire == _LENGTH:
            length, position = _varint(buffer, position)
            yield field_number, wire, (position, position + length)
            position += length
        elif wire == _64BIT:
            yield field_number, wire, position
            position += 8
        elif wire == _32BIT:
            yield field_number, wire, position
            position += 4
        else:
            raise PbfError(f"unsupported protobuf wire type {wire}")


def _packed_varints(buffer: bytes, span: tuple[int, int]) -> Iterator[int]:
    position, end = span
    while position < end:
        value, position = _varint(buffer, position)
        yield value


def _iter_blobs(path: str | Path) -> Iterator[tuple[str, bytes]]:
    with Path(path).open("rb") as handle:
        while True:
            size_bytes = handle.read(4)
            if not size_bytes:
                return
            if len(size_bytes) < 4:
                raise PbfError("truncated blob header")
            header = handle.read(int.from_bytes(size_bytes, "big"))
            if not header:
                raise PbfError("truncated blob header")
            blob_type, data_size = "", 0
            for field_number, wire, value in _fields(header):
                if field_number == 1 and wire == _LENGTH:
                    blob_type = header[value[0] : value[1]].decode("utf-8", "replace")
                elif field_number == 3 and wire == _VARINT:
                    data_size = value
            if data_size <= 0:
                raise PbfError("blob without a data size")
            data = handle.read(data_size)
            if len(data) < data_size:
                raise PbfError("truncated blob")
            yield blob_type, data


def _decode_blob(data: bytes) -> bytes:
    raw: bytes | None = None
    compressed: bytes | None = None
    raw_size: int | None = None
    for field_number, wire, value in _fields(data):
        if field_number == 1 and wire == _LENGTH:
            raw = data[value[0] : value[1]]
        elif field_number == 2 and wire == _VARINT:
            raw_size = value
        elif field_number == 3 and wire == _LENGTH:
            compressed = data[value[0] : value[1]]
    if raw is not None:
        return raw
    if compressed is not None:
        payload = zlib.decompress(compressed)
        if raw_size is not None and len(payload) != raw_size:
            raise PbfError("decompressed blob size does not match its header")
        return payload
    raise PbfError("blob carries neither raw nor zlib data")


def _header_info(block: bytes) -> tuple[tuple[str, ...], int]:
    features: list[str] = []
    osm_base = 0
    for field_number, wire, value in _fields(block):
        if field_number == 4 and wire == _LENGTH:
            features.append(block[value[0] : value[1]].decode("utf-8", "replace"))
        elif field_number == 32 and wire == _VARINT:
            osm_base = _signed(value)
    return tuple(features), osm_base


def _check_features(features: tuple[str, ...]) -> None:
    unsupported = {feature for feature in features if feature not in _SUPPORTED_FEATURES}
    if unsupported:
        raise PbfError(
            "unsupported PBF feature(s): "
            + ", ".join(sorted(unsupported))
            + " — use a current Geofabrik-style extract"
        )


@dataclass(frozen=True)
class _Header:
    features: tuple[str, ...] = ()
    osm_base: int = 0


def _iter_blocks(path: str | Path) -> Iterator[tuple[bytes, _Header]]:
    """Yield primitive blocks that contain nodes or ways."""
    header = _Header()
    for blob_type, data in _iter_blobs(path):
        if blob_type == "OSMHeader":
            features, osm_base = _header_info(_decode_blob(data))
            _check_features(features)
            header = _Header(features=features, osm_base=osm_base)
            continue
        if blob_type != "OSMData":
            continue
        block = _decode_blob(data)
        if _block_has_nodes(block) or _block_has_ways(block):
            yield block, header


def _group_spans(block: bytes) -> list[tuple[int, int]]:
    return [
        value
        for field_number, wire, value in _fields(block)
        if field_number == 2 and wire == _LENGTH
    ]


def _block_has_nodes(block: bytes) -> bool:
    for span in _group_spans(block):
        for field_number, wire, _value in _fields(block, span[0], span[1]):
            if wire == _LENGTH and field_number in (1, 2):
                return True
    return False


def _block_has_ways(block: bytes) -> bool:
    for span in _group_spans(block):
        for field_number, wire, _value in _fields(block, span[0], span[1]):
            if wire == _LENGTH and field_number == 3:
                return True
    return False


def _block_layout(
    block: bytes,
) -> tuple[tuple[int, int] | None, int, int, int]:
    stringtable: tuple[int, int] | None = None
    granularity, lat_offset, lon_offset = 100, 0, 0
    for field_number, wire, value in _fields(block):
        if field_number == 1 and wire == _LENGTH:
            stringtable = value
        elif field_number == 17 and wire == _VARINT:
            granularity = value
        elif field_number == 19 and wire == _VARINT:
            lat_offset = _signed(value)
        elif field_number == 20 and wire == _VARINT:
            lon_offset = _signed(value)
    return stringtable, granularity, lat_offset, lon_offset


def read_nodes(
    path: str | Path, *, bbox: tuple[float, float, float, float]
) -> tuple[dict[str, tuple[float, float]], PbfStats]:
    """Read every node inside ``bbox`` = (south, west, north, east)."""
    south, west, north, east = bbox
    nodes: dict[str, tuple[float, float]] = {}
    seen = 0
    header = _Header()
    for block, block_header in _iter_blocks(path):
        if not _block_has_nodes(block):
            continue
        header = block_header or header
        _stringtable, granularity, lat_offset, lon_offset = _block_layout(block)
        for group_start, group_end in _group_spans(block):
            for field_number, wire, value in _fields(block, group_start, group_end):
                if wire != _LENGTH:
                    continue
                if field_number == 1:
                    node_id, latitude, longitude = _plain_node(
                        block, value, granularity, lat_offset, lon_offset
                    )
                    seen += 1
                    if south <= latitude <= north and west <= longitude <= east:
                        nodes[node_id] = (latitude, longitude)
                elif field_number == 2:
                    read = _dense_nodes(
                        block,
                        value,
                        bbox=(south, west, north, east),
                        granularity=granularity,
                        lat_offset=lat_offset,
                        lon_offset=lon_offset,
                        into=nodes,
                    )
                    seen += read
    stats = PbfStats(nodes_read=seen, nodes_kept=len(nodes), features=header.features,
                     osm_base=header.osm_base)
    return nodes, stats


def _plain_node(
    block: bytes,
    span: tuple[int, int],
    granularity: int,
    lat_offset: int,
    lon_offset: int,
) -> tuple[str, float, float]:
    node_id = 0
    raw_lat = 0
    raw_lon = 0
    for field_number, wire, value in _fields(block, span[0], span[1]):
        if wire != _VARINT:
            continue
        if field_number == 1:
            node_id = _zigzag(value)
        elif field_number == 8:
            raw_lat = _zigzag(value)
        elif field_number == 9:
            raw_lon = _zigzag(value)
    return (
        str(node_id),
        (lat_offset + granularity * raw_lat) * NANO,
        (lon_offset + granularity * raw_lon) * NANO,
    )


def _dense_nodes(
    block: bytes,
    span: tuple[int, int],
    *,
    bbox: tuple[float, float, float, float],
    granularity: int,
    lat_offset: int,
    lon_offset: int,
    into: dict[str, tuple[float, float]],
) -> int:
    south, west, north, east = bbox
    ids_span: tuple[int, int] | None = None
    lat_span: tuple[int, int] | None = None
    lon_span: tuple[int, int] | None = None
    for field_number, wire, value in _fields(block, span[0], span[1]):
        if wire != _LENGTH:
            continue
        if field_number == 1:
            ids_span = value
        elif field_number == 8:
            lat_span = value
        elif field_number == 9:
            lon_span = value
    if ids_span is None or lat_span is None or lon_span is None:
        raise PbfError("dense nodes without id/lat/lon arrays")
    read = 0
    node_id = 0
    latitude = 0
    longitude = 0
    for raw_id, raw_lat, raw_lon in zip(
        _packed_varints(block, ids_span),
        _packed_varints(block, lat_span),
        _packed_varints(block, lon_span),
        strict=True,
    ):
        node_id += _zigzag(raw_id)
        latitude += _zigzag(raw_lat)
        longitude += _zigzag(raw_lon)
        read += 1
        lat = (lat_offset + granularity * latitude) * NANO
        if lat < south or lat > north:
            continue
        lon = (lon_offset + granularity * longitude) * NANO
        if west <= lon <= east:
            into[str(node_id)] = (lat, lon)
    return read


def read_ways(
    path: str | Path,
    *,
    nodes: dict[str, tuple[float, float]],
    classes: set[str],
) -> tuple[list[WaySegment], PbfStats]:
    """Read ways in the requested classes, split into contiguous in-box segments."""
    segments: list[WaySegment] = []
    ways_read = 0
    ways_kept = 0
    header = _Header()
    for block, block_header in _iter_blocks(path):
        if not _block_has_ways(block):
            continue
        header = block_header or header
        stringtable_span, _granularity, _lat_offset, _lon_offset = _block_layout(block)
        table = _string_table(block, stringtable_span) if stringtable_span else [b""]
        for group_start, group_end in _group_spans(block):
            for field_number, wire, value in _fields(block, group_start, group_end):
                if field_number != 3 or wire != _LENGTH:
                    continue
                ways_read += 1
                parsed = _parse_way(block, value, table)
                if parsed is None:
                    continue
                way_id, tags, refs = parsed
                if tags.get("highway") not in classes:
                    continue
                kept = _split_segments(way_id, tags, refs, nodes)
                if kept:
                    ways_kept += 1
                    segments.extend(kept)
    stats = PbfStats(
        ways_read=ways_read,
        ways_kept=ways_kept,
        segments_kept=len(segments),
        osm_base=header.osm_base,
        features=header.features,
    )
    return segments, stats


def _string_table(block: bytes, span: tuple[int, int]) -> list[bytes]:
    table: list[bytes] = []
    for field_number, wire, value in _fields(block, span[0], span[1]):
        if field_number == 1 and wire == _LENGTH:
            table.append(block[value[0] : value[1]])
    return table


def _parse_way(
    block: bytes, span: tuple[int, int], table: list[bytes]
) -> tuple[str, dict[str, str], tuple[str, ...]] | None:
    way_id = 0
    keys: list[int] = []
    vals: list[int] = []
    refs: list[int] = []
    inline = False
    for field_number, wire, value in _fields(block, span[0], span[1]):
        if field_number == 1 and wire == _VARINT:
            way_id = value
        elif wire != _LENGTH:
            if field_number in (9, 10):
                inline = True
            continue
        elif field_number == 2:
            keys = list(_packed_varints(block, value))
        elif field_number == 3:
            vals = list(_packed_varints(block, value))
        elif field_number == 8:
            refs = list(_packed_varints(block, value))
        elif field_number in (9, 10):
            inline = True
    if inline:
        raise PbfError("LocationsOnWays extracts are not supported; use a standard file")
    tags: dict[str, str] = {}
    for key_index, value_index in zip(keys, vals, strict=False):
        if key_index >= len(table) or value_index >= len(table):
            continue
        key = table[key_index].decode("utf-8", "replace")
        if key in ROAD_KEYS:
            tags[key] = table[value_index].decode("utf-8", "replace")
    if not tags:
        return None
    ids: list[str] = []
    running = 0
    for raw in refs:
        running += _zigzag(raw)
        ids.append(str(running))
    return str(way_id), tags, tuple(ids)


def _split_segments(
    way_id: str,
    tags: dict[str, str],
    refs: tuple[str, ...],
    nodes: dict[str, tuple[float, float]],
) -> list[WaySegment]:
    segments: list[WaySegment] = []
    current: list[str] = []
    for ref in refs:
        if ref in nodes:
            current.append(ref)
        else:
            if len(current) >= 2:
                segments.append(WaySegment(way_id=way_id, tags=tags, refs=tuple(current)))
            current = []
    if len(current) >= 2:
        segments.append(WaySegment(way_id=way_id, tags=tags, refs=tuple(current)))
    return segments


def read_extract(
    path: str | Path,
    *,
    bbox: tuple[float, float, float, float],
    classes: set[str],
) -> Extract:
    """Two streaming passes: bbox nodes first, then ways that touch them."""
    nodes, node_stats = read_nodes(path, bbox=bbox)
    segments, way_stats = read_ways(path, nodes=nodes, classes=classes)
    stats = PbfStats(
        nodes_read=node_stats.nodes_read,
        nodes_kept=node_stats.nodes_kept,
        ways_read=way_stats.ways_read,
        ways_kept=way_stats.ways_kept,
        segments_kept=way_stats.segments_kept,
        osm_base=node_stats.osm_base,
        features=node_stats.features,
    )
    return Extract(nodes=nodes, segments=segments, stats=stats)
