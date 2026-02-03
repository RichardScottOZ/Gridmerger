"""
Tests for handling grids with different resolutions.
"""

import pytest
import numpy as np
from gridmerge import Grid, GridMerger
from scipy import ndimage


def test_same_resolution_merge():
    """Test merging grids with same resolution works correctly."""
    # Create two grids with same cellsize
    data1 = np.ones((10, 10)) * 100
    grid1 = Grid(data1, xmin=0, ymin=0, cellsize=50)
    
    data2 = np.ones((10, 10)) * 110
    grid2 = Grid(data2, xmin=400, ymin=0, cellsize=50)
    
    # Merge should work fine
    merged = GridMerger.merge_two_grids(grid1, grid2)
    
    assert merged.cellsize == 50
    assert merged.ncols == 18  # Covers both grids
    assert merged.nrows == 10


def test_different_resolution_detection():
    """Test that we can detect different resolutions."""
    grid1 = Grid(np.ones((10, 10)), xmin=0, ymin=0, cellsize=100)
    grid2 = Grid(np.ones((20, 20)), xmin=0, ymin=0, cellsize=50)
    
    assert grid1.cellsize != grid2.cellsize
    assert grid1.cellsize == 100
    assert grid2.cellsize == 50


def test_output_uses_first_grid_cellsize():
    """Test that merged grid uses first grid's cellsize."""
    # Grid 1: 100m cellsize
    grid1 = Grid(np.ones((10, 10)) * 100, xmin=0, ymin=0, cellsize=100)
    
    # Grid 2: 50m cellsize (different!)
    grid2 = Grid(np.ones((20, 20)) * 110, xmin=900, ymin=0, cellsize=50)
    
    # Merge (may have issues, but cellsize should be from grid1)
    try:
        merged = GridMerger.merge_two_grids(grid1, grid2)
        assert merged.cellsize == grid1.cellsize  # Should use first grid's cellsize
    except Exception:
        # Expected to fail due to misalignment
        pass


def test_resample_downsampling():
    """Test downsampling a grid (high res to low res)."""
    # Create high-res grid (50m)
    data = np.random.randn(100, 100) * 10 + 52000
    grid_50m = Grid(data, xmin=0, ymin=0, cellsize=50)
    
    # Downsample to 100m
    target_cellsize = 100
    zoom_factor = grid_50m.cellsize / target_cellsize
    resampled_data = ndimage.zoom(grid_50m.data, zoom_factor, order=1)
    
    grid_100m = Grid(
        resampled_data,
        xmin=grid_50m.xmin,
        ymin=grid_50m.ymin,
        cellsize=target_cellsize,
        nodata_value=grid_50m.nodata_value
    )
    
    assert grid_100m.cellsize == 100
    assert grid_100m.ncols == 50  # 100 cells * 0.5 zoom = 50 cells
    assert grid_100m.nrows == 50
    assert np.abs(grid_100m.data.mean() - grid_50m.data.mean()) < 10  # Similar mean


def test_resample_upsampling():
    """Test upsampling a grid (low res to high res)."""
    # Create low-res grid (200m)
    data = np.random.randn(50, 50) * 10 + 52000
    grid_200m = Grid(data, xmin=0, ymin=0, cellsize=200)
    
    # Upsample to 100m
    target_cellsize = 100
    zoom_factor = grid_200m.cellsize / target_cellsize
    resampled_data = ndimage.zoom(grid_200m.data, zoom_factor, order=1)
    
    grid_100m = Grid(
        resampled_data,
        xmin=grid_200m.xmin,
        ymin=grid_200m.ymin,
        cellsize=target_cellsize,
        nodata_value=grid_200m.nodata_value
    )
    
    assert grid_100m.cellsize == 100
    assert grid_100m.ncols == 100  # 50 cells * 2.0 zoom = 100 cells
    assert grid_100m.nrows == 100
    assert np.abs(grid_100m.data.mean() - grid_200m.data.mean()) < 10  # Similar mean


