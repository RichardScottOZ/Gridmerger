"""
Demonstration of batch grid reprojection utilities.

This example shows how to use the utilities in gridmerge.utils to:
1. Inspect multiple grids with different CRS and resolutions
2. Select a reference grid
3. Reproject all grids to match the reference
4. Merge the aligned grids

This is particularly useful when working with heterogeneous datasets from
different surveys, regions, or time periods.
"""

import numpy as np
import os
import sys

# Add parent directory to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gridmerge import Grid
from gridmerge.utils import inspect_grids, reproject_grids_to_reference, prepare_grids_for_merge


def create_test_grids_with_different_crs():
    """
    Create test grids simulating surveys with different CRS and resolutions.
    
    This simulates a common real-world scenario:
    - Survey A: UTM Zone 55, 100m resolution (reference quality)
    - Survey B: UTM Zone 55, 50m resolution (high resolution)
    - Survey C: UTM Zone 54, 200m resolution (older survey)
    """
    print("\n" + "="*80)
    print("DEMO 1: Creating Test Grids with Different CRS/Resolutions")
    print("="*80)
    
    # Create temporary directory
    output_dir = "/tmp/gridmerge_batch_demo"
    os.makedirs(output_dir, exist_ok=True)
    
    # Grid A: UTM Zone 55, 100m resolution
    # Simulates central reference survey
    print("\nCreating Grid A: UTM55, 100m resolution (reference)")
    nx_a, ny_a = 100, 100
    x_a = np.linspace(500000, 510000, nx_a)  # UTM easting
    y_a = np.linspace(6500000, 6510000, ny_a)  # UTM northing
    X_a, Y_a = np.meshgrid(x_a, y_a)
    
    # Create synthetic magnetic data
    data_a = 52000 + 100 * np.sin(X_a / 2000) * np.cos(Y_a / 3000)
    
    grid_a = Grid(
        data=data_a,
        xmin=x_a.min() - 50,  # Half cellsize
        ymin=y_a.min() - 50,
        cellsize=100.0,
        metadata={'crs': 'EPSG:32755'}  # UTM Zone 55S
    )
    
    path_a = os.path.join(output_dir, "survey_a_utm55_100m.tif")
    grid_a.write(path_a)
    print(f"  Created: {path_a}")
    print(f"  CRS: EPSG:32755 (UTM 55S)")
    print(f"  Resolution: 100m")
    
    # Grid B: UTM Zone 55, 50m resolution
    # Simulates high-resolution modern survey overlapping Grid A
    print("\nCreating Grid B: UTM55, 50m resolution (high-res)")
    nx_b, ny_b = 150, 150
    x_b = np.linspace(505000, 512500, nx_b)  # Overlaps with A
    y_b = np.linspace(6502000, 6509500, ny_b)
    X_b, Y_b = np.meshgrid(x_b, y_b)
    
    # Similar but with different baseline (needs leveling)
    data_b = 52100 + 80 * np.sin(X_b / 2000) * np.cos(Y_b / 3000)
    
    grid_b = Grid(
        data=data_b,
        xmin=x_b.min() - 25,  # Half cellsize
        ymin=y_b.min() - 25,
        cellsize=50.0,
        metadata={'crs': 'EPSG:32755'}  # Same zone
    )
    
    path_b = os.path.join(output_dir, "survey_b_utm55_50m.tif")
    grid_b.write(path_b)
    print(f"  Created: {path_b}")
    print(f"  CRS: EPSG:32755 (UTM 55S)")
    print(f"  Resolution: 50m")
    
    # Grid C: UTM Zone 54, 200m resolution
    # Simulates older survey in adjacent zone
    print("\nCreating Grid C: UTM54, 200m resolution (different zone!)")
    nx_c, ny_c = 60, 60
    # Convert approximate coordinates to UTM 54
    x_c = np.linspace(700000, 712000, nx_c)  # Different zone
    y_c = np.linspace(6500000, 6512000, ny_c)
    X_c, Y_c = np.meshgrid(x_c, y_c)
    
    # Different baseline and pattern
    data_c = 51900 + 120 * np.sin(X_c / 3000) * np.cos(Y_c / 2500)
    
    grid_c = Grid(
        data=data_c,
        xmin=x_c.min() - 100,  # Half cellsize
        ymin=y_c.min() - 100,
        cellsize=200.0,
        metadata={'crs': 'EPSG:32754'}  # UTM Zone 54S (different!)
    )
    
    path_c = os.path.join(output_dir, "survey_c_utm54_200m.tif")
    grid_c.write(path_c)
    print(f"  Created: {path_c}")
    print(f"  CRS: EPSG:32754 (UTM 54S) - DIFFERENT ZONE")
    print(f"  Resolution: 200m")
    
    return [path_a, path_b, path_c], output_dir


