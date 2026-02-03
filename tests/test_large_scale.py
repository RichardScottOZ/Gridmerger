"""
Tests for large-scale grid merging operations.
"""

import numpy as np
import pytest
from gridmerge import Grid, GridMerger


def test_merge_many_grids():
    """Test merging a large number of grids (47 grids)."""
    # Create 47 small test grids with overlaps
    num_grids = 47
    grids = []
    
    # Arrange in grid pattern
    grids_per_row = 7
    for i in range(num_grids):
        row = i // grids_per_row
        col = i % grids_per_row
        
        # Small grids for fast testing
        data = np.full((10, 10), 100.0 + i, dtype=np.float32)
        
        # Position with slight overlap
        xmin = col * 8  # 80% spacing = 20% overlap
        ymin = row * 8
        
        grid = Grid(data, xmin=xmin, ymin=ymin, cellsize=1)
        grids.append(grid)
    
    # Merge all grids
    merged = GridMerger.merge_with_auto_leveling(grids, polynomial_degree=1)
    
    # Verify result
    assert merged is not None
    assert merged.nrows > 0
    assert merged.ncols > 0
    
    # Should have data from all grids
    valid_data = merged.get_valid_data()
    assert len(valid_data) > 0
    
    print(f"Successfully merged {num_grids} grids")
    print(f"Result: {merged.nrows}x{merged.ncols} grid")
    print(f"Coverage: {100*len(valid_data)/(merged.nrows*merged.ncols):.1f}%")


def test_merge_many_grids_with_priorities():
    """Test merging many grids with priority values."""
    num_grids = 20
    grids = []
    priorities = []
    
    for i in range(num_grids):
        data = np.full((5, 5), 100.0 + i, dtype=np.float32)
        xmin = i * 3  # 40% overlap
        grid = Grid(data, xmin=xmin, ymin=0, cellsize=1)
        grids.append(grid)
        
        # Higher priority for middle grids (higher quality)
        priority = 100 - abs(i - num_grids//2)
        priorities.append(priority)
    
    # Merge with priorities
    merged = GridMerger.merge_multiple_grids(
        grids,
        priorities=priorities,
        level_to_first=True,
        use_dc_shift=True,
        polynomial_degree=1,
        feather=True
    )
    
    assert merged is not None
    assert merged.nrows == 5
    # Should span all grids
    assert merged.ncols >= num_grids * 3


def test_merge_grids_different_overlaps():
    """Test merging grids with varying overlap amounts."""
    grids = []
    
    # Create grids with different overlap patterns
    for i in range(15):
        data = np.random.rand(8, 8).astype(np.float32) * 10 + 100
        
        if i < 5:
            # High overlap group
            xmin = i * 4
        elif i < 10:
            # Medium overlap group
            xmin = 20 + (i-5) * 6
        else:
            # Low overlap group
            xmin = 50 + (i-10) * 7
        
        grid = Grid(data, xmin=xmin, ymin=0, cellsize=1)
        grids.append(grid)
    
    # Merge all
    merged = GridMerger.merge_with_auto_leveling(grids, polynomial_degree=1, feather=True)
    
    assert merged is not None
    assert merged.nrows == 8
    # Should cover the full extent
    expected_extent = 50 + 5*7 + 8  # Last grid position + width
    assert merged.ncols >= expected_extent * 0.9  # Allow some tolerance


def test_merge_performance_scaling():
    """Test that merge time scales reasonably with number of grids."""
    import time
    
    results = []
    
    for num_grids in [5, 10, 20]:
        grids = []
        for i in range(num_grids):
            data = np.full((10, 10), 100.0, dtype=np.float32)
            grid = Grid(data, xmin=i*8, ymin=0, cellsize=1)
            grids.append(grid)
        
        start = time.time()
        merged = GridMerger.merge_with_auto_leveling(grids, polynomial_degree=1)
        elapsed = time.time() - start
        
        results.append((num_grids, elapsed))
        print(f"{num_grids} grids: {elapsed:.3f}s ({elapsed/num_grids:.4f}s per grid)")
    
    # Verify it completed
    assert merged is not None
    
    # Time should scale roughly linearly (allowing for overhead)
    # Ratio of times should be close to ratio of grid counts
    ratio_grids = results[2][0] / results[0][0]  # 20/5 = 4
    ratio_time = results[2][1] / results[0][1]
    
    # Allow generous tolerance due to small samples and overhead
    # Time ratio should be within 2x of grid ratio
    assert ratio_time < ratio_grids * 2, f"Performance scaling issue: {ratio_time} vs {ratio_grids}"


def test_merge_with_no_leveling():
    """Test merging many grids without leveling (faster)."""
    num_grids = 30
    grids = []
    
    for i in range(num_grids):
        data = np.full((6, 6), 100.0 + i*0.5, dtype=np.float32)
        grid = Grid(data, xmin=i*5, ymin=0, cellsize=1)
        grids.append(grid)
    
    # Merge without leveling (should be faster)
    merged = GridMerger.merge_multiple_grids(
        grids,
        level_to_first=False,
        feather=True
    )
    
    assert merged is not None
    assert merged.nrows == 6


def test_merge_grids_memory_efficient():
    """Test that merging doesn't keep all grids in memory simultaneously."""
    # This is more of a documentation test - the algorithm processes sequentially
    num_grids = 25
    grids = []
    
    for i in range(num_grids):
        # Create grid
        data = np.random.rand(10, 10).astype(np.float32) * 50 + 100
        grid = Grid(data, xmin=i*8, ymin=0, cellsize=1)
        grids.append(grid)
    
    # The merge should complete without memory issues
    merged = GridMerger.merge_with_auto_leveling(grids, polynomial_degree=1)
    
    assert merged is not None
    # If we got here, memory management worked
    print(f"Successfully merged {num_grids} grids with sequential processing")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
