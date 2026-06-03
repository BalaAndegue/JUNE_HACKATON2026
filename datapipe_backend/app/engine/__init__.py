"""
DataPipe execution engine.

Real, pandas/DuckDB-backed pipeline execution. Replaces the previous
simulated runner: every node transforms actual data, produces real row
counts, real previews and a real data-quality score.
"""
from .executor import execute_pipeline

__all__ = ['execute_pipeline']