def demo_inspect_grids(grid_files):
    """
    Demonstrate grid inspection functionality.
    """
    print("\n" + "="*80)
    print("DEMO 2: Inspecting Grids")
    print("="*80)
    
    # Inspect grids - shows table with all properties
    grid_info = inspect_grids(grid_files)
    
    print("\nInspection complete!")
    print(f"Found {len(grid_info)} grids")
    print("\nKey observations:")
    print("  - Grid 0 and 1 have same CRS (UTM 55)")
    print("  - Grid 2 has different CRS (UTM 54) - needs reprojection!")
    print("  - All grids have different resolutions")
    
    return grid_info


def demo_batch_reproject(grid_files, output_dir):
    """
    Demonstrate batch reprojection to reference grid.
    """
    print("\n" + "="*80)
    print("DEMO 3: Batch Reprojection to Reference")
    print("="*80)
    
    print("\nScenario: Reproject all grids to match Grid 0 (UTM 55, 100m)")
    print("This will:")
    print("  - Keep Grid 0 unchanged (it's the reference)")
    print("  - Resample Grid 1 from 50m to 100m")
    print("  - Reproject Grid 2 from UTM 54 to UTM 55 AND resample to 100m")
    
    aligned_dir = os.path.join(output_dir, "aligned")
    
    # Reproject all grids to match first one
    aligned_files = reproject_grids_to_reference(
        grid_files=grid_files,
        reference_index=0,  # Use first grid as reference
        output_dir=aligned_dir,
        method='bilinear'
    )
    
    print("\nBatch reprojection complete!")
    print(f"Aligned grids saved to: {aligned_dir}")
    
    # Inspect the aligned grids
    print("\n" + "-"*80)
    print("Inspecting aligned grids to verify they match:")
    print("-"*80)
    aligned_info = inspect_grids(aligned_files)
    
    print("\nVerification:")
    crs_set = set(info.get('crs', 'unknown') for info in aligned_info if 'error' not in info)
    cellsize_set = set(info.get('cellsize', 0) for info in aligned_info if 'error' not in info)
    
    if len(crs_set) == 1:
        print(f"  ✓ All grids now have same CRS: {list(crs_set)[0]}")
    else:
        print(f"  ✗ CRS mismatch: {crs_set}")
    
    if len(cellsize_set) == 1:
        print(f"  ✓ All grids now have same resolution: {list(cellsize_set)[0]}")
    else:
        print(f"  ✗ Resolution mismatch: {cellsize_set}")
    
    return aligned_files


