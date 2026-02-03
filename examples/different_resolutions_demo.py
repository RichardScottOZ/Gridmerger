"""
Demonstration of how GridMerge handles grids with different resolutions.

This example shows:
1. What happens when merging grids with different cellsizes
2. The problems that arise
3. How to properly resample before merging
"""

import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gridmerge import Grid, GridMerger


def create_test_grid(cellsize, xmin, ymin, ncols, nrows, base_value):
    """Create a test grid with given cellsize."""
    # Create data with some variation
    data = np.random.randn(nrows, ncols) * 5 + base_value
    return Grid(
        data=data,
        xmin=xmin,
        ymin=ymin,
        cellsize=cellsize,
        nodata_value=-99999
    )


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80 + "\n")


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


print_header("DIFFERENT RESOLUTIONS DEMONSTRATION")

print("""
This demo shows what happens when you merge grids with different resolutions.

GridMerge assumes all grids have the same cellsize. When they don't:
  • Output uses the FIRST grid's cellsize
  • Subsequent grids are placed directly without resampling
  • This causes misalignment and incorrect results

RECOMMENDATION: Always resample grids to a common resolution before merging!
""")

# ============================================================================
# DEMO 1: Different Resolutions - The Problem
# ============================================================================

print_section("DEMO 1: Merging Grids with Different Resolutions")

print("\nCreating test grids:\n")

# Grid 1: Coarse resolution (100m)
grid1_100m = create_test_grid(
    cellsize=100,
    xmin=0,
    ymin=0,
    ncols=50,
    nrows=50,
    base_value=52000
)

print(f"Grid 1 (Reference):")
print(f"  Cellsize: {grid1_100m.cellsize}m")
print(f"  Dimensions: {grid1_100m.ncols} x {grid1_100m.nrows}")
print(f"  Coverage: {grid1_100m.xmax - grid1_100m.xmin}m x {grid1_100m.ymax - grid1_100m.ymin}m")
print(f"  Extent: ({grid1_100m.xmin}, {grid1_100m.ymin}) to ({grid1_100m.xmax}, {grid1_100m.ymax})")
print(f"  Mean value: {grid1_100m.data.mean():.1f}")

# Grid 2: Fine resolution (50m), overlaps Grid 1
grid2_50m = create_test_grid(
    cellsize=50,
    xmin=4000,
    ymin=0,
    ncols=100,
    nrows=100,
    base_value=52150
)

print(f"\nGrid 2 (High Resolution):")
print(f"  Cellsize: {grid2_50m.cellsize}m (DIFFERENT from Grid 1!)")
print(f"  Dimensions: {grid2_50m.ncols} x {grid2_50m.nrows}")
print(f"  Coverage: {grid2_50m.xmax - grid2_50m.xmin}m x {grid2_50m.ymax - grid2_50m.ymin}m")
print(f"  Extent: ({grid2_50m.xmin}, {grid2_50m.ymin}) to ({grid2_50m.xmax}, {grid2_50m.ymax})")
print(f"  Mean value: {grid2_50m.data.mean():.1f}")

print(f"\n⚠️  WARNING: Grid resolutions differ!")
print(f"  Grid 1: {grid1_100m.cellsize}m")
print(f"  Grid 2: {grid2_50m.cellsize}m")
print(f"  Ratio: {grid1_100m.cellsize / grid2_50m.cellsize:.1f}x")

print("\nAttempting to merge...")

try:
    merged_wrong = GridMerger.merge_two_grids(grid1_100m, grid2_50m)
    
    print(f"\n✗ Merge completed, but result may be incorrect!")
    print(f"  Output cellsize: {merged_wrong.cellsize}m (uses Grid 1's cellsize)")
    print(f"  Output dimensions: {merged_wrong.ncols} x {merged_wrong.nrows}")
    print(f"  Coverage: {merged_wrong.xmax - merged_wrong.xmin}m x {merged_wrong.ymax - merged_wrong.ymin}m")
    
    print("\n⚠️  PROBLEM:")
    print("  • Grid 2 has 50m cells, but output grid has 100m cells")
    print("  • Grid 2's data is placed as-is into the 100m grid")
    print("  • 4 cells from Grid 2 (50m each) should map to 1 cell in output (100m)")
    print("  • Instead, they may not align properly")
    print("  • Result: Misaligned data, potential artifacts")
    
