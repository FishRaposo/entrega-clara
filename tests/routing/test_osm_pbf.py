"""The OSM PBF reader, verified against files this test writes itself.

Building the fixture with a minimal protobuf encoder keeps the repository free
of binary blobs and exercises the exact wire format the reader consumes: blob
headers, raw and zlib payloads, dense and plain nodes, delta-coded ways.
"""

import importlib.util
import sys
import zlib
from itertools import pairwise
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "data" / "osm_pbf.py"
spec = importlib.util.spec_from_file_location("osm_pbf", MODULE_PATH)
osm_pbf = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
# Register before executing: on Python 3.11 dataclasses resolves annotations via
# sys.modules[cls.__module__], so an unregistered module fails at the first
# @dataclass with "'NoneType' object has no attribute '__dict__'".
sys.modules[spec.name] = osm_pbf  # type: ignore[union-attr]
spec.loader.exec_module(osm_pbf)  # type: ignore[union-attr]

BBOX = (-23.60, -46.70, -23.50, -46.60)  # south, west, north, east


# --- a minimal PBF writer -------------------------------------------------


def _varint(value: int) -> bytes:
    if value < 0:
        value += 1 << 64
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _zigzag(value: int) -> int:
    return (value << 1) ^ (value >> 63)


def _f_varint(number: int, value: int) -> bytes:
    return _varint(number << 3) + _varint(value)


def _f_bytes(number: int, payload: bytes) -> bytes:
    return _varint((number << 3) | 2) + _varint(len(payload)) + payload


def _f_packed(number: int, values: list[int], *, zigzag: bool = False) -> bytes:
    payload = b"".join(_varint(_zigzag(value) if zigzag else value) for value in values)
    return _f_bytes(number, payload)


def _deltas(values: list[int]) -> list[int]:
    if not values:
        return []
    return [values[0], *(b - a for a, b in pairwise(values))]


def _blob(payload: bytes, *, compress: bool) -> bytes:
    if compress:
        body = _f_varint(2, len(payload)) + _f_bytes(3, zlib.compress(payload))
    else:
        body = _f_bytes(1, payload)
    header = _f_bytes(1, b"OSMData") + _f_varint(3, len(body))
    return len(header).to_bytes(4, "big") + header + body


def _header_blob(
    features: tuple[str, ...] = ("OsmSchema-V0.6", "DenseNodes"),
    osm_base: int = 1_700_000_000,
) -> bytes:
    payload = b"".join(_f_bytes(4, feature.encode()) for feature in features)
    payload += _f_varint(32, osm_base)
    body = _f_bytes(1, payload)
    header = _f_bytes(1, b"OSMHeader") + _f_varint(3, len(body))
    return len(header).to_bytes(4, "big") + header + body


def _primitive_block(
    *,
    dense: list[tuple[int, float, float]] | None = None,
    plain: list[tuple[int, float, float]] | None = None,
    ways: list[tuple[int, dict[str, str], list[int]]] | None = None,
    compress: bool = False,
    granularity: int = 100,
) -> bytes:
    strings = [""]
    for _way_id, tags, _refs in ways or []:
        for key, value in tags.items():
            for text in (key, value):
                if text not in strings:
                    strings.append(text)
    table = b"".join(_f_bytes(1, text.encode()) for text in strings)
    group = b""
    if dense:
        ids = _deltas([node[0] for node in dense])
        lats = _deltas([round(node[1] / 1e-7) for node in dense])
        lons = _deltas([round(node[2] / 1e-7) for node in dense])
        dense_payload = (
            _f_packed(1, ids, zigzag=True)
            + _f_packed(8, lats, zigzag=True)
            + _f_packed(9, lons, zigzag=True)
        )
        group += _f_bytes(2, dense_payload)
    for node_id, latitude, longitude in plain or []:
        node = (
            _f_varint(1, _zigzag(node_id))
            + _f_varint(8, _zigzag(round(latitude / 1e-9 / granularity)))
            + _f_varint(9, _zigzag(round(longitude / 1e-9 / granularity)))
        )
        group += _f_bytes(1, node)
    for way_id, tags, refs in ways or []:
        keys = [strings.index(key) for key in tags]
        vals = [strings.index(value) for value in tags.values()]
        way = _f_varint(1, way_id) + _f_packed(2, keys) + _f_packed(3, vals)
        way += _f_packed(8, _deltas(refs), zigzag=True)
        group += _f_bytes(3, way)
    block = _f_bytes(1, table) + _f_bytes(2, group) + _f_varint(17, granularity)
    return _blob(block, compress=compress)


def _write(tmp_path: Path, *blobs: bytes) -> Path:
    path = tmp_path / "extract.osm.pbf"
    path.write_bytes(_header_blob() + b"".join(blobs))
    return path