def demo_merge_aligned_grids(aligned_files):
    """
    Demonstrate merging the aligned grids.
    """
    print("\n" + "="*80)
    print("DEMO 4: Merging Aligned Grids")
    print("="*80)
    
    from gridmerge import GridMerger
    
    print("\nNow that all grids have the same CRS and resolution,")
    print("we can merge them seamlessly with auto-leveling.")
    
    # Load aligned grids
    print("\nLoading aligned grids...")
    grids = []
    for i, filepath in enumerate(aligned_files):
        if filepath and os.path.exists(filepath):
            grid = Grid.read(filepath)
            grids.append(grid)
            print(f"  [{i}] Loaded: {os.path.basename(filepath)}")
            print(f"      CRS: {grid.metadata.get('crs', 'unknown')}")
            print(f"      Resolution: {grid.cellsize}")
    
    if not grids:
        print("ERROR: No grids to merge")
        return None
    
    # Merge with auto-leveling
    print(f"\nMerging {len(grids)} grids with auto-leveling...")
    merged = GridMerger.merge_with_auto_leveling(
        grids,
        use_dc_shift=True,
        polynomial_degree=1,
        feather_distance=5
    )
    
    print(f"\nMerge complete!")
    print(f"  Output dimensions: {merged.nrows} × {merged.ncols}")
    print(f"  Output resolution: {merged.cellsize}")
    print(f"  Output CRS: {merged.metadata.get('crs', 'unknown')}")
    
    # Save merged grid
    output_path = os.path.join(os.path.dirname(aligned_files[0]), "merged_output.tif")
    merged.write(output_path)
    print(f"\nMerged grid saved to: {output_path}")
    
    return merged, output_path


def demo_prepare_for_merge_shortcut(grid_files, output_dir):
    """
    Demonstrate the convenience function for preparing grids for merge.
    """
    print("\n" + "="*80)
    print("DEMO 5: Using prepare_grids_for_merge() Shortcut")
    print("="*80)
    
    print("\nThe prepare_grids_for_merge() function is a convenient shortcut")
    print("that combines inspection and reprojection in one call.")
    
    prepared_dir = os.path.join(output_dir, "prepared")
    
    # One-line preparation
    prepared_files = prepare_grids_for_merge(
        grid_files=grid_files,
        reference_index=0,
        output_dir=prepared_dir,
        method='bilinear'
    )
    
    print(f"\nPrepared grids saved to: {prepared_dir}")
    print("These grids are now ready for immediate merging!")
    
    # Quick merge
    from gridmerge import GridMerger
    
    grids = [Grid.read(f) for f in prepared_files if f]
    if grids:
        merged = GridMerger.merge_with_auto_leveling(grids)
        output_path = os.path.join(prepared_dir, "quick_merged.tif")
        merged.write(output_path)
        print(f"\nQuick merge saved to: {output_path}")


def main():
    """
    Run all demonstrations.
    """
    print("\n" + "="*80)
    print("BATCH GRID REPROJECTION DEMONSTRATION")
    print("="*80)
    print("\nThis demo shows how to work with heterogeneous grid datasets:")
    print("  1. Create test grids with different CRS and resolutions")
    print("  2. Inspect grid properties")
    print("  3. Batch reproject to common reference")
    print("  4. Merge aligned grids")
    print("  5. Use convenience functions")
    
    # Check if rioxarray is available
    try:
        import rioxarray  # noqa: F401
        print("\n✓ rioxarray is installed - all features available")
    except ImportError:
        print("\n✗ rioxarray not installed")
        print("  Install with: pip install rioxarray")
        print("  Some features will not be available in this demo")
        return
    
    # Demo 1: Create test data
    grid_files, output_dir = create_test_grids_with_different_crs()
    
    # Demo 2: Inspect grids
    grid_info = demo_inspect_grids(grid_files)
    
    # Demo 3: Batch reproject
    aligned_files = demo_batch_reproject(grid_files, output_dir)
    
    # Demo 4: Merge aligned grids
    merged, merged_path = demo_merge_aligned_grids(aligned_files)
    
    # Demo 5: Shortcut function
    demo_prepare_for_merge_shortcut(grid_files, output_dir)
    
    print("\n" + "="*80)
    print("ALL DEMONSTRATIONS COMPLETE")
    print("="*80)
    print(f"\nOutput files created in: {output_dir}")
    print("\nKey takeaways:")
    print("  1. inspect_grids() - See all grid properties at a glance")
    print("  2. reproject_grids_to_reference() - Batch align to reference")
    print("  3. prepare_grids_for_merge() - One-line preparation")
    print("  4. After alignment, GridMerger.merge_with_auto_leveling() works seamlessly")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
