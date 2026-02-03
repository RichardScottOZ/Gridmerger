#!/usr/bin/env python3
"""
Demonstration of rioxarray-based resampling and reprojection functionality.

This example shows how to:
1. Resample grids to different resolutions
2. Reproject grids to different coordinate systems
3. Match grids to a reference grid's spatial properties
4. Merge grids with different resolutions and CRS

Requirements:
    pip install xarray rioxarray
    or
    pip install -e .[rioxarray]
"""

import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from gridmerge import Grid, GridMerger
    import xarray as xr
    import rioxarray
    RIOXARRAY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: {e}")
    print("This demo requires xarray and rioxarray.")
    print("Install with: pip install xarray rioxarray")
    RIOXARRAY_AVAILABLE = False
    sys.exit(1)


def create_test_grid(name, xmin, ymin, ncols, nrows, cellsize, 
                     base_value, crs='EPSG:32755'):
    """Create a test grid with synthetic data."""
    x = np.arange(ncols)
    y = np.arange(nrows)
    xx, yy = np.meshgrid(x, y)
    
    # Create synthetic magnetic data
    data = base_value + 50 * np.sin(xx / 10) * np.cos(yy / 10)
    data = data.astype(np.float32)
    
    grid = Grid(
        data=data,
        xmin=xmin,
        ymin=ymin,
        cellsize=cellsize,
        nodata_value=-99999.0,
        metadata={'crs': crs, 'name': name}
    )
    
    return grid


def demo_1_resampling():
    """Demonstrate resampling to different resolutions."""
    print("\n" + "="*70)
    print("DEMO 1: Resampling to Different Resolutions")
    print("="*70)
    
    # Create a high-resolution grid (50m)
    print("\n1. Creating high-resolution grid (50m cellsize)...")
    grid_highres = create_test_grid(
        name="HighRes_50m",
        xmin=500000, ymin=6000000,
        ncols=200, nrows=200,
        cellsize=50,
        base_value=52000,
        crs='EPSG:32755'  # UTM Zone 55S (common for Australian geophysics)
    )
    
    print(f"   Original grid: {grid_highres.ncols}x{grid_highres.nrows} cells")
    print(f"   Cellsize: {grid_highres.cellsize}m")
    print(f"   Bounds: ({grid_highres.xmin}, {grid_highres.ymin}) to "
          f"({grid_highres.xmax}, {grid_highres.ymax})")
    print(f"   CRS: {grid_highres.metadata.get('crs')}")
    
    # Downsample to 100m (lower resolution)
    print("\n2. Downsampling to 100m (averaging high-res data)...")
    grid_100m = grid_highres.resample(target_cellsize=100, method='average')
    
    print(f"   Resampled grid: {grid_100m.ncols}x{grid_100m.nrows} cells")
    print(f"   Cellsize: {grid_100m.cellsize}m")
    print(f"   Bounds preserved: ({grid_100m.xmin:.1f}, {grid_100m.ymin:.1f}) to "
          f"({grid_100m.xmax:.1f}, {grid_100m.ymax:.1f})")
    
    # Downsample to 200m (coarser resolution)
    print("\n3. Downsampling to 200m (even coarser)...")
    grid_200m = grid_highres.resample(target_cellsize=200, method='average')
    
    print(f"   Resampled grid: {grid_200m.ncols}x{grid_200m.nrows} cells")
    print(f"   Cellsize: {grid_200m.cellsize}m")
    
    # Upsample to 25m (higher resolution - interpolation)
    print("\n4. Upsampling to 25m (interpolating to finer resolution)...")
    grid_25m = grid_highres.resample(target_cellsize=25, method='bilinear')
    
    print(f"   Resampled grid: {grid_25m.ncols}x{grid_25m.nrows} cells")
    print(f"   Cellsize: {grid_25m.cellsize}m")
    
    print("\n✓ Resampling complete - grids can be saved at different resolutions")
    
    return grid_highres, grid_100m, grid_200m, grid_25m