except Exception as e:
    print(f"\n✗ Error: {e}")

# ============================================================================
# DEMO 2: Manual Resampling Solution
# ============================================================================

print_section("DEMO 2: Correct Approach - Resample Before Merging")

print("\nResampling Grid 2 from 50m to 100m...\n")

# Simple resampling using scipy
from scipy import ndimage

# Calculate zoom factor (downsampling: 50m → 100m = 0.5x)
zoom_factor = grid2_50m.cellsize / grid1_100m.cellsize
print(f"Zoom factor: {zoom_factor} (downsampling from 50m to 100m)")

# Resample data (order=1 for bilinear interpolation)
resampled_data = ndimage.zoom(grid2_50m.data, zoom_factor, order=1)

# Create new grid with resampled data
grid2_100m = Grid(
    data=resampled_data,
    xmin=grid2_50m.xmin,
    ymin=grid2_50m.ymin,
    cellsize=grid1_100m.cellsize,  # Now matches Grid 1!
    nodata_value=grid2_50m.nodata_value,
    metadata=grid2_50m.metadata.copy()
)

print(f"Grid 2 (Resampled):")
print(f"  Original cellsize: {grid2_50m.cellsize}m")
print(f"  New cellsize: {grid2_100m.cellsize}m")
print(f"  Original dimensions: {grid2_50m.ncols} x {grid2_50m.nrows}")
print(f"  New dimensions: {grid2_100m.ncols} x {grid2_100m.nrows}")
print(f"  Mean value: {grid2_100m.data.mean():.1f}")

print("\n✓ Resolutions now match!")
print(f"  Grid 1: {grid1_100m.cellsize}m")
print(f"  Grid 2: {grid2_100m.cellsize}m")

print("\nMerging resampled grids...")

merged_correct = GridMerger.merge_two_grids(grid1_100m, grid2_100m)

print(f"\n✓ Merge successful!")
print(f"  Output cellsize: {merged_correct.cellsize}m")
print(f"  Output dimensions: {merged_correct.ncols} x {merged_correct.nrows}")
print(f"  Coverage: {merged_correct.xmax - merged_correct.xmin}m x {merged_correct.ymax - merged_correct.ymin}m")
print(f"  Mean value: {merged_correct.data[merged_correct.data != merged_correct.nodata_value].mean():.1f}")

# ============================================================================
# DEMO 3: Multiple Different Resolutions
# ============================================================================

print_section("DEMO 3: Multiple Grids with Different Resolutions")

print("\nScenario: Regional compilation with 3 surveys:\n")

# Survey A: 200m resolution
survey_a_200m = create_test_grid(
    cellsize=200,
    xmin=0,
    ymin=0,
    ncols=30,
    nrows=30,
    base_value=52000
)

print(f"Survey A (2005):")
print(f"  Cellsize: {survey_a_200m.cellsize}m")
print(f"  Dimensions: {survey_a_200m.ncols} x {survey_a_200m.nrows}")
print(f"  Coverage: {(survey_a_200m.xmax - survey_a_200m.xmin)/1000:.1f}km x {(survey_a_200m.ymax - survey_a_200m.ymin)/1000:.1f}km")

# Survey B: 100m resolution
survey_b_100m = create_test_grid(
    cellsize=100,
    xmin=5000,
    ymin=0,
    ncols=60,
    nrows=60,
    base_value=52150
)

