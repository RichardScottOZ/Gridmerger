"""
Example: Creating and merging synthetic grids.

This example demonstrates how to create synthetic grids and merge them
using the GridMerge package.
"""

import numpy as np
from gridmerge import Grid, GridMerger


def create_synthetic_grid(xmin, ymin, nrows, ncols, cellsize, 
                         base_value=100, gradient_x=0.1, gradient_y=0.05,
                         noise_level=5):
    """
    Create a synthetic grid with a gradient and noise.
    
    Args:
        xmin, ymin: Grid origin
        nrows, ncols: Grid dimensions
        cellsize: Cell size
        base_value: Base value for the grid
        gradient_x: Gradient in X direction
        gradient_y: Gradient in Y direction
        noise_level: Standard deviation of random noise
    
    Returns:
        Grid object
    """
    # Create coordinate arrays
    rows, cols = np.mgrid[0:nrows, 0:ncols]
    x = xmin + cols * cellsize
    y = ymin + rows * cellsize
    
    # Create gradient
    data = base_value + gradient_x * x + gradient_y * y
    
    # Add noise
    noise = np.random.normal(0, noise_level, data.shape)
    data += noise
    
    return Grid(data, xmin, ymin, cellsize, nodata_value=-99999.0)


def main():
    """Main example function."""
    print("GridMerge Example: Creating and Merging Synthetic Grids")
    print("=" * 60)
    
    # Create three overlapping synthetic grids
    print("\n1. Creating synthetic grids...")
    
    grid1 = create_synthetic_grid(
        xmin=0, ymin=0, nrows=100, ncols=100, cellsize=10,
        base_value=100, gradient_x=0.1, gradient_y=0.05
    )
    print(f"   Grid 1: {grid1.nrows}x{grid1.ncols}, bounds={grid1.bounds}")
    
    # Grid 2 overlaps with Grid 1 and has a different baseline
    grid2 = create_synthetic_grid(
        xmin=500, ymin=0, nrows=100, ncols=100, cellsize=10,
        base_value=110, gradient_x=0.12, gradient_y=0.04  # Slightly different
    )
    print(f"   Grid 2: {grid2.nrows}x{grid2.ncols}, bounds={grid2.bounds}")
    
    # Grid 3 overlaps with both
    grid3 = create_synthetic_grid(
        xmin=250, ymin=500, nrows=100, ncols=100, cellsize=10,
        base_value=105, gradient_x=0.11, gradient_y=0.045
    )
    print(f"   Grid 3: {grid3.nrows}x{grid3.ncols}, bounds={grid3.bounds}")
    
    # Calculate statistics before merging
    print("\n2. Grid statistics before merging:")
    for i, grid in enumerate([grid1, grid2, grid3], 1):
        data = grid.get_valid_data()
        print(f"   Grid {i}: mean={data.mean():.2f}, std={data.std():.2f}")
    
    # Merge grids with automatic leveling
    print("\n3. Merging grids with automatic leveling...")
    merged = GridMerger.merge_with_auto_leveling(
        [grid1, grid2, grid3],
        polynomial_degree=1,
        feather=True
    )
    print(f"   Merged grid: {merged.nrows}x{merged.ncols}")
    print(f"   Bounds: {merged.bounds}")
    
    # Calculate statistics after merging
    merged_data = merged.get_valid_data()
    print(f"   Merged mean: {merged_data.mean():.2f}")
    print(f"   Merged std: {merged_data.std():.2f}")
    
    # Save grids (optional - requires write capability)
    print("\n4. Saving grids...")
    try:
        grid1.write_ers("/tmp/example_grid1.ers")
        grid2.write_ers("/tmp/example_grid2.ers")
        grid3.write_ers("/tmp/example_grid3.ers")
        merged.write_ers("/tmp/example_merged.ers")
        print("   Grids saved to /tmp/example_*.ers")
    except Exception as e:
        print(f"   Could not save grids: {e}")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("\nTo visualize the results, you can load the .ers files in")
    print("geophysical software like Geosoft Oasis montaj or QGIS.")


if __name__ == "__main__":
    main()