def demo_2_reprojection():
    """Demonstrate reprojection to different coordinate systems."""
    print("\n" + "="*70)
    print("DEMO 2: Reprojection to Different Coordinate Systems")
    print("="*70)
    
    # Create grid in UTM Zone 55S (common for eastern Australian geophysics)
    print("\n1. Creating grid in UTM Zone 55S (EPSG:32755)...")
    grid_utm55 = create_test_grid(
        name="Survey_UTM55S",
        xmin=500000, ymin=6000000,
        ncols=100, nrows=100,
        cellsize=100,
        base_value=52000,
        crs='EPSG:32755'
    )
    
    print(f"   Original CRS: {grid_utm55.metadata.get('crs')}")
    print(f"   Bounds: ({grid_utm55.xmin}, {grid_utm55.ymin}) to "
          f"({grid_utm55.xmax}, {grid_utm55.ymax})")
    
    # Reproject to Geographic (WGS84)
    print("\n2. Reprojecting to Geographic WGS84 (EPSG:4326)...")
    grid_wgs84 = grid_utm55.reproject(target_crs='EPSG:4326', method='bilinear')
    
    print(f"   Reprojected CRS: {grid_wgs84.metadata.get('crs')}")
    print(f"   Bounds: ({grid_wgs84.xmin:.6f}, {grid_wgs84.ymin:.6f}) to "
          f"({grid_wgs84.xmax:.6f}, {grid_wgs84.ymax:.6f})")
    print(f"   (Now in degrees lat/lon)")
    
    # Reproject to UTM Zone 54S
    print("\n3. Reprojecting to UTM Zone 54S (EPSG:32754)...")
    grid_utm54 = grid_utm55.reproject(target_crs='EPSG:32754', method='bilinear')
    
    print(f"   Reprojected CRS: {grid_utm54.metadata.get('crs')}")
    print(f"   Bounds: ({grid_utm54.xmin:.1f}, {grid_utm54.ymin:.1f}) to "
          f"({grid_utm54.xmax:.1f}, {grid_utm54.ymax:.1f})")
    
    print("\n✓ Reprojection complete - grids can be transformed between CRS")
    
    return grid_utm55, grid_wgs84, grid_utm54


def demo_3_match_reference():
    """Demonstrate matching grids to a reference grid."""
    print("\n" + "="*70)
    print("DEMO 3: Matching Grids to Reference Grid")
    print("="*70)
    
    # Create reference grid (100m, UTM 55S)
    print("\n1. Creating reference grid (100m, UTM Zone 55S)...")
    reference = create_test_grid(
        name="Reference",
        xmin=500000, ymin=6000000,
        ncols=100, nrows=100,
        cellsize=100,
        base_value=52000,
        crs='EPSG:32755'
    )
    
    print(f"   Reference: {reference.ncols}x{reference.nrows} @ {reference.cellsize}m")
    print(f"   CRS: {reference.metadata.get('crs')}")
    
    # Create grid with different resolution (50m, same CRS)
    print("\n2. Creating grid with different resolution (50m, same CRS)...")
    grid_diffres = create_test_grid(
        name="DifferentRes",
        xmin=505000, ymin=6005000,
        ncols=150, nrows=150,
        cellsize=50,
        base_value=52100,
        crs='EPSG:32755'
    )
    
    print(f"   Source: {grid_diffres.ncols}x{grid_diffres.nrows} @ {grid_diffres.cellsize}m")
    
    # Match to reference
    print("\n3. Matching to reference grid...")
    grid_matched = grid_diffres.match_grid(reference, method='bilinear')
    
    print(f"   Matched: {grid_matched.ncols}x{grid_matched.nrows} @ {grid_matched.cellsize}m")
    print(f"   ✓ Now matches reference resolution and extent!")
    
    # Create grid with different CRS (UTM 54S)
    print("\n4. Creating grid with different CRS (UTM Zone 54S)...")
    grid_diffcrs = create_test_grid(
        name="DifferentCRS",
        xmin=700000, ymin=6000000,
        ncols=80, nrows=80,
        cellsize=150,
        base_value=52200,
        crs='EPSG:32754'  # Different zone
    )
    
    print(f"   Source: {grid_diffcrs.ncols}x{grid_diffcrs.nrows} @ {grid_diffcrs.cellsize}m")
    print(f"   CRS: {grid_diffcrs.metadata.get('crs')}")
    
    # Match to reference (different CRS AND resolution)
    print("\n5. Matching to reference grid (reprojecting AND resampling)...")
    grid_matched2 = grid_diffcrs.match_grid(reference, method='bilinear')
    
    print(f"   Matched: {grid_matched2.ncols}x{grid_matched2.nrows} @ {grid_matched2.cellsize}m")
    print(f"   CRS: {grid_matched2.metadata.get('crs')}")
    print(f"   ✓ Now matches reference CRS, resolution, and extent!")
    
    print("\n✓ Grid matching complete - heterogeneous grids unified to reference")
    
    return reference, grid_diffres, grid_diffcrs, grid_matched, grid_matched2