print(f"\nSurvey B (2010):")
print(f"  Cellsize: {survey_b_100m.cellsize}m")
print(f"  Dimensions: {survey_b_100m.ncols} x {survey_b_100m.nrows}")
print(f"  Coverage: {(survey_b_100m.xmax - survey_b_100m.xmin)/1000:.1f}km x {(survey_b_100m.ymax - survey_b_100m.ymin)/1000:.1f}km")

# Survey C: 50m resolution (high-res)
survey_c_50m = create_test_grid(
    cellsize=50,
    xmin=10000,
    ymin=0,
    ncols=120,
    nrows=120,
    base_value=52100
)

print(f"\nSurvey C (2020, high-resolution):")
print(f"  Cellsize: {survey_c_50m.cellsize}m")
print(f"  Dimensions: {survey_c_50m.ncols} x {survey_c_50m.nrows}")
print(f"  Coverage: {(survey_c_50m.xmax - survey_c_50m.xmin)/1000:.1f}km x {(survey_c_50m.ymax - survey_c_50m.ymin)/1000:.1f}km")

print(f"\n⚠️  Three different resolutions: 200m, 100m, 50m")

print("\nChoosing target resolution: 100m (balanced)")
print("  • 50m would preserve Survey C detail but create very large output")
print("  • 200m would be fast but lose detail from Surveys B and C")
print("  • 100m is a good compromise")

target_cellsize = 100

print(f"\nResampling all surveys to {target_cellsize}m...\n")

# Resample Survey A (200m → 100m, upsampling)
zoom_a = survey_a_200m.cellsize / target_cellsize
data_a_100m = ndimage.zoom(survey_a_200m.data, zoom_a, order=1)
survey_a_100m = Grid(
    data=data_a_100m,
    xmin=survey_a_200m.xmin,
    ymin=survey_a_200m.ymin,
    cellsize=target_cellsize,
    nodata_value=survey_a_200m.nodata_value
)
print(f"Survey A: {survey_a_200m.cellsize}m → {survey_a_100m.cellsize}m (upsampled {zoom_a}x)")

# Survey B already at 100m
survey_b_100m_copy = survey_b_100m.copy()
print(f"Survey B: {survey_b_100m.cellsize}m (no resampling needed)")

# Resample Survey C (50m → 100m, downsampling)
zoom_c = survey_c_50m.cellsize / target_cellsize
data_c_100m = ndimage.zoom(survey_c_50m.data, zoom_c, order=1)
survey_c_100m = Grid(
    data=data_c_100m,
    xmin=survey_c_50m.xmin,
    ymin=survey_c_50m.ymin,
    cellsize=target_cellsize,
    nodata_value=survey_c_50m.nodata_value
)
print(f"Survey C: {survey_c_50m.cellsize}m → {survey_c_100m.cellsize}m (downsampled {zoom_c}x)")

print("\n✓ All surveys now at same resolution!")

# Verify
cellsizes = [survey_a_100m.cellsize, survey_b_100m_copy.cellsize, survey_c_100m.cellsize]
assert len(set(cellsizes)) == 1, "Resolutions must match!"
print(f"  All cellsizes: {cellsizes}")

print("\nMerging all three surveys...")

grids = [survey_a_100m, survey_b_100m_copy, survey_c_100m]
merged_regional = GridMerger.merge_multiple_grids(grids, level_to_first=True)

print(f"\n✓ Regional compilation complete!")
print(f"  Output cellsize: {merged_regional.cellsize}m")
print(f"  Output dimensions: {merged_regional.ncols} x {merged_regional.nrows}")
print(f"  Coverage: {(merged_regional.xmax - merged_regional.xmin)/1000:.1f}km x {(merged_regional.ymax - merged_regional.ymin)/1000:.1f}km")

valid_data = merged_regional.data[merged_regional.data != merged_regional.nodata_value]
print(f"  Value range: {valid_data.min():.1f} to {valid_data.max():.1f}")
print(f"  Mean value: {valid_data.mean():.1f}")

