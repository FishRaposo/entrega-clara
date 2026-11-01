"""Both graph document shapes, and gzip transparency in ``load_graph``."""

import gzip
import json
from pathlib import Path

import pytest
from delivery_platform.application.container import GRAPH_FILES, graph_path
from delivery_platform.core.config import Settings
from delivery_platform.routing.graph import load_graph

SYNTHETIC = Path("data/graph/sao-paulo-centro.json")


def _compact_document() -> dict:
    return {
        "format": "compact-v1",
        "graph_id": "compact-fixture",
        "version": "1",
        "source": "test",
        "attribution": "© OpenStreetMap contributors (ODbL 1.0)",
        "ids": ["a", "b", "c"],
        "nodes": [[-23.55, -46.65], [-23.551, -46.651], [-23.552, -46.652]],
        "edges": [
            [0, 1, 140.0, 30.0],
            [1, 2, 150.0, 40.0],
            [2, 1, 150.0, 40.0],
        ],
    }


def test_compact_document_round_trips_through_gzip(tmp_path: Path):
    path = tmp_path / "compact.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(_compact_document(), handle)

    graph = load_graph(path)

    assert graph.graph_id == "compact-fixture"
    assert graph.version == "1"
    assert list(graph.nodes) == ["a", "b", "c"]
    assert graph.nodes["b"].latitude == pytest.approx(-23.551)
    assert [edge.to_node for edge in graph.neighbors("a")] == ["b"]
    # Reverse adjacency is derived for the compact documents too.
    assert [edge.to_node for edge in graph.reverse_neighbors("b")] == ["a", "c"]
    assert graph.max_speed_mps == pytest.approx(40 * 1000 / 3600)
    assert "ODbL" in graph.attribution


def test_compact_document_rejects_unknown_edge_indices(tmp_path: Path):
    document = _compact_document()
    document["edges"] = [[0, 9, 10.0, 30.0]]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown node index"):
        load_graph(path)


def test_compact_document_requires_aligned_arrays(tmp_path: Path):
    document = _compact_document()
    document["nodes"] = document["nodes"][:2]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="same length"):
        load_graph(path)


def test_object_document_still_reads_when_gzipped(tmp_path: Path):
    raw = SYNTHETIC.read_text(encoding="utf-8")
    path = tmp_path / "synthetic.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(raw)

    plain = load_graph(SYNTHETIC)
    compressed = load_graph(path)

    assert compressed.graph_id == plain.graph_id
    assert len(compressed.nodes) == len(plain.nodes)
    assert len(compressed.adjacency) == len(plain.adjacency)


def test_city_graph_is_a_named_source():
    assert "city" in GRAPH_FILES
    settings = Settings()
    path = graph_path(settings, "city")
    assert path is not None
    assert path.name == GRAPH_FILES["city"]