# --- tests ----------------------------------------------------------------


def test_reads_dense_nodes_and_ways_inside_the_bbox(tmp_path: Path):
    path = _write(
        tmp_path,
        _primitive_block(
            dense=[
                (1001, -23.55, -46.65),
                (1002, -23.551, -46.651),
                (1003, -23.40, -46.65),  # north of the box
                (1004, -23.552, -46.652),
                (1005, -23.553, -46.653),
                (1006, -23.554, -46.654),
            ],
            ways=[
                (10, {"highway": "residential", "oneway": "yes"}, [1001, 1002, 1004]),
                (11, {"highway": "residential"}, [1001, 1003, 1004]),
                (12, {"highway": "footway"}, [1001, 1002]),
                (13, {"highway": "residential"}, [1001, 1002, 9999, 1005, 1006]),
            ],
        ),
    )

    extract = osm_pbf.read_extract(path, bbox=BBOX, classes={"residential"})

    assert set(extract.nodes) == {"1001", "1002", "1004", "1005", "1006"}
    assert extract.nodes["1001"] == pytest.approx((-23.55, -46.65))
    by_way = {}
    for segment in extract.segments:
        by_way.setdefault(segment.way_id, []).append(segment.refs)
    # The footway is filtered out; the way leaving the box is split, and a
    # single-node fragment is never emitted.
    assert set(by_way) == {"10", "13"}
    assert by_way["10"] == [("1001", "1002", "1004")]
    assert by_way["13"] == [("1001", "1002"), ("1005", "1006")]
    assert extract.segments[0].tags == {"highway": "residential", "oneway": "yes"}
    assert extract.stats.nodes_read == 6
    assert extract.stats.nodes_kept == 5
    assert extract.stats.ways_read == 4
    assert extract.stats.ways_kept == 2
    assert extract.stats.segments_kept == 3
    assert extract.stats.osm_base == 1_700_000_000
    assert "DenseNodes" in extract.stats.features


def test_reads_zlib_compressed_blocks(tmp_path: Path):
    path = _write(
        tmp_path,
        _primitive_block(dense=[(2001, -23.55, -46.65), (2002, -23.551, -46.651)],
                         compress=True),
        _primitive_block(ways=[(20, {"highway": "primary"}, [2001, 2002])],
                         compress=True),
    )
    extract = osm_pbf.read_extract(path, bbox=BBOX, classes={"primary"})
    assert set(extract.nodes) == {"2001", "2002"}
    assert [segment.refs for segment in extract.segments] == [("2001", "2002")]


def test_reads_plain_nodes_with_granularity(tmp_path: Path):
    path = _write(
        tmp_path,
        _primitive_block(
            plain=[(3001, -23.555, -46.655), (3002, -23.556, -46.656)],
            ways=[(30, {"highway": "tertiary"}, [3001, 3002])],
        ),
    )
    extract = osm_pbf.read_extract(path, bbox=BBOX, classes={"tertiary"})
    assert extract.nodes["3001"] == pytest.approx((-23.555, -46.655))
    assert [segment.refs for segment in extract.segments] == [("3001", "3002")]


def test_bbox_is_inclusive_on_its_edges(tmp_path: Path):
    path = _write(
        tmp_path,
        _primitive_block(
            dense=[(4001, BBOX[0], BBOX[1]), (4002, BBOX[2], BBOX[3])],
            ways=[(40, {"highway": "service"}, [4001, 4002])],
        ),
    )
    extract = osm_pbf.read_extract(path, bbox=BBOX, classes={"service"})
    assert set(extract.nodes) == {"4001", "4002"}


def test_rejects_unsupported_required_features(tmp_path: Path):
    path = tmp_path / "historical.osm.pbf"
    path.write_bytes(_header_blob(features=("OsmSchema-V0.6", "HistoricalInformation")))
    with pytest.raises(osm_pbf.PbfError, match="unsupported PBF feature"):
        osm_pbf.read_extract(path, bbox=BBOX, classes={"residential"})


def test_rejects_truncated_files(tmp_path: Path):
    path = tmp_path / "truncated.osm.pbf"
    path.write_bytes(b"\x00\x00\x00\x08")
    with pytest.raises(osm_pbf.PbfError):
        osm_pbf.read_extract(path, bbox=BBOX, classes={"residential"})


def test_way_without_road_tags_is_skipped(tmp_path: Path):
    path = _write(
        tmp_path,
        _primitive_block(
            dense=[(5001, -23.55, -46.65), (5002, -23.551, -46.651)],
            ways=[(50, {"building": "yes"}, [5001, 5002])],
        ),
    )
    extract = osm_pbf.read_extract(path, bbox=BBOX, classes={"residential"})
    assert extract.stats.ways_read == 1
    assert extract.stats.ways_kept == 0
    assert extract.segments == []