# Save if output directory exists
output_file = '/tmp/regional_compilation_100m.asc'
try:
    merged_regional.write(output_file)
    print(f"\n✓ Saved to: {output_file}")
except Exception as e:
    print(f"\n  Could not save output: {e}")

# ============================================================================
# DEMO 4: Resolution Strategy Comparison
# ============================================================================

print_section("DEMO 4: Resolution Strategy Comparison")

print("\nComparing different target resolution strategies:\n")

# Create test grids with different resolutions
test_grid_200m = create_test_grid(200, 0, 0, 25, 25, 52000)
test_grid_100m = create_test_grid(100, 4500, 0, 50, 50, 52100)
test_grid_50m = create_test_grid(50, 9000, 0, 100, 100, 52050)

strategies = [
    ("Coarsest (200m)", 200),
    ("Median (100m)", 100),
    ("Finest (50m)", 50)
]

print("Strategy Comparison:")
print("-" * 80)
print(f"{'Strategy':<20} {'Output Size':<15} {'File Size':<15} {'Detail Level':<15}")
print("-" * 80)

for strategy_name, target_res in strategies:
    # Resample to target
    grids_resampled = []
    for g in [test_grid_200m, test_grid_100m, test_grid_50m]:
        zoom = g.cellsize / target_res
        resampled_data = ndimage.zoom(g.data, zoom, order=1)
        grids_resampled.append(Grid(
            data=resampled_data,
            xmin=g.xmin,
            ymin=g.ymin,
            cellsize=target_res,
            nodata_value=g.nodata_value
        ))
    
    # Merge without leveling (to avoid overlap calculation issues in demo)
    merged = GridMerger.merge_multiple_grids(grids_resampled, level_to_first=False)
    
    # Calculate approximate file size (data array size)
    file_size_mb = (merged.data.nbytes) / (1024 * 1024)
    
    # Detail level (smaller cells = more detail)
    if target_res == 50:
        detail = "Highest"
    elif target_res == 100:
        detail = "Medium"
    else:
        detail = "Lowest"
    
    print(f"{strategy_name:<20} {merged.ncols}x{merged.nrows:<10} {file_size_mb:>6.2f} MB{'':<6} {detail:<15}")

print("-" * 80)

print("\nRecommendations:")
print("  • Finest (50m): Preserves all detail, largest file")
print("  • Median (100m): Good balance, recommended for most cases")
print("  • Coarsest (200m): Fastest processing, loses some detail")

# ============================================================================
# SUMMARY
# ============================================================================

print_section("SUMMARY")

print("""
KEY POINTS:

1. PROBLEM: GridMerge assumes all grids have the same cellsize
   → Output uses first grid's cellsize
   → Other grids placed without resampling
   → Results in misaligned data

2. SOLUTION: Always resample to common resolution BEFORE merging
   → Choose target resolution (finest, coarsest, median, or specific)
   → Resample all grids using scipy, rasterio, or GDAL
   → Verify all cellsizes match
   → Then merge with GridMerge

3. RESAMPLING METHODS:
   → Upsampling (low→high res): Use bilinear or cubic interpolation
   → Downsampling (high→low res): Use average or bilinear
   → order=0 (nearest), order=1 (linear), order=3 (cubic) in scipy

4. CHOOSING TARGET RESOLUTION:
   → Finest: Preserves maximum detail (largest output)
   → Coarsest: Fastest, smallest file (loses detail)
   → Median: Good balance (recommended)
   → Specific: Match your project standards

5. BEST PRACTICE WORKFLOW:
   a. Load all grids
   b. Check cellsizes: [g.cellsize for g in grids]
   c. If different, choose target resolution
   d. Resample all to target (externally or with scipy)
   e. Verify cellsizes match
   f. Merge with GridMerge

For more details, see DIFFERENT_RESOLUTIONS.md
""")

print("\n" + "=" * 80)
print("DEMONSTRATION COMPLETE")
print("=" * 80)
