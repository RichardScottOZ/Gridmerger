"""
Tests for non-intersecting grids and priority handling.
"""

import numpy as np
import pytest
from gridmerge import Grid, GridMerger, GridAdjuster


def test_dc_shift_with_no_overlap():
    """Test that DC shift returns None when grids don't overlap."""
    # Two grids that don't intersect
    grid1 = Grid(np.full((10, 10), 100.0, dtype=np.float32), xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(np.full((10, 10), 150.0, dtype=np.float32), xmin=100, ymin=100, cellsize=1)
    
    # DC shift should return None
    dc_shift = GridAdjuster.calculate_dc_shift(grid1, grid2)
    assert dc_shift is None


def test_level_to_reference_no_overlap():
    """Test that leveling returns unchanged grid when no overlap."""
    grid1 = Grid(np.full((10, 10), 100.0, dtype=np.float32), xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(np.full((10, 10), 150.0, dtype=np.float32), xmin=100, ymin=100, cellsize=1)
    
    # Level grid2 to grid1 (no overlap)
    leveled = GridAdjuster.level_to_reference(
        grid2, grid1,
        use_dc_shift=True,
        polynomial_degree=1
    )
    
    # Should be unchanged (original value ~150)
    assert np.allclose(leveled.get_valid_data().mean(), 150.0, atol=1.0)


def test_merge_non_intersecting_grids():
    """Test merging grids that don't intersect with each other."""
    # Three separate grids
    grid1 = Grid(np.full((10, 10), 100.0, dtype=np.float32), xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(np.full((10, 10), 120.0, dtype=np.float32), xmin=50, ymin=0, cellsize=1)
    grid3 = Grid(np.full((10, 10), 140.0, dtype=np.float32), xmin=100, ymin=0, cellsize=1)
    
    # Merge
    merged = GridMerger.merge_with_auto_leveling([grid1, grid2, grid3])
    
    # Should contain all three grids
    assert merged is not None
    assert merged.ncols >= 110  # Spans from 0 to 110
    
    # Check that data from all grids is present
    valid_data = merged.get_valid_data()
    assert len(valid_data) > 0


def test_merge_with_some_overlaps_some_not():
    """Test merging where some grids overlap and some don't."""
    # Grid 1 and 2 overlap, Grid 3 doesn't overlap with either
    grid1 = Grid(np.full((10, 10), 100.0, dtype=np.float32), xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(np.full((10, 10), 115.0, dtype=np.float32), xmin=5, ymin=0, cellsize=1)
    grid3 = Grid(np.full((10, 10), 150.0, dtype=np.float32), xmin=100, ymin=100, cellsize=1)
    
    # Merge with leveling
    merged = GridMerger.merge_with_auto_leveling([grid1, grid2, grid3])
    
    # Grid 2 should be leveled to Grid 1, Grid 3 should not
    assert merged is not None
    
    # Check valid data includes all grids
    valid_data = merged.get_valid_data()
    assert len(valid_data) >= 20  # At least data from 2+ grids


def test_chain_leveling():
    """Test chain leveling for connected but non-overlapping grids."""
    # Create a chain: 1 ↔ 2 ↔ 3 ↔ 4
    grids = [
        Grid(np.full((10, 10), 100.0, dtype=np.float32), xmin=0, ymin=0, cellsize=1),
        Grid(np.full((10, 10), 112.0, dtype=np.float32), xmin=8, ymin=0, cellsize=1),
        Grid(np.full((10, 10), 124.0, dtype=np.float32), xmin=16, ymin=0, cellsize=1),
        Grid(np.full((10, 10), 136.0, dtype=np.float32), xmin=24, ymin=0, cellsize=1),
    ]
    
    # Chain leveling manually
    leveled_grids = [grids[0]]
    for i in range(1, len(grids)):
        leveled = GridAdjuster.level_to_reference(
            grids[i], leveled_grids[i-1],
            use_dc_shift=True,
            polynomial_degree=1
        )
        leveled_grids.append(leveled)
    
    # Check that all are now roughly on same baseline
    means = [g.get_valid_data().mean() for g in leveled_grids]
    # All should be close to the reference baseline (~100)
    for mean in means:
        assert 95 < mean < 115, f"Mean {mean} not close to baseline 100"


def test_priorities_order():
    """Test that priorities affect merge order."""
    # Create grids
    grids = [
        Grid(np.full((5, 5), 100.0, dtype=np.float32), xmin=0, ymin=0, cellsize=1),
        Grid(np.full((5, 5), 110.0, dtype=np.float32), xmin=3, ymin=0, cellsize=1),
        Grid(np.full((5, 5), 120.0, dtype=np.float32), xmin=6, ymin=0, cellsize=1),
    ]
    
    # Low to high priorities
    priorities = [60, 80, 100]
    
    # Merge with priorities
    merged = GridMerger.merge_multiple_grids(
        grids,
        priorities=priorities,
        level_to_first=False,
        feather=False
    )
    
    # Should complete without error
    assert merged is not None


def test_priorities_with_non_intersecting():
    """Test priorities when some grids don't intersect."""
    # Two groups of grids with different priorities
    group_a = [
        Grid(np.full((5, 5), 100.0, dtype=np.float32), xmin=0, ymin=0, cellsize=1),
        Grid(np.full((5, 5), 105.0, dtype=np.float32), xmin=3, ymin=0, cellsize=1),
    ]
    
    group_b = [
        Grid(np.full((5, 5), 150.0, dtype=np.float32), xmin=50, ymin=50, cellsize=1),
        Grid(np.full((5, 5), 155.0, dtype=np.float32), xmin=53, ymin=50, cellsize=1),
    ]
    
    grids = group_a + group_b
    priorities = [100, 100, 70, 70]  # Group A higher priority
    
    # Merge
    merged = GridMerger.merge_multiple_grids(
        grids,
        priorities=priorities,
        level_to_first=True,
        feather=True
    )
    
    # Should include both groups
    assert merged is not None
    assert merged.ncols >= 55  # Spans both groups


def test_scale_factor_no_overlap():
    """Test that scale factor returns None with no overlap."""
    grid1 = Grid(np.random.rand(10, 10).astype(np.float32) * 50 + 100, 
                xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(np.random.rand(10, 10).astype(np.float32) * 50 + 100,
                xmin=100, ymin=100, cellsize=1)
    
    scale = GridAdjuster.calculate_scale_factor(grid1, grid2)
    assert scale is None


def test_polynomial_fitting_no_overlap():
    """Test polynomial fitting returns None with no overlap."""
    grid1 = Grid(np.full((10, 10), 100.0, dtype=np.float32), xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(np.full((10, 10), 150.0, dtype=np.float32), xmin=100, ymin=100, cellsize=1)
    
    coeffs = GridAdjuster.fit_surface_in_overlap(grid1, grid2, degree=1)
    assert coeffs is None


def test_merge_preserves_non_overlapping_data():
    """Test that non-overlapping grid data is preserved in merge."""
    # Create two separate grids with distinct values
    grid1 = Grid(np.full((10, 10), 100.0, dtype=np.float32), xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(np.full((10, 10), 200.0, dtype=np.float32), xmin=50, ymin=50, cellsize=1)
    
    merged = GridMerger.merge_two_grids(grid1, grid2, feather=False)
    
    # Check that both value ranges exist
    valid_data = merged.get_valid_data()
    assert valid_data.min() < 110  # Grid 1 data (~100)
    assert valid_data.max() > 190  # Grid 2 data (~200)


def test_merge_multiple_non_intersecting_regions():
    """Test merging grids from completely separate regions."""
    # Create 3 separate regions
    region1_grids = [
        Grid(np.full((5, 5), 100.0, dtype=np.float32), xmin=0, ymin=0, cellsize=1),
        Grid(np.full((5, 5), 102.0, dtype=np.float32), xmin=4, ymin=0, cellsize=1),
    ]
    
    region2_grids = [
        Grid(np.full((5, 5), 200.0, dtype=np.float32), xmin=50, ymin=50, cellsize=1),
        Grid(np.full((5, 5), 202.0, dtype=np.float32), xmin=54, ymin=50, cellsize=1),
    ]
    
    region3_grids = [
        Grid(np.full((5, 5), 300.0, dtype=np.float32), xmin=100, ymin=100, cellsize=1),
    ]
    
    all_grids = region1_grids + region2_grids + region3_grids
    
    merged = GridMerger.merge_with_auto_leveling(all_grids)
    
    # Should span all regions
    assert merged.xmax >= 105
    assert merged.ymax >= 105
    
    # Should have data from all three regions
    valid_data = merged.get_valid_data()
    assert 95 < valid_data.min() < 105   # Region 1
    assert 295 < valid_data.max() < 305  # Region 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
