# Resampling and Reprojection with rioxarray

This guide explains how to use GridMerge's rioxarray-based functionality for resampling and reprojecting grids.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Core Concepts](#core-concepts)
- [Resampling](#resampling)
- [Reprojection](#reprojection)
- [Matching to Reference Grid](#matching-to-reference-grid)
- [Complete Workflows](#complete-workflows)
- [Resampling Methods](#resampling-methods)
- [Best Practices](#best-practices)
- [xarray Integration](#xarray-integration)
- [Comparison to Manual Approaches](#comparison-to-manual-approaches)

## Overview

GridMerge now supports automatic resampling and reprojection through the rioxarray library. This enables:

1. **Resampling**: Change grid resolution (upsampling or downsampling)
2. **Reprojection**: Transform between coordinate reference systems (CRS)
3. **Grid Matching**: Unify resolution, CRS, and extent to match a reference grid
4. **Heterogeneous Merging**: Seamlessly merge grids with different resolutions and projections

**Key Advantage**: No need for external preprocessing with GDAL or other tools - do it all in Python!

## Installation

```bash
# Install with rioxarray support
pip install -e ".[rioxarray]"

# Or install all optional features
pip install -e ".[all]"

# Or install dependencies separately
pip install xarray rioxarray rasterio
```

**Dependencies**:
- `xarray >= 0.20.0` - Multi-dimensional arrays with labeled coordinates
- `rioxarray >= 0.13.0` - Geospatial extensions for xarray
- `rasterio >= 1.2.0` - GDAL bindings for Python

## Core Concepts

### Grid vs. xarray DataArray

GridMerge's `Grid` class is optimized for geophysical data processing, while xarray `DataArray` provides rich analysis capabilities:

- **Grid**: Simple, efficient storage for gridded data with basic spatial operations
- **DataArray**: Advanced analysis, lazy evaluation, integration with scientific Python ecosystem

You can convert between them:

```python
# Grid → xarray
da = grid.to_xarray(crs='EPSG:32755')

# xarray → Grid
grid = Grid.from_xarray(da)
```

### Coordinate Reference Systems (CRS)

A CRS defines how coordinates relate to positions on Earth. Common formats:

- **EPSG codes**: `'EPSG:4326'` (WGS84 Geographic), `'EPSG:32755'` (UTM Zone 55 South)
- **PROJ strings**: `'+proj=utm +zone=55 +south +datum=WGS84'`
- **WKT strings**: Well-Known Text format

**Important**: Your grids must have a CRS defined in metadata for reprojection:

```python
grid.metadata['crs'] = 'EPSG:32755'
```

### Resampling vs. Reprojection

- **Resampling**: Changes pixel size, keeps same CRS (e.g., 100m → 50m)
- **Reprojection**: Changes CRS, may change pixel size (e.g., UTM → Geographic)

## Resampling

### Downsampling (Coarser Resolution)

Make grids smaller by averaging or subsampling:

```python
from gridmerge import Grid

# Load high-resolution grid (50m)
grid_50m = Grid.read("highres_50m.tif")
print(f"Original: {grid_50m.ncols}×{grid_50m.nrows} cells @ {grid_50m.cellsize}m")

# Downsample to 100m (use 'average' for better results)
grid_100m = grid_50m.resample(target_cellsize=100, method='average')
print(f"Downsampled: {grid_100m.ncols}×{grid_100m.nrows} cells @ {grid_100m.cellsize}m")

# Downsample to 200m
grid_200m = grid_50m.resample(target_cellsize=200, method='average')
```

**When to use**: Reduce file size, match coarser reference grids, speed up processing.

**Best method**: `'average'` - averages all input pixels that contribute to each output pixel.

### Upsampling (Finer Resolution)

Interpolate to create more pixels:

```python
# Load low-resolution grid (200m)
grid_200m = Grid.read("lowres_200m.tif")

# Upsample to 100m (use 'bilinear' or 'cubic')
grid_100m = grid_200m.resample(target_cellsize=100, method='bilinear')

# Upsample to 50m
grid_50m = grid_200m.resample(target_cellsize=50, method='cubic')
```

**When to use**: Match finer reference grids, create smoother visualizations.

**Best methods**:
- `'bilinear'`: Fast, smooth, general purpose
- `'cubic'`: Smoother, higher quality, slower

**Warning**: Upsampling doesn't add real detail - it only interpolates between existing values.

### Choosing Target Resolution

```python
# Strategy 1: Finest resolution (preserves maximum detail)
cellsizes = [grid.cellsize for grid in grids]
target = min(cellsizes)

# Strategy 2: Coarsest resolution (smallest file size)
target = max(cellsizes)

# Strategy 3: Median resolution (balanced)
import statistics
target = statistics.median(cellsizes)

# Strategy 4: Specific project standard
target = 100  # e.g., 100m for regional aeromagnetic
```

## Reprojection

### Between UTM Zones

Common for surveys spanning UTM zone boundaries:

```python
# Load grid in UTM Zone 55S
grid_utm55 = Grid.read("survey_utm55.tif")
print(f"CRS: {grid_utm55.metadata['crs']}")

# Reproject to UTM Zone 54S
grid_utm54 = grid_utm55.reproject(target_crs='EPSG:32754', method='bilinear')
print(f"Reprojected CRS: {grid_utm54.metadata['crs']}")
```

**EPSG codes for Australian UTM zones**:
- UTM 50S: `EPSG:32750`
- UTM 51S: `EPSG:32751`
- UTM 52S: `EPSG:32752`
- UTM 53S: `EPSG:32753`
- UTM 54S: `EPSG:32754`
- UTM 55S: `EPSG:32755`
- UTM 56S: `EPSG:32756`

### To/From Geographic Coordinates

```python
# UTM → Geographic (degrees)
grid_utm = Grid.read("survey_utm.tif")
grid_geo = grid_utm.reproject(target_crs='EPSG:4326', method='bilinear')
print(f"Bounds: {grid_geo.xmin:.6f}°E to {grid_geo.xmax:.6f}°E")

# Geographic → UTM
grid_geo = Grid.read("survey_geo.tif")
grid_utm = grid_geo.reproject(target_crs='EPSG:32755', method='bilinear')
```

**When to use**:
- Geographic: Global visualization, web maps, GIS integration
- UTM: Metric units, accurate distance/area calculations, geophysical processing

### State Plane or Custom Projections

```python
# To State Plane (e.g., California Zone 5)
grid_sp = grid.reproject(target_crs='EPSG:2229', method='bilinear')

# To custom PROJ string
grid_custom = grid.reproject(
    target_crs='+proj=lcc +lat_1=33 +lat_2=45 +lat_0=39 +lon_0=-96',
    method='bilinear'
)
```

## Matching to Reference Grid

The most powerful feature for merging heterogeneous datasets:

```python
from gridmerge import Grid, GridMerger

# Load reference grid (defines target resolution and CRS)
reference = Grid.read("reference_100m_utm55.tif")

# Load survey with different resolution
survey_a = Grid.read("survey_50m_utm55.tif")  # Different resolution, same CRS

# Load survey with different CRS
survey_b = Grid.read("survey_200m_utm54.tif")  # Different resolution AND CRS

# Match both to reference
survey_a_matched = survey_a.match_grid(reference, method='average')
survey_b_matched = survey_b.match_grid(reference, method='bilinear')

# All grids now have identical resolution, CRS, and extent!
print(f"Reference: {reference.cellsize}m, {reference.metadata['crs']}")
print(f"Survey A:  {survey_a_matched.cellsize}m, {survey_a_matched.metadata['crs']}")
print(f"Survey B:  {survey_b_matched.cellsize}m, {survey_b_matched.metadata['crs']}")

# Merge seamlessly
merged = GridMerger.merge_with_auto_leveling(
    [reference, survey_a_matched, survey_b_matched]
)
```

**What `match_grid()` does**:
1. Reprojects to reference CRS (if different)
2. Resamples to reference cellsize (if different)
3. Matches spatial extent to reference bounds
4. Returns grid ready to merge with reference

## Complete Workflows

### Workflow 1: Regional Compilation from Multiple Sources

```python
from gridmerge import Grid, GridMerger

# Scenario: Compile regional aeromagnetic map from various surveys
# - Survey 1: 100m, UTM 55S, TMI (2010)
# - Survey 2: 50m, UTM 55S, RTP (2015)
# - Survey 3: 200m, UTM 54S, TMI (2020) - different zone!

# Load grids
survey1 = Grid.read("survey1_100m_utm55_tmi.tif")
survey2 = Grid.read("survey2_50m_utm55_rtp.tif")
survey3 = Grid.read("survey3_200m_utm54_tmi.tif")

# Choose reference (typically best quality or most coverage)
reference = survey1

# Match all others to reference
survey2_matched = survey2.match_grid(reference, method='average')  # Downsample
survey3_matched = survey3.match_grid(reference, method='bilinear')  # Reproject + upsample

# Merge with leveling
merged = GridMerger.merge_with_auto_leveling(
    [reference, survey2_matched, survey3_matched],
    use_dc_shift=True,
    polynomial_degree=1,
    feather_distance=10
)

# Save
merged.write("regional_compilation_100m_utm55.tif")
```

### Workflow 2: Automatic Resolution Unification

```python
from gridmerge import Grid, GridMerger
import statistics

# Load all surveys
files = ["survey1.tif", "survey2.tif", "survey3.tif", "survey4.tif"]
grids = [Grid.read(f) for f in files]

# Check resolutions
cellsizes = [g.cellsize for g in grids]
print(f"Resolutions: {cellsizes}")

# Decide target resolution (median strategy)
target_cellsize = statistics.median(cellsizes)
print(f"Target resolution: {target_cellsize}m")

# Resample all to target
grids_resampled = []
for grid in grids:
    if grid.cellsize < target_cellsize:
        # Downsample (coarsen)
        resampled = grid.resample(target_cellsize, method='average')
    elif grid.cellsize > target_cellsize:
        # Upsample (refine)
        resampled = grid.resample(target_cellsize, method='bilinear')
    else:
        # Already at target
        resampled = grid.copy()
    grids_resampled.append(resampled)

# Merge
merged = GridMerger.merge_with_auto_leveling(grids_resampled)
merged.write("unified_compilation.tif")
```

### Workflow 3: Quality-Based Reference Selection

```python
from gridmerge import Grid, GridMerger

# Load surveys with quality metadata
grids = []
for file in ["survey_a.tif", "survey_b.tif", "survey_c.tif"]:
    grid = Grid.read(file)
    grids.append(grid)

# Choose reference based on quality
# Option 1: Finest resolution
reference = min(grids, key=lambda g: g.cellsize)

# Option 2: Most recent (assuming filename convention)
# reference = grids[-1]

# Option 3: Specific survey (manual selection)
# reference = grids[1]

print(f"Reference: {reference.cellsize}m, {reference.metadata.get('crs')}")

# Match all to reference
grids_matched = [reference.copy()]
for grid in grids:
    if grid is not reference:
        grids_matched.append(grid.match_grid(reference))

# Merge
merged = GridMerger.merge_with_auto_leveling(grids_matched)
```

## Resampling Methods

rioxarray supports many resampling methods via rasterio:

### For Downsampling (high → low resolution)

| Method | Description | Best For |
|--------|-------------|----------|
| `'average'` | Average of all input pixels | Continuous data (magnetic, gravity) |
| `'bilinear'` | Bilinear interpolation | General purpose |
| `'cubic'` | Cubic convolution | Smoother results |
| `'min'` | Minimum value | Detecting anomaly minimums |
| `'max'` | Maximum value | Detecting anomaly maximums |
| `'med'` | Median value | Reducing noise |

### For Upsampling (low → high resolution)

| Method | Description | Best For |
|--------|-------------|----------|
| `'bilinear'` | Bilinear interpolation | General purpose, fast |
| `'cubic'` | Cubic interpolation | Smoother, higher quality |
| `'cubic_spline'` | Cubic spline | Smoothest, mathematical |
| `'lanczos'` | Lanczos resampling | High quality, sharp edges |
| `'nearest'` | Nearest neighbor | Preserving exact values (classifications) |

### Example Usage

```python
# Downsampling examples
grid_avg = grid.resample(200, method='average')      # Best for continuous data
grid_med = grid.resample(200, method='med')          # Best for noisy data
grid_max = grid.resample(200, method='max')          # Preserve peak values

# Upsampling examples
grid_bilinear = grid.resample(50, method='bilinear') # Fast, smooth
grid_cubic = grid.resample(50, method='cubic')       # High quality
grid_lanczos = grid.resample(50, method='lanczos')   # Sharpest
```

## Best Practices

### 1. Preserve Original Data

Always work on copies:

```python
# Good
grid_resampled = grid.resample(100, method='average')

# Also good
grid_backup = grid.copy()
grid_processed = grid_backup.resample(100, method='average')
```

### 2. Choose Appropriate Reference

For merging:
- **Highest quality survey** - If one is clearly better
- **Finest resolution** - To preserve maximum detail
- **Most extensive coverage** - For regional context
- **Project standard** - If specified (e.g., 100m for regional, 50m for detailed)

### 3. Match Resampling Method to Data

```python
# Continuous magnetic/gravity data
grid.resample(target, method='average')  # Downsampling
grid.resample(target, method='bilinear') # Upsampling

# Discrete classifications
grid.resample(target, method='mode')     # Downsampling
grid.resample(target, method='nearest')  # Upsampling
```

### 4. Verify Results

```python
# Check bounds are preserved
print(f"Original bounds: {grid.bounds}")
print(f"Resampled bounds: {grid_resampled.bounds}")

# Check resolution changed correctly
print(f"Original cellsize: {grid.cellsize}")
print(f"Target cellsize: {target_cellsize}")
print(f"Actual cellsize: {grid_resampled.cellsize}")

# Check CRS if reprojecting
print(f"Original CRS: {grid.metadata.get('crs')}")
print(f"Reprojected CRS: {grid_reprojected.metadata.get('crs')}")
```

### 5. Document Processing

```python
# Add processing info to metadata
grid_processed.metadata['processing_history'] = (
    f"Resampled from {original_cellsize}m to {target_cellsize}m "
    f"using {method} method"
)
grid_processed.metadata['source_file'] = "original.tif"
grid_processed.metadata['processed_date'] = "2024-01-15"
```

## xarray Integration

### Convert to xarray for Analysis

```python
import xarray as xr
from gridmerge import Grid

# Load grid
grid = Grid.read("survey.tif")

# Convert to xarray
da = grid.to_xarray()

# Use xarray operations
mean_value = float(da.mean())
std_dev = float(da.std())
percentiles = da.quantile([0.25, 0.50, 0.75])

# Spatial operations
da_subset = da.sel(x=slice(500000, 510000), y=slice(6000000, 6010000))

# Plotting with xarray
da.plot()

# Convert back to Grid
grid_processed = Grid.from_xarray(da_subset)
```

### Integration with Other Libraries

```python
# Works with hvplot for interactive visualization
import hvplot.xarray
da = grid.to_xarray()
da.hvplot(cmap='viridis')

# Works with dask for large datasets
import dask.array as dask_array
da_large = grid.to_xarray().chunk({'x': 1000, 'y': 1000})

# Works with cartopy for maps
import cartopy.crs as ccrs
da.plot(transform=ccrs.UTM(55, southern_hemisphere=True))
```

## Comparison to Manual Approaches

### Before (Manual GDAL/rasterio)

```python
# Complex, requires external tools or detailed GDAL knowledge
import rasterio
from rasterio.warp import reproject, Resampling

# Load
with rasterio.open("input.tif") as src:
    # Calculate new transform
    transform = ... # Complex calculations
    
    # Create output
    data_out = np.empty((new_height, new_width), dtype=src.dtypes[0])
    
    # Reproject
    reproject(
        source=rasterio.band(src, 1),
        destination=data_out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=transform,
        dst_crs='EPSG:32755',
        resampling=Resampling.bilinear
    )
    
    # Write output (more code...)
```

### After (GridMerge with rioxarray)

```python
# Simple, intuitive
from gridmerge import Grid

grid = Grid.read("input.tif")
grid_reprojected = grid.reproject('EPSG:32755', method='bilinear')
grid_reprojected.write("output.tif")
```

### Benefits

1. **Simpler API**: One-line operations instead of complex setup
2. **Type Safety**: Grid class provides structure and validation
3. **Integration**: Works seamlessly with GridMerge leveling and merging
4. **Flexibility**: Easy conversion to/from xarray for advanced workflows
5. **Documentation**: Clear examples and best practices

## See Also

- [examples/rioxarray_demo.py](../examples/rioxarray_demo.py) - Complete working examples
- [DIFFERENT_RESOLUTIONS.md](DIFFERENT_RESOLUTIONS.md) - Manual resampling approaches
- [README.md](../README.md) - Main documentation
- [rioxarray documentation](https://corteva.github.io/rioxarray/)
- [xarray documentation](https://docs.xarray.dev/)