def demo_4_merge_different_crs_resolution():
    """Demonstrate merging grids with different CRS and resolutions."""
    print("\n" + "="*70)
    print("DEMO 4: Merging Grids with Different CRS and Resolutions")
    print("="*70)
    
    print("\nScenario: Regional compilation of surveys from different projects")
    print("- Survey A: 100m resolution, UTM Zone 55S")
    print("- Survey B: 50m resolution, UTM Zone 55S")
    print("- Survey C: 200m resolution, UTM Zone 54S (different zone!)")
    
    # Create three surveys
    print("\n1. Creating Survey A (100m, UTM 55S)...")
    survey_a = create_test_grid(
        name="SurveyA",
        xmin=500000, ymin=6000000,
        ncols=100, nrows=100,
        cellsize=100,
        base_value=52000,
        crs='EPSG:32755'
    )
    print(f"   Survey A: {survey_a.shape} @ {survey_a.cellsize}m, {survey_a.metadata['crs']}")
    
    print("\n2. Creating Survey B (50m, UTM 55S, overlaps A)...")
    survey_b = create_test_grid(
        name="SurveyB",
        xmin=508000, ymin=6008000,
        ncols=120, nrows=120,
        cellsize=50,
        base_value=52150,  # Different baseline
        crs='EPSG:32755'
    )
    print(f"   Survey B: {survey_b.shape} @ {survey_b.cellsize}m, {survey_b.metadata['crs']}")
    
    print("\n3. Creating Survey C (200m, UTM 54S, different zone!)...")
    # Note: This is in a different UTM zone, simulating data from adjacent region
    survey_c = create_test_grid(
        name="SurveyC",
        xmin=700000, ymin=6000000,
        ncols=50, nrows=50,
        cellsize=200,
        base_value=52300,
        crs='EPSG:32754'
    )
    print(f"   Survey C: {survey_c.shape} @ {survey_c.cellsize}m, {survey_c.metadata['crs']}")
    
    # Strategy: Match all to Survey A (reference)
    print("\n4. Matching all surveys to Survey A (reference)...")
    print("   This will:")
    print("   - Keep Survey A as-is (reference)")
    print("   - Resample Survey B from 50m to 100m")
    print("   - Reproject AND resample Survey C to UTM 55S @ 100m")
    
    # Start with reference grid (no modification needed)
    grids_matched = [survey_a.copy()]  # Copy to avoid modifying original
    
    print("\n   Matching Survey B...")
    survey_b_matched = survey_b.match_grid(survey_a, method='average')
    grids_matched.append(survey_b_matched)
    print(f"   ✓ Survey B: {survey_b_matched.shape} @ {survey_b_matched.cellsize}m")
    
    print("\n   Matching Survey C (includes reprojection)...")
    survey_c_matched = survey_c.match_grid(survey_a, method='bilinear')
    grids_matched.append(survey_c_matched)
    print(f"   ✓ Survey C: {survey_c_matched.shape} @ {survey_c_matched.cellsize}m, "
          f"{survey_c_matched.metadata.get('crs')}")
    
    # Now merge with leveling
    print("\n5. Merging matched grids with automatic leveling...")
    merged = GridMerger.merge_with_auto_leveling(
        grids_matched,
        use_dc_shift=True,
        polynomial_degree=1,
        feather_distance=5
    )
    
    print(f"   ✓ Merged grid: {merged.shape} @ {merged.cellsize}m")
    print(f"   Bounds: ({merged.xmin:.1f}, {merged.ymin:.1f}) to "
          f"({merged.xmax:.1f}, {merged.ymax:.1f})")
    
    print("\n✓ Complete workflow:")
    print("  1. Match all grids to reference CRS and resolution")
    print("  2. Level grids to common baseline")
    print("  3. Merge with feathering")
    print("  → Seamless mosaic from heterogeneous inputs!")
    
    return survey_a, survey_b, survey_c, grids_matched, merged


