"""
GridMerge: Python package for leveling and merging gridded geophysical data.

This package provides tools for adjusting and merging multiple gridded datasets,
particularly airborne magnetic and gamma-ray spectrometric data. It implements
algorithms for:
- DC shift correction (baseline leveling)
- Scale adjustment
- Polynomial fitting for tilt and gradient removal
- Seamless grid merging with feathering in overlap regions
"""

__version__ = "0.1.0"

from .grid import Grid
from .merge import GridMerger
from .adjust import GridAdjuster
from .utils import (
    inspect_grids,
    reproject_grids_to_reference,
    interactive_reproject,
    prepare_grids_for_merge
)

__all__ = [
    "Grid",
    "GridMerger",
    "GridAdjuster",
    "inspect_grids",
    "reproject_grids_to_reference",
    "interactive_reproject",
    "prepare_grids_for_merge"
]
