# Batch Grid Utilities - Implementation Summary

This document summarizes the batch grid processing utilities added to GridMerge.

## Overview

GridMerge now includes powerful batch utilities for working with heterogeneous grid datasets that have different coordinate reference systems (CRS) and resolutions.

## Key Features

### 1. Grid Inspection - `inspect_grids()`

Displays comprehensive information about multiple grids in a clear table format.

**What it shows:**
- File index and name
- Resolution (cellsize)
- Coordinate Reference System (CRS)
- Spatial bounds
- Dimensions (rows × columns)
- File size

**Usage:**
```python
from gridmerge.utils import inspect_grids

grid_files = ['survey1.tif', 'survey2.tif', 'survey3.tif']
info = inspect_grids(grid_files)
```

**Output:**
```
================================================================================
GRID INSPECTION REPORT
================================================================================

[0] Loading: survey1.tif
    Resolution:  100.000000 units
    CRS:         EPSG:32755
    Bounds:      (500000.0, 6500000.0, 510000.0, 6510000.0)
    Dimensions:  100 rows × 100 cols
    Size:        3.81 MB

[1] Loading: survey2.tif
    Resolution:  50.000000 units
    CRS:         EPSG:32755
    ...
```

### 2. Batch Reprojection - `reproject_grids_to_reference()`

Reprojects multiple grids to match a reference grid's CRS and resolution.

**Features:**
- Use one of the input grids as reference, or provide external reference
- Automatic CRS detection from GeoTIFF files
- Smart skipping (grids already matching are copied, not reprojected)
- Progress reporting
- Creates output directory if needed
- Returns list of output file paths

**Usage:**
```python
from gridmerge.utils import reproject_grids_to_reference

# Use first grid as reference
aligned_files = reproject_grids_to_reference(
    grid_files=['survey1.tif', 'survey2.tif', 'survey3.tif'],
    reference_index=0,
    output_dir='./aligned/',
    method='bilinear'
)

# Or provide explicit reference
from gridmerge import Grid
reference = Grid.read('my_reference.tif')

aligned_files = reproject_grids_to_reference(
    grid_files=['survey1.tif', 'survey2.tif'],
    reference_grid=reference,
    output_dir='./aligned/'
)
```

### 3. Convenience Function - `prepare_grids_for_merge()`

One-line function to prepare grids for immediate merging.

**Usage:**
```python
from gridmerge.utils import prepare_grids_for_merge
from gridmerge import Grid, GridMerger

# Prepare
prepared_files = prepare_grids_for_merge(
    grid_files=['a.tif', 'b.tif', 'c.tif'],
    output_dir='./prepared/'
)

# Merge
grids = [Grid.read(f) for f in prepared_files]
merged = GridMerger.merge_with_auto_leveling(grids)
merged.write('final.tif')
```

### 4. Interactive Workflow - `interactive_reproject()`

Command-line interactive workflow for exploration.

**Usage:**
```python
from gridmerge.utils import interactive_reproject

interactive_reproject(['survey1.tif', 'survey2.tif', 'survey3.tif'])
# Prompts user to select reference, method, and optionally merge
```

## Complete Workflow

The recommended workflow for heterogeneous datasets:

```python
from gridmerge import Grid, GridMerger
from gridmerge.utils import inspect_grids, reproject_grids_to_reference

# Step 1: Inspect to see what you're working with
grid_files = ['survey_a.tif', 'survey_b.tif', 'survey_c.tif']
info = inspect_grids(grid_files)
# Review the table, note CRS differences, choose best reference

# Step 2: Reproject all to match reference
aligned_files = reproject_grids_to_reference(
    grid_files=grid_files,
    reference_index=0,  # Choose based on inspection
    output_dir='./aligned/',
    method='bilinear'
)

# Step 3: Load aligned grids
grids = [Grid.read(f) for f in aligned_files]

# Step 4: Merge with auto-leveling
merged = GridMerger.merge_with_auto_leveling(
    grids,
    use_dc_shift=True,
    polynomial_degree=1,
    feather_distance=10
)

# Step 5: Save final result
merged.write('final_merged.tif')
```

## Dependencies

- **rioxarray**: Automatically installs xarray as a dependency
- **xarray**: Installed automatically with rioxarray
- **rasterio**: Used by rioxarray for GeoTIFF I/O

**Installation:**
```bash
pip install -e ".[rioxarray]"
```

## Implementation Details

### Using rioxarray (not plain xarray)

All spatial operations use the rioxarray `.rio` accessor:

- ✅ `da.rio.reproject()` - rioxarray reprojection method
- ✅ `da.rio.crs` - rioxarray CRS accessor
- ✅ `da.rio.write_crs()` - rioxarray CRS setter
- ✅ `da.rio.nodata` - rioxarray nodata accessor

This ensures proper geospatial operations rather than generic array operations.

### Smart Processing

The batch utilities are designed to be efficient:

1. **Skip unnecessary work**: Grids already matching the reference are copied, not reprojected
2. **Progress reporting**: Shows which grid is being processed
3. **Error handling**: Continues processing if one grid fails, reports errors
4. **Flexible reference**: Can use input grid or external reference

## Files Added

- `gridmerge/utils.py` - Utility module (400+ lines)
- `examples/batch_reproject_demo.py` - Working demonstration (350+ lines)
- `tests/test_utils.py` - Test suite (200+ lines)

## Documentation

See also:
- [README.md](README.md) - Quick start and examples
- [examples/batch_reproject_demo.py](examples/batch_reproject_demo.py) - Complete demonstrations
- [RIOXARRAY_GUIDE.md](RIOXARRAY_GUIDE.md) - Detailed rioxarray guide

## Summary

The batch utilities address the need to work with heterogeneous grid datasets:

1. **Inspect** - See all grid properties at a glance
2. **Select** - Choose appropriate reference grid
3. **Reproject** - Align all grids to common CRS and resolution
4. **Merge** - Use GridMerger to create seamless composite

All in a simple, efficient workflow!
