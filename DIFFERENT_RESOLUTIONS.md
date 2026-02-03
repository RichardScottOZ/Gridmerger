# How GridMerge Handles Grids at Different Resolutions

## Quick Answer

**GridMerge currently assumes all grids have the same resolution (cellsize).** When merging grids with different resolutions, the output grid uses the **first grid's resolution**, and subsequent grids are placed directly without resampling.

**Recommendation:** Resample all grids to a common resolution before merging for best results.

---

## Table of Contents

1. [Current Behavior](#current-behavior)
2. [What Happens with Different Resolutions](#what-happens-with-different-resolutions)
3. [Why Same Resolution Matters](#why-same-resolution-matters)
4. [Best Practices](#best-practices)
5. [Manual Resampling Solutions](#manual-resampling-solutions)
6. [Real-World Example](#real-world-example)
7. [Future Enhancements](#future-enhancements)

---

## Current Behavior

### How Merging Works

When you merge grids with `GridMerger.merge_two_grids()` or `GridMerger.merge_multiple_grids()`:

```python
# From merge.py, line 70-71:
# Use first grid's cell size (assume they match)
cellsize = grid1.cellsize
```

**The algorithm:**
1. Takes the **first grid's cellsize** as the output resolution
2. Creates output grid with dimensions based on this cellsize
3. Places each grid's data directly into the output grid
4. Assumes all grids align on the same coordinate system

### Code Example

```python
from gridmerge import Grid, GridMerger

# Grid 1: 100m resolution
grid1 = Grid(data1, xmin=0, ymin=0, cellsize=100)  # 100m cells

# Grid 2: 50m resolution (DIFFERENT!)
grid2 = Grid(data2, xmin=5000, ymin=0, cellsize=50)  # 50m cells

# Merge
merged = GridMerger.merge_two_grids(grid1, grid2)

# Result cellsize = grid1.cellsize = 100m
print(f"Output resolution: {merged.cellsize}m")  # 100m
```

---

## What Happens with Different Resolutions

### Scenario 1: High-Res Grid Merged into Low-Res Grid

**Setup:**
- Grid 1: 100m resolution (reference/first)
- Grid 2: 50m resolution (high-res detail)

**Result:**
```
Grid 1: 100m cells → Output: 100m cells
Grid 2: 50m cells → Placed as-is into 100m grid

Problem: Grid 2's 50m cells don't align with 100m grid!
  - 2 cells from Grid 2 (50m each) span 1 cell of output (100m)
  - Data placement may be incorrect
  - Some high-res detail is lost
```

**Visual:**
```
Grid 1 (100m cells):
┌─────┬─────┬─────┐
│ 100 │ 105 │ 110 │  Each cell = 100m×100m
└─────┴─────┴─────┘

Grid 2 (50m cells):
┌───┬───┬───┬───┐
│ 90│ 92│ 94│ 96│  Each cell = 50m×50m
└───┴───┴───┴───┘

Output (100m cells, grid2 data misaligned):
┌─────┬─────┬─────┬─────┐
│ 100 │ 105 │ 90  │ 94  │  ← Grid 2 cells don't fit!
└─────┴─────┴─────┴─────┘
         ^^^ Potential misalignment
```

### Scenario 2: Low-Res Grid Merged into High-Res Grid

**Setup:**
- Grid 1: 50m resolution (reference/first)
- Grid 2: 100m resolution (coarse detail)

**Result:**
```
Grid 1: 50m cells → Output: 50m cells
Grid 2: 100m cells → Placed as-is into 50m grid

Problem: Grid 2's 100m cells span multiple 50m cells
  - Each 100m cell should be split into 4×50m cells
  - Instead, only one 50m cell gets the value
  - Result looks blocky/incorrect
```

**Visual:**
```
Grid 1 (50m cells):
┌───┬───┬───┬───┐
│ 90│ 92│ 94│ 96│  Each cell = 50m×50m
└───┴───┴───┴───┘

Grid 2 (100m cells):
┌─────┬─────┐
│ 100 │ 105 │  Each cell = 100m×100m
└─────┴─────┘

Output (50m cells, grid2 data incomplete):
┌───┬───┬───┬───┬────┬───┐
│ 90│ 92│ 94│ 96│100 │ ? │  ← Only 1 cell filled per 100m value
└───┴───┴───┴───┴────┴───┘
                       ^^^ Missing data
```

### Scenario 3: Multiple Different Resolutions

**Setup:**
- Grid 1: 100m resolution
- Grid 2: 50m resolution
- Grid 3: 200m resolution

**Result:**
```
All grids forced to Grid 1's 100m resolution
  → Grid 2 (50m): Misaligned
  → Grid 3 (200m): Blocky/incomplete
```

---

## Why Same Resolution Matters

### 1. Grid Alignment

Grids must align on the same coordinate grid:
```
Same resolution (100m):
Grid A cells: [0-100m] [100-200m] [200-300m]
Grid B cells: [0-100m] [100-200m] [200-300m]
           ✓ ALIGNED

Different resolution:
Grid A cells: [0-100m] [100-200m] [200-300m]
Grid B cells: [0-50m] [50-100m] [100-150m] [150-200m]
           ✗ NOT ALIGNED
```

### 2. Data Integrity

- **Upsampling** (low→high res): Requires interpolation (bilinear, cubic, etc.)
- **Downsampling** (high→low res): Requires aggregation (mean, median, etc.)
- **No resampling**: Data placement is incorrect

### 3. Leveling Accuracy

DC shift and polynomial leveling calculations require aligned overlaps:
```python
# From adjust.py - calculate overlap differences
overlap1 = grid1.data[overlap_rows, overlap_cols]
overlap2 = grid2.data[overlap_rows, overlap_cols]
diff = overlap1 - overlap2  # Requires same cell positions!
```

If resolutions differ, `overlap_rows` and `overlap_cols` won't match correctly.

### 4. Feathering Quality

Distance-based feathering blends values based on spatial proximity:
```python
# Blending in overlap
blended = (weight1 * value1 + weight2 * value2) / (weight1 + weight2)
```

Requires aligned cells for accurate blending.

---

## Best Practices

### ✅ Recommended Approach

**1. Check Resolutions Before Merging**

```python
from gridmerge import Grid

grids = [Grid.read(f) for f in grid_files]

# Check all cellsizes
cellsizes = [g.cellsize for g in grids]
if len(set(cellsizes)) > 1:
    print(f"WARNING: Different resolutions detected: {cellsizes}")
    print("Recommend resampling to common resolution")
```

**2. Choose Target Resolution**

Strategy depends on your goals:

| Goal | Target Resolution | Rationale |
|------|------------------|-----------|
| Maximum detail | Minimum cellsize (finest) | Preserve high-res data |
| Balanced | Median cellsize | Compromise between detail and file size |
| Performance | Maximum cellsize (coarsest) | Smaller output, faster processing |
| Uniform | Specific value (e.g., 100m) | Standard for your project |

**3. Resample All Grids**

Use external tools (see [Manual Resampling Solutions](#manual-resampling-solutions)) to resample before merging.

**4. Then Merge**

```python
# After resampling externally
grids = [Grid.read(f) for f in resampled_files]

# Verify
assert len(set([g.cellsize for g in grids])) == 1, "Resolutions must match!"

# Merge
merged = GridMerger.merge_with_auto_leveling(grids)
```

### ⚠️ What to Avoid

❌ **Don't merge different resolutions without resampling**
```python
# BAD: Different resolutions
grid1 = Grid.read("100m_resolution.tif")  # 100m
grid2 = Grid.read("50m_resolution.tif")   # 50m
merged = GridMerger.merge_two_grids(grid1, grid2)  # Likely incorrect!
```

❌ **Don't rely on order to control output resolution**
```python
# BAD: Trying to force high-res output by placing high-res grid first
grid_highres = Grid.read("10m_resolution.tif")   # 10m
grid_lowres = Grid.read("100m_resolution.tif")   # 100m
merged = GridMerger.merge_two_grids(grid_highres, grid_lowres)
# Output is 10m, but low-res grid data is still incorrectly placed
```

❌ **Don't assume it will "just work"**

The library doesn't automatically resample. You must handle it explicitly.

---

## Manual Resampling Solutions

### Option 1: GDAL Command Line

**Upsample to finer resolution (e.g., 100m → 50m):**
```bash
gdalwarp -tr 50 50 -r bilinear input_100m.tif output_50m.tif
```

**Downsample to coarser resolution (e.g., 50m → 100m):**
```bash
gdalwarp -tr 100 100 -r average input_50m.tif output_100m.tif
```

**Resampling methods:**
- `bilinear`: Smooth interpolation (good for upsampling)
- `cubic`: Smoother interpolation (better for upsampling, slower)
- `average`: Mean of all pixels (good for downsampling)
- `near`: Nearest neighbor (fast, preserves original values)

### Option 2: Python with rasterio

```python
import rasterio
from rasterio.enums import Resampling
import numpy as np

def resample_grid(input_file, output_file, target_cellsize, method='bilinear'):
    """
    Resample a grid to a target cellsize.
    
    Args:
        input_file: Input grid file
        output_file: Output grid file
        target_cellsize: Target cell size (meters)
        method: Resampling method ('bilinear', 'cubic', 'average', 'nearest')
    """
    with rasterio.open(input_file) as src:
        # Calculate new dimensions
        scale_x = src.res[0] / target_cellsize
        scale_y = src.res[1] / target_cellsize
        
        new_width = int(src.width * scale_x)
        new_height = int(src.height * scale_y)
        
        # Read and resample
        resampling_method = {
            'bilinear': Resampling.bilinear,
            'cubic': Resampling.cubic,
            'average': Resampling.average,
            'nearest': Resampling.nearest
        }[method]
        
        data = src.read(
            out_shape=(src.count, new_height, new_width),
            resampling=resampling_method
        )
        
        # Update transform
        transform = src.transform * src.transform.scale(
            (src.width / new_width),
            (src.height / new_height)
        )
        
        # Write output
        profile = src.profile.copy()
        profile.update({
            'width': new_width,
            'height': new_height,
            'transform': transform
        })
        
        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(data)

# Example usage
resample_grid('input_100m.tif', 'output_50m.tif', target_cellsize=50)
```

### Option 3: Python with scipy

For simple in-memory resampling:

```python
from scipy import ndimage
import numpy as np
from gridmerge import Grid

def resample_grid_data(grid, target_cellsize, method='linear'):
    """
    Resample a Grid object to a target cellsize.
    
    Args:
        grid: Input Grid object
        target_cellsize: Target cell size
        method: Interpolation method ('linear', 'cubic', 'nearest')
        
    Returns:
        New Grid object with resampled data
    """
    # Calculate zoom factor
    zoom_factor = grid.cellsize / target_cellsize
    
    # Choose interpolation order
    order = {'nearest': 0, 'linear': 1, 'cubic': 3}[method]
    
    # Resample data
    resampled_data = ndimage.zoom(grid.data, zoom_factor, order=order)
    
    # Create new grid with same geographic extent but different cellsize
    return Grid(
        data=resampled_data,
        xmin=grid.xmin,
        ymin=grid.ymin,
        cellsize=target_cellsize,
        nodata_value=grid.nodata_value,
        metadata=grid.metadata.copy()
    )

# Example usage
grid = Grid.read('input.tif')  # 100m resolution
resampled = resample_grid_data(grid, target_cellsize=50)  # Upsample to 50m
resampled.write('output.tif')
```

### Option 4: Batch Resampling Script

```python
"""
Batch resample multiple grids to common resolution before merging.
"""
import os
from pathlib import Path
from gridmerge import Grid
from scipy import ndimage

def batch_resample(input_files, output_dir, target_cellsize, method='linear'):
    """
    Resample multiple grids to a common cellsize.
    
    Args:
        input_files: List of input grid files
        output_dir: Output directory for resampled grids
        target_cellsize: Target cell size for all grids
        method: Interpolation method
    """
    os.makedirs(output_dir, exist_ok=True)
    
    resampled_files = []
    for input_file in input_files:
        # Load grid
        grid = Grid.read(input_file)
        
        print(f"Resampling {input_file}:")
        print(f"  Original: {grid.cellsize}m")
        print(f"  Target: {target_cellsize}m")
        
        # Resample
        zoom_factor = grid.cellsize / target_cellsize
        order = {'nearest': 0, 'linear': 1, 'cubic': 3}[method]
        resampled_data = ndimage.zoom(grid.data, zoom_factor, order=order)
        
        resampled_grid = Grid(
            data=resampled_data,
            xmin=grid.xmin,
            ymin=grid.ymin,
            cellsize=target_cellsize,
            nodata_value=grid.nodata_value,
            metadata=grid.metadata.copy()
        )
        
        # Save
        output_file = os.path.join(
            output_dir,
            f"resampled_{Path(input_file).name}"
        )
        resampled_grid.write(output_file)
        resampled_files.append(output_file)
        
        print(f"  Saved: {output_file}")
    
    return resampled_files

# Example usage
input_files = [
    'survey1_100m.tif',
    'survey2_50m.tif',
    'survey3_200m.tif'
]

# Resample all to 50m (finest resolution)
resampled = batch_resample(
    input_files,
    output_dir='resampled_grids',
    target_cellsize=50,
    method='linear'
)

# Now merge with GridMerge
from gridmerge import GridMerger
grids = [Grid.read(f) for f in resampled]
merged = GridMerger.merge_with_auto_leveling(grids)
merged.write('final_merged.tif')
```

---

## Real-World Example

### Scenario: Regional Aeromagnetic Compilation

You have 3 surveys with different resolutions:

```
Survey A (2005): 200m cell size, covers west region
Survey B (2010): 100m cell size, covers central (overlaps A and C)
Survey C (2020): 50m cell size, covers east region (high-res detail)
```

### Problem

```python
from gridmerge import Grid, GridMerger

# Load grids
survey_a = Grid.read('survey_a_200m.tif')  # 200m
survey_b = Grid.read('survey_b_100m.tif')  # 100m
survey_c = Grid.read('survey_c_50m.tif')   # 50m

# Try to merge (will produce incorrect results!)
grids = [survey_a, survey_b, survey_c]
merged = GridMerger.merge_with_auto_leveling(grids)
# Output resolution = 200m (first grid)
# Survey B and C data misaligned!
```

### Solution

**Step 1: Choose target resolution**

Strategy: Use 50m (finest) to preserve Survey C's high-res detail

**Step 2: Resample all grids to 50m**

```bash
# Using GDAL
gdalwarp -tr 50 50 -r bilinear survey_a_200m.tif survey_a_50m.tif
gdalwarp -tr 50 50 -r bilinear survey_b_100m.tif survey_b_50m.tif
# Survey C already 50m, no need to resample
```

**Step 3: Verify resolutions match**

```python
from gridmerge import Grid

grids = [
    Grid.read('survey_a_50m.tif'),
    Grid.read('survey_b_50m.tif'),
    Grid.read('survey_c_50m.tif')
]

# Check
cellsizes = [g.cellsize for g in grids]
print(f"All cellsizes: {cellsizes}")  # [50.0, 50.0, 50.0]
assert len(set(cellsizes)) == 1, "Resolutions must match!"
```

**Step 4: Merge with confidence**

```python
from gridmerge import GridMerger

# Now safe to merge
merged = GridMerger.merge_with_auto_leveling(grids)
merged.write('regional_compilation_50m.tif')

print(f"Output resolution: {merged.cellsize}m")  # 50m
print(f"Output dimensions: {merged.ncols} x {merged.nrows}")
```

### Alternative: Coarser Output

If 50m output is too large or you don't need that detail:

```bash
# Resample all to 100m (balanced)
gdalwarp -tr 100 100 -r bilinear survey_a_200m.tif survey_a_100m.tif
# Survey B already 100m
gdalwarp -tr 100 100 -r average survey_c_50m.tif survey_c_100m.tif
```

Note: Use `-r average` when downsampling to aggregate high-res data properly.

---

## Future Enhancements

### Potential Improvements

The library could be enhanced to:

1. **Automatic Resolution Detection**
   ```python
   # Proposed API
   merged = GridMerger.merge_with_resampling(
       grids,
       target_resolution='finest',  # or 'coarsest', 'median', specific value
       resampling_method='bilinear'
   )
   ```

2. **Warning When Resolutions Differ**
   ```python
   if grid1.cellsize != grid2.cellsize:
       warnings.warn(
           f"Grid resolutions differ ({grid1.cellsize} vs {grid2.cellsize}). "
           f"Output will use {grid1.cellsize}. Consider resampling first."
       )
   ```

3. **Built-in Resampling**
   ```python
   # Proposed: Add to Grid class
   resampled = grid.resample(target_cellsize=50, method='bilinear')
   ```

4. **Smart Resolution Selection**
   ```python
   # Proposed: Analyze all grids and choose optimal resolution
   target_res = GridMerger.suggest_resolution(grids)
   # Returns: finest resolution, or median if difference is large
   ```

### Why Not Implemented Yet?

1. **Complexity**: Resampling requires careful handling of:
   - Interpolation methods (different for different data types)
   - Edge cases (nodata values, grid boundaries)
   - Performance (large grids)

2. **Dependencies**: Would require scipy or rasterio

3. **User Control**: Users may want specific resampling methods or parameters

4. **Philosophy**: Library focuses on merging/leveling; resampling is preprocessing

### Contribution Welcome!

If you'd like to add automatic resampling, see the codebase structure:
- `gridmerge/grid.py`: Add `resample()` method to Grid class
- `gridmerge/merge.py`: Add resolution checking and optional auto-resample
- `tests/test_resample.py`: Add test cases for resampling

---

## Summary

### Key Takeaways

1. **GridMerge assumes same resolution** for all input grids
2. **Output resolution = first grid's resolution**
3. **Different resolutions cause misalignment** (data placed incorrectly)
4. **Always resample before merging** for correct results
5. **Use external tools** (GDAL, rasterio, scipy) for resampling

### Quick Checklist

Before merging grids:

- [ ] Check all grids have same cellsize
- [ ] If different, choose target resolution (finest/coarsest/specific)
- [ ] Resample all grids to target resolution
- [ ] Verify resolutions match
- [ ] Then merge with GridMerge

### Example Workflow

```python
from gridmerge import Grid, GridMerger

# 1. Load and check
grids = [Grid.read(f) for f in grid_files]
cellsizes = [g.cellsize for g in grids]

# 2. If different, resample externally first
if len(set(cellsizes)) > 1:
    print("Different resolutions detected. Resample first!")
    # Use GDAL/rasterio to resample, then reload
    
# 3. Merge
merged = GridMerger.merge_with_auto_leveling(grids)
merged.write('output.tif')
```

---

## See Also

- [LARGE_SCALE_MERGING.md](LARGE_SCALE_MERGING.md) - Merging many grids
- [CHAIN_LEVELING.md](CHAIN_LEVELING.md) - Non-intersecting grids
- [NON_INTERSECTING_GRIDS.md](NON_INTERSECTING_GRIDS.md) - Quality classification
- [MULTI_FORMAT_GUIDE.md](MULTI_FORMAT_GUIDE.md) - Format support

---

**Questions? Issues?**

If you encounter problems with different resolutions, please report them in the GitHub issues with:
- Input grid resolutions
- Expected behavior
- Actual behavior
- Example code
