"""
Basic tests for the GridMerge package.
"""

import numpy as np
import pytest
from gridmerge import Grid, GridMerger, GridAdjuster


def test_grid_creation():
    """Test basic grid creation."""
    data = np.random.rand(10, 10) * 100
    grid = Grid(data, xmin=0, ymin=0, cellsize=10, nodata_value=-99999.0)
    
    assert grid.nrows == 10
    assert grid.ncols == 10
    assert grid.xmin == 0
    assert grid.ymin == 0
    assert grid.cellsize == 10
    assert grid.xmax == 100
    assert grid.ymax == 100


def test_grid_bounds():
    """Test grid bounds calculation."""
    data = np.ones((20, 30))
    grid = Grid(data, xmin=100, ymin=200, cellsize=5)
    
    bounds = grid.bounds
    assert bounds == (100, 200, 250, 300)


def test_grid_valid_data():
    """Test valid data extraction."""
    data = np.array([[1, 2, -99999], [3, 4, 5]], dtype=np.float32)
    grid = Grid(data, xmin=0, ymin=0, cellsize=1, nodata_value=-99999.0)
    
    valid_data = grid.get_valid_data()
    assert len(valid_data) == 5
    assert -99999 not in valid_data


def test_grid_overlap_detection():
    """Test overlap detection between grids."""
    grid1 = Grid(np.ones((10, 10)), xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(np.ones((10, 10)), xmin=5, ymin=0, cellsize=1)
    
    overlap = grid1.get_overlap(grid2)
    assert overlap is not None
    
    # No overlap case
    grid3 = Grid(np.ones((10, 10)), xmin=100, ymin=100, cellsize=1)
    overlap2 = grid1.get_overlap(grid3)
    assert overlap2 is None


def test_dc_shift_calculation():
    """Test DC shift calculation."""
    # Create two grids with known offset
    data1 = np.full((10, 20), 100.0, dtype=np.float32)
    data2 = np.full((10, 20), 110.0, dtype=np.float32)
    
    grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(data2, xmin=10, ymin=0, cellsize=1)  # Overlaps
    
    dc_shift = GridAdjuster.calculate_dc_shift(grid1, grid2)
    assert dc_shift is not None
    assert abs(dc_shift - (-10.0)) < 0.01  # Should be -10


def test_apply_dc_shift():
    """Test DC shift application."""
    data = np.full((10, 10), 100.0, dtype=np.float32)
    grid = Grid(data, xmin=0, ymin=0, cellsize=1)
    
    adjusted = GridAdjuster.apply_dc_shift(grid, 10.0)
    
    assert np.allclose(adjusted.get_valid_data(), 110.0)


def test_scale_calculation():
    """Test scale factor calculation."""
    # Grid 1 with std=10
    data1 = np.random.normal(100, 10, (20, 20)).astype(np.float32)
    # Grid 2 with std=20
    data2 = np.random.normal(100, 20, (20, 20)).astype(np.float32)
    
    grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(data2, xmin=10, ymin=0, cellsize=1)
    
    scale = GridAdjuster.calculate_scale_factor(grid1, grid2)
    assert scale is not None
    # Scale should be approximately std1/std2 ≈ 0.5
    assert 0.3 < scale < 0.7


def test_polynomial_fitting_2d():
    """Test 2D polynomial fitting."""
    # Create simple linear surface
    x = np.array([0, 1, 2, 0, 1, 2])
    y = np.array([0, 0, 0, 1, 1, 1])
    z = 10 + 2*x + 3*y  # z = 10 + 2x + 3y
    
    coeffs = GridAdjuster.fit_polynomial_2d(x, y, z, degree=1)
    
    # Coefficients should be close to [10, 2, 3]
    assert abs(coeffs[0] - 10) < 0.01
    assert abs(coeffs[1] - 2) < 0.01
    assert abs(coeffs[2] - 3) < 0.01


def test_polynomial_evaluation_2d():
    """Test 2D polynomial evaluation."""
    coeffs = np.array([10, 2, 3])  # z = 10 + 2x + 3y
    
    x = np.array([[0, 1], [0, 1]])
    y = np.array([[0, 0], [1, 1]])
    
    z = GridAdjuster.evaluate_polynomial_2d(x, y, coeffs, degree=1)
    
    expected = np.array([[10, 12], [13, 15]])
    assert np.allclose(z, expected)


def test_merge_two_grids():
    """Test merging two grids."""
    data1 = np.full((10, 10), 100.0, dtype=np.float32)
    data2 = np.full((10, 10), 100.0, dtype=np.float32)
    
    grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(data2, xmin=5, ymin=0, cellsize=1)
    
    merged = GridMerger.merge_two_grids(grid1, grid2, priority='first')
    
    assert merged.nrows == 10
    assert merged.ncols == 15
    assert merged.xmin == 0
    assert merged.xmax == 15


def test_merge_multiple_grids():
    """Test merging multiple grids."""
    grids = []
    for i in range(3):
        data = np.full((10, 10), 100.0 + i*10, dtype=np.float32)
        grid = Grid(data, xmin=i*5, ymin=0, cellsize=1)
        grids.append(grid)
    
    merged = GridMerger.merge_multiple_grids(grids, level_to_first=False)
    
    assert merged.nrows == 10
    assert merged.ncols >= 15


def test_merge_with_auto_leveling():
    """Test automatic leveling and merging."""
    # Create grids with different baselines
    data1 = np.full((10, 10), 100.0, dtype=np.float32)
    data2 = np.full((10, 10), 110.0, dtype=np.float32)
    
    grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(data2, xmin=5, ymin=0, cellsize=1)
    
    merged = GridMerger.merge_with_auto_leveling([grid1, grid2], polynomial_degree=1)
    
    assert merged is not None
    assert merged.nrows == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