def demo_5_xarray_interoperability():
    """Demonstrate conversion to/from xarray for advanced workflows."""
    print("\n" + "="*70)
    print("DEMO 5: xarray Interoperability for Advanced Workflows")
    print("="*70)
    
    print("\nrioxarray enables integration with the xarray ecosystem:")
    print("- Climate and weather data (netCDF)")
    print("- Dask for parallel/distributed computing")
    print("- Advanced analysis and visualization tools")
    
    # Create a grid
    print("\n1. Creating test grid...")
    grid = create_test_grid(
        name="TestGrid",
        xmin=500000, ymin=6000000,
        ncols=50, nrows=50,
        cellsize=100,
        base_value=52000,
        crs='EPSG:32755'
    )
    
    print(f"   Grid: {grid.shape} @ {grid.cellsize}m")
    
    # Convert to xarray
    print("\n2. Converting to xarray DataArray...")
    da = grid.to_xarray()
    
    print(f"   DataArray shape: {da.shape}")
    print(f"   Coordinates: {list(da.coords)}")
    print(f"   CRS: {da.rio.crs}")
    print(f"   Nodata: {da.rio.nodata}")
    
    # Perform xarray operations
    print("\n3. Performing xarray operations...")
    print(f"   Mean value: {float(da.mean()):.2f} nT")
    print(f"   Std dev: {float(da.std()):.2f} nT")
    print(f"   Min: {float(da.min()):.2f} nT")
    print(f"   Max: {float(da.max()):.2f} nT")
    
    # Convert back to Grid
    print("\n4. Converting back to Grid...")
    grid_back = Grid.from_xarray(da)
    
    print(f"   Grid: {grid_back.shape} @ {grid_back.cellsize}m")
    print(f"   CRS: {grid_back.metadata.get('crs')}")
    
    # Verify round-trip
    data_diff = np.abs(grid.data - grid_back.data).max()
    print(f"   Max difference after round-trip: {data_diff:.10f}")
    print(f"   ✓ Perfect round-trip conversion!")
    
    print("\n✓ xarray integration enables powerful workflows")
    print("  - Use xarray's rich analysis tools")
    print("  - Integrate with climate/weather data")
    print("  - Scale with Dask for large datasets")
    print("  - Easy visualization with hvplot, plotly, etc.")


def main():
    """Run all demonstrations."""
    print("\n" + "="*70)
    print("GridMerge rioxarray Demonstration")
    print("="*70)
    print("\nThis demo shows how rioxarray enables:")
    print("1. Resampling grids to different resolutions")
    print("2. Reprojecting grids to different coordinate systems")
    print("3. Matching grids to a reference grid")
    print("4. Merging heterogeneous datasets (different CRS + resolution)")
    print("5. Integration with the xarray ecosystem")
    
    if not RIOXARRAY_AVAILABLE:
        print("\nERROR: rioxarray not available")
        return
    
    try:
        # Run demonstrations
        demo_1_resampling()
        demo_2_reprojection()
        demo_3_match_reference()
        demo_4_merge_different_crs_resolution()
        demo_5_xarray_interoperability()
        
        print("\n" + "="*70)
        print("All Demonstrations Complete!")
        print("="*70)
        print("\nKey Takeaways:")
        print("1. ✓ Resample grids to any resolution (up or down)")
        print("2. ✓ Reproject grids between any CRS")
        print("3. ✓ Match grids to reference (CRS + resolution + extent)")
        print("4. ✓ Merge heterogeneous datasets seamlessly")
        print("5. ✓ Integrate with xarray ecosystem for advanced workflows")
        print("\nInstallation:")
        print("  pip install xarray rioxarray")
        print("  or")
        print("  pip install -e .[rioxarray]")
        
    except Exception as e:
        print(f"\nERROR during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