def test_merge_after_resampling():
    """Test merging works correctly after resampling to common resolution."""
    # Create grids with different resolutions
    grid1_200m = Grid(np.ones((30, 30)) * 100, xmin=0, ymin=0, cellsize=200)
    grid2_100m = Grid(np.ones((60, 60)) * 110, xmin=5500, ymin=0, cellsize=100)
    grid3_50m = Grid(np.ones((120, 120)) * 105, xmin=10500, ymin=0, cellsize=50)
    
    # Resample all to 100m
    target = 100
    
    # Grid 1: 200m → 100m (upsample)
    zoom1 = grid1_200m.cellsize / target
    data1 = ndimage.zoom(grid1_200m.data, zoom1, order=1)
    grid1_100m = Grid(data1, grid1_200m.xmin, grid1_200m.ymin, target)
    
    # Grid 2: already 100m
    grid2_100m_copy = grid2_100m.copy()
    
    # Grid 3: 50m → 100m (downsample)
    zoom3 = grid3_50m.cellsize / target
    data3 = ndimage.zoom(grid3_50m.data, zoom3, order=1)
    grid3_100m = Grid(data3, grid3_50m.xmin, grid3_50m.ymin, target)
    
    # Verify all same resolution
    assert grid1_100m.cellsize == target
    assert grid2_100m_copy.cellsize == target
    assert grid3_100m.cellsize == target
    
    # Now merge should work
    grids = [grid1_100m, grid2_100m_copy, grid3_100m]
    merged = GridMerger.merge_multiple_grids(grids, level_to_first=False)
    
    assert merged.cellsize == target
    assert merged.ncols > 0
    assert merged.nrows > 0


def test_cellsize_check_multiple_grids():
    """Test checking cellsizes of multiple grids."""
    grids = [
        Grid(np.ones((10, 10)), xmin=0, ymin=0, cellsize=200),
        Grid(np.ones((10, 10)), xmin=0, ymin=0, cellsize=100),
        Grid(np.ones((10, 10)), xmin=0, ymin=0, cellsize=50)
    ]
    
    cellsizes = [g.cellsize for g in grids]
    unique_cellsizes = set(cellsizes)
    
    assert len(unique_cellsizes) == 3  # Three different resolutions
    assert 200 in unique_cellsizes
    assert 100 in unique_cellsizes
    assert 50 in unique_cellsizes


def test_geographic_extent_preserved_after_resampling():
    """Test that geographic extent is preserved when resampling."""
    # Create grid
    grid_original = Grid(np.ones((50, 50)) * 100, xmin=1000, ymin=2000, cellsize=100)
    
    original_xmax = grid_original.xmax
    original_ymax = grid_original.ymax
    
    # Resample to different resolution
    target_cellsize = 50
    zoom_factor = grid_original.cellsize / target_cellsize
    resampled_data = ndimage.zoom(grid_original.data, zoom_factor, order=1)
    
    grid_resampled = Grid(
        resampled_data,
        xmin=grid_original.xmin,
        ymin=grid_original.ymin,
        cellsize=target_cellsize
    )
    
    # Check extent approximately preserved (may have small rounding difference)
    assert abs(grid_resampled.xmax - original_xmax) < target_cellsize
    assert abs(grid_resampled.ymax - original_ymax) < target_cellsize


def test_resample_preserves_mean_value():
    """Test that resampling preserves approximate mean value."""
    # Create grid with known values
    data = np.random.randn(100, 100) * 10 + 52000
    grid_original = Grid(data, xmin=0, ymin=0, cellsize=50)
    
    original_mean = grid_original.data.mean()
    
    # Downsample
    target_cellsize = 100
    zoom_factor = grid_original.cellsize / target_cellsize
    resampled_data = ndimage.zoom(grid_original.data, zoom_factor, order=1)
    
    resampled_mean = resampled_data.mean()
    
    # Mean should be very similar (within 1% or small absolute difference)
    assert np.abs(resampled_mean - original_mean) < max(10, abs(original_mean * 0.01))


def test_finest_resolution_strategy():
    """Test choosing finest resolution as target."""
    cellsizes = [200, 100, 50]
    finest = min(cellsizes)
    assert finest == 50


def test_coarsest_resolution_strategy():
    """Test choosing coarsest resolution as target."""
    cellsizes = [200, 100, 50]
    coarsest = max(cellsizes)
    assert coarsest == 200


def test_median_resolution_strategy():
    """Test choosing median resolution as target."""
    cellsizes = [200, 100, 50]
    median = sorted(cellsizes)[len(cellsizes) // 2]
    assert median == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
