"""Streaming execution — large blocking pipelines spill through the sink path."""
import glob
import os

import polars as pl
from pyflow_engine import Runner, WorkflowDoc
from pyflow_engine.cache import RunCache
from pyflow_engine.frame import collect_streaming


def test_collect_streaming_matches_in_memory():
    lf = (
        pl.LazyFrame({"g": [1, 1, 2, 3, 3, 3], "v": [10, 20, 30, 40, 50, 60]})
        .group_by("g")
        .agg(pl.col("v").sum().alias("total"))
    )
    assert collect_streaming(lf).sort("g").to_dicts() == lf.collect().sort("g").to_dicts()


def test_pipeline_streams_scan_filter_groupby_sink(registry, tmp_path):
    """A million-row scan -> filter -> group-by -> sink pipeline runs through the
    Runner (materialize() streams each node to an Arrow file) and matches a direct
    Polars computation. Exercises the out-of-core sink path end to end."""
    n = 1_000_000
    src = tmp_path / "big.parquet"
    pl.select(
        (pl.int_range(n, dtype=pl.Int64) % 100).alias("region"),
        pl.int_range(n, dtype=pl.Int64).alias("v"),
    ).write_parquet(src)

    out = tmp_path / "agg.csv"
    doc = WorkflowDoc.model_validate(
        {
            "nodes": [
                {"id": "i", "type": "input.file", "config": {"path": str(src), "format": "parquet"}},
                {"id": "f", "type": "prep.filter", "config": {"expression": "[region] < 50"}},
                {
                    "id": "s",
                    "type": "transform.summarize",
                    "config": {
                        "group_by": ["region"],
                        "aggregations": [{"field": "v", "func": "sum", "output": "total"}],
                    },
                },
                {
                    "id": "o",
                    "type": "output.file",
                    "config": {"path": str(out), "format": "csv", "delimiter": ",", "write_header": True},
                },
            ],
            "edges": [
                {"id": "e1", "source": {"node": "i", "anchor": "out"}, "target": {"node": "f", "anchor": "in"}},
                {"id": "e2", "source": {"node": "f", "anchor": "true"}, "target": {"node": "s", "anchor": "in"}},
                {"id": "e3", "source": {"node": "s", "anchor": "out"}, "target": {"node": "o", "anchor": "in"}},
            ],
        }
    )
    cache_dir = tmp_path / "cache"
    Runner(registry=registry, cache=RunCache(str(cache_dir))).run(doc)

    result = pl.read_csv(out).sort("region")
    expected = (
        pl.scan_parquet(src)
        .filter(pl.col("region") < 50)
        .group_by("region")
        .agg(pl.col("v").sum().alias("total"))
        .collect()
        .sort("region")
    )
    assert result.height == 50
    assert result["region"].to_list() == expected["region"].to_list()
    assert result["total"].to_list() == expected["total"].to_list()
    # Nodes were materialized through the streaming sink cache.
    assert glob.glob(os.path.join(str(cache_dir), "*.arrow"))
