# GridMerge

A basic Python package for leveling and merging gridded geophysical data, like airborne magnetic and gamma-ray spectrometric data. 

## Features

GridMerge provides comprehensive tools for:

- **Grid I/O**: Read and write multiple grid formats:
  - ER Mapper (.ers)
  - GeoTIFF (.tif, .tiff) - requires rasterio or GDAL
  - ASCII Grid (.asc, .grd)
  - **Mix and match formats!** - You can merge grids from different formats
- **Grid Leveling**: Adjust grids to match reference levels using:
  - DC shift (baseline correction)
  - Scale adjustment
  - Polynomial fitting for tilt and gradient removal (1D and 2D)
- **Grid Merging**: Seamlessly merge multiple grids with:
  - Automatic overlap detection
  - Priority-based merging
  - Feathering/blending in overlap regions
  - **Scales to 47+ grids** (or hundreds more) - See [LARGE_SCALE_MERGING.md](LARGE_SCALE_MERGING.md)
- **Resampling & Reprojection** (with rioxarray):
  - Resample grids to different resolutions
  - Reproject grids to different coordinate systems
  - Match grids to reference grid (resolution + CRS)
  - Merge heterogeneous datasets (different resolutions and projections)

## Installation

Install from the repository:

```bash
pip install -e .
```

For GeoTIFF support, install with rasterio:

```bash
pip install -e ".[geotiff]"
```

For resampling and reprojection support (rioxarray):

```bash
pip install -e ".[rioxarray]"
```

Or install everything (GeoTIFF + rioxarray + dev tools):

```bash
pip install -e ".[all,dev]"
```

## Quick Start

### Python API

```python
from gridmerge import Grid, GridMerger, GridAdjuster

# Load grids (format auto-detected from extension)
grid1 = Grid.read("survey1.tif")  # GeoTIFF
grid2 = Grid.read("survey2.asc")  # ASCII Grid
grid3 = Grid.read("survey3.ers")  # ER Mapper

# Automatic merging with leveling (mixed formats!)
merged = GridMerger.merge_with_auto_leveling(
    [grid1, grid2, grid3],
    polynomial_degree=1,
    feather=True
)

# Save result (format auto-detected from extension)
merged.write("merged_output.tif")  # Save as GeoTIFF
# or
merged.write("merged_output.asc")  # Save as ASCII Grid
# or
merged.write("merged_output.ers")  # Save as ER Mapper
```

### Command-Line Interface

Merge multiple grids with automatic leveling (mixed formats):
```bash
gridmerge merge grid1.tif grid2.asc grid3.ers -o merged.tif --auto
```

Merge with specific adjustments:
```bash
gridmerge merge grid1.ers grid2.ers -o merged.tif --dc-shift --polynomial --polynomial-degree 2
```

Level one grid to another (different formats):
```bash
gridmerge level reference.tif input.asc -o leveled.ers --dc-shift --polynomial 2
```

Convert between formats:
```bash
gridmerge info input.asc  # Show grid info
# Then save as different format using Python API or by merging a single grid
```

Display grid information:
```bash
gridmerge info grid1.tif grid2.asc grid3.ers
```

## Supported Formats

### Format Auto-Detection

GridMerge automatically detects the format based on file extension:

- **ER Mapper**: `.ers` files
- **GeoTIFF**: `.tif`, `.tiff` files (requires rasterio or GDAL)
- **ASCII Grid**: `.asc`, `.grd` files

You can also explicitly specify the format:

```python
grid = Grid.read("myfile.dat", format="ascii")
grid.write("output.dat", format="geotiff")
```

### Format Conversion

Convert between formats easily:

```python
from gridmerge import Grid

# Read ASCII, write as GeoTIFF
grid = Grid.read("input.asc")
grid.write("output.tif")

# Read GeoTIFF, write as ER Mapper
grid = Grid.read("input.tif")
grid.write("output.ers")
```

### No Conversion Needed!

**The key feature**: You don't need to convert all your grids to the same format before merging! GridMerge can read and merge grids from different formats directly:

```python
# Mix and match formats!
grids = [
    Grid.read("magnetic_survey.tif"),
    Grid.read("radiometric_survey.asc"),
    Grid.read("legacy_data.ers")
]
merged = GridMerger.merge_with_auto_leveling(grids)
merged.write("combined.tif")  # Save in any format you want
```

## Core Concepts

### Grid Leveling

GridMerge adjusts individual grids to ensure they align correctly before merging:

1. **DC Shift**: Corrects baseline offset differences between grids
2. **Scale Adjustment**: Matches amplitude/variance between grids
3. **Polynomial Fitting**: Removes smooth trends, tilts, and gradients

### Grid Merging

The merging process combines multiple grids into a seamless composite:

1. **Overlap Detection**: Automatically finds overlapping regions
2. **Priority Management**: Higher priority grids take precedence in overlaps
3. **Feathering**: Smoothly blends data in overlap zones using distance-based weights

## Python API Examples

### Basic Grid Operations

```python
from gridmerge import Grid

# Load a grid
grid = Grid.read_ers("input.ers")

# Access grid properties
print(f"Grid size: {grid.nrows} x {grid.ncols}")
print(f"Bounds: {grid.bounds}")
print(f"Cell size: {grid.cellsize}")

# Get valid data (excluding nodata values)
valid_data = grid.get_valid_data()
print(f"Valid data range: {valid_data.min()} to {valid_data.max()}")

# Save grid
grid.write_ers("output.ers")
```

### Grid Adjustment

```python
from gridmerge import Grid, GridAdjuster

# Load grids (any format)
reference = Grid.read("reference.tif")
grid = Grid.read("input.asc")

# Calculate adjustments
dc_shift = GridAdjuster.calculate_dc_shift(reference, grid)
scale = GridAdjuster.calculate_scale_factor(reference, grid)

print(f"DC shift: {dc_shift}")
print(f"Scale factor: {scale}")

# Apply adjustments
adjusted = GridAdjuster.apply_dc_shift(grid, dc_shift)
adjusted = GridAdjuster.apply_scale(adjusted, scale)

# Or use the convenience method
leveled = GridAdjuster.level_to_reference(
    grid, reference,
    use_dc_shift=True,
    use_scale=True,
    polynomial_degree=2
)

# Save in desired format
leveled.write("leveled_output.tif")
```

### Advanced Merging

```python
from gridmerge import Grid, GridMerger

# Load multiple grids (mixed formats)
grids = [Grid.read(f"grid{i}.tif") for i in range(1, 6)]

# Merge with custom priorities (higher = more important)
priorities = [1, 2, 1, 3, 1]
merged = GridMerger.merge_multiple_grids(
    grids,
    priorities=priorities,
    level_to_first=True,
    use_dc_shift=True,
    polynomial_degree=1,
    feather=True
)

# Save result (any format)
merged.write("merged.tif")
```

### Large-Scale Merging (47+ Grids)

GridMerge efficiently handles large numbers of grids:

```python
# Merge 47 (or more!) grids
grids = [Grid.read(f"survey_{i:03d}.tif") for i in range(47)]

merged = GridMerger.merge_with_auto_leveling(
    grids,
    polynomial_degree=1,
    feather=True
)

merged.write("merged_47_grids.tif")
```

**Performance:** ~1-3 seconds per grid for 50×50 cells, linear scaling to hundreds of grids.

**See [LARGE_SCALE_MERGING.md](LARGE_SCALE_MERGING.md) for complete guide including:**
- Algorithm explanation
- Performance characteristics
- Memory considerations
- Progress tracking
- Optimization tips

### Non-Intersecting Grids & Quality Classification

**Important:** Some grids may not overlap with each other. Learn how GridMerge handles this:

```python
# Some grids overlap, some don't
grids = [
    Grid.read("region_a_grid1.tif"),  # Reference
    Grid.read("region_a_grid2.tif"),  # Overlaps with grid1
    Grid.read("region_b_grid1.tif"),  # NO overlap with region_a!
]

# Grids without overlap won't be leveled to reference
merged = GridMerger.merge_with_auto_leveling(grids)
```

**Quality classification** (priorities) lets you control merge order:

```python
# Assign priorities based on quality (higher = better)
priorities = [100, 100, 70]  # Region A high quality, Region B lower

merged = GridMerger.merge_multiple_grids(
    grids,
    priorities=priorities,
    level_to_first=True
)
```

**See [NON_INTERSECTING_GRIDS.md](NON_INTERSECTING_GRIDS.md) for detailed guide on:**
- How DC shift/leveling works without overlap
- Solutions for non-intersecting grids (chain leveling)
- Quality classification and its impact
- Combined scenarios and best practices

**See [CHAIN_LEVELING.md](CHAIN_LEVELING.md) for comprehensive guide on:**
- What chain leveling means (leveling through geographic neighbors)
- Real-world aeromagnetic survey examples (TMI, RTP)
- Geographic vs data type connections (GEOGRAPHY matters, not data type!)
- Comparison to Minty GridMerge methodology
- Step-by-step implementation guide

### Different Grid Resolutions

**Important:** GridMerge assumes all grids have the same resolution (cellsize).

#### Manual Resampling (External Tools)

You can resample grids before merging using external tools like GDAL or rasterio:

```python
from gridmerge import Grid

# Check resolutions
grids = [Grid.read(f) for f in grid_files]
cellsizes = [g.cellsize for g in grids]

if len(set(cellsizes)) > 1:
    print(f"WARNING: Different resolutions: {cellsizes}")
    print("Resample to common resolution before merging!")
```

**See [DIFFERENT_RESOLUTIONS.md](DIFFERENT_RESOLUTIONS.md) for complete guide on manual resampling using GDAL, rasterio, or scipy.**

#### Automatic Resampling and Reprojection (rioxarray)

GridMerge now supports automatic resampling and reprojection using rioxarray:

```bash
# Install rioxarray support
pip install -e ".[rioxarray]"
```

**Resample to different resolution:**
```python
from gridmerge import Grid

# Load grid
grid = Grid.read("input.tif")

# Resample to coarser resolution (100m → 200m)
grid_200m = grid.resample(target_cellsize=200, method='average')

# Resample to finer resolution (100m → 50m)
grid_50m = grid.resample(target_cellsize=50, method='bilinear')

# Save
grid_200m.write("output_200m.tif")
```

**Reproject to different CRS:**
```python
# Reproject from UTM to Geographic
grid_geo = grid.reproject(target_crs='EPSG:4326', method='bilinear')

# Reproject to different UTM zone
grid_utm54 = grid.reproject(target_crs='EPSG:32754', method='bilinear')
```

**Match to reference grid (resolution + CRS + extent):**
```python
# Load grids with different resolutions and CRS
reference = Grid.read("reference_100m_utm55.tif")  # 100m, UTM 55S
survey_a = Grid.read("survey_50m_utm55.tif")       # 50m, UTM 55S
survey_b = Grid.read("survey_200m_utm54.tif")      # 200m, UTM 54S (different zone!)

# Match both surveys to reference grid
survey_a_matched = survey_a.match_grid(reference, method='average')
survey_b_matched = survey_b.match_grid(reference, method='bilinear')

# Now all grids have same resolution, CRS, and extent - ready to merge!
merged = GridMerger.merge_with_auto_leveling(
    [reference, survey_a_matched, survey_b_matched]
)
```

**Complete workflow for heterogeneous datasets:**
```python
from gridmerge import Grid, GridMerger

# Load surveys with different resolutions and CRS
grids = [
    Grid.read("survey_100m_utm55.tif"),  # Reference
    Grid.read("survey_50m_utm55.tif"),   # Different resolution
    Grid.read("survey_200m_utm54.tif"),  # Different resolution AND CRS
]

# Choose reference (typically highest quality or most coverage)
reference = grids[0]

# Match all other grids to reference
grids_matched = [reference.copy()]
for grid in grids[1:]:
    grids_matched.append(grid.match_grid(reference, method='bilinear'))

# Merge with leveling
merged = GridMerger.merge_with_auto_leveling(
    grids_matched,
    use_dc_shift=True,
    polynomial_degree=1,
    feather_distance=10
)

merged.write("merged_unified.tif")
```

**Available resampling methods:**
- `'nearest'`: Nearest neighbor (fast, preserves values)
- `'bilinear'`: Bilinear interpolation (smooth, general purpose)
- `'cubic'`: Cubic interpolation (smoother, higher quality)
- `'average'`: Average of cells (best for downsampling)
- And many more (lanczos, gauss, mode, min, max, etc.)

**xarray Integration:**
```python
# Convert to xarray for advanced workflows
da = grid.to_xarray(crs='EPSG:32755')

# Use xarray operations
mean_value = da.mean()
std_dev = da.std()

# Convert back
grid_back = Grid.from_xarray(da)
```

**See also:**
- [examples/rioxarray_demo.py](examples/rioxarray_demo.py) - Complete working examples
- [DIFFERENT_RESOLUTIONS.md](DIFFERENT_RESOLUTIONS.md) - Manual resampling guide
- Resolution strategy selection (finest, coarsest, median)
- Real-world examples and workflows

### Batch Reprojection Utilities

For working with many grids that have different CRS and resolutions, GridMerge provides convenient batch processing utilities:

#### Inspect Multiple Grids

See all grid properties at a glance:

```python
from gridmerge.utils import inspect_grids

# Inspect multiple grid files
grid_files = ['survey1.tif', 'survey2.tif', 'survey3.tif']
info = inspect_grids(grid_files)

# Displays table with:
# - Index, filename
# - Resolution (cellsize)
# - CRS
# - Bounds and dimensions
# - File size
```

Output example:
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

[2] Loading: survey3.tif
    Resolution:  200.000000 units
    CRS:         EPSG:32754  <-- Different CRS!
    ...
```

#### Batch Reproject to Reference

Reproject all grids to match a reference grid in one call:

```python
from gridmerge.utils import reproject_grids_to_reference

# Option 1: Use one of the input grids as reference
aligned_files = reproject_grids_to_reference(
    grid_files=['survey1.tif', 'survey2.tif', 'survey3.tif'],
    reference_index=0,  # Use first grid as reference
    output_dir='./aligned/',
    method='bilinear'
)

# Option 2: Provide explicit reference grid
from gridmerge import Grid
reference = Grid.read('my_reference_grid.tif')

aligned_files = reproject_grids_to_reference(
    grid_files=['survey1.tif', 'survey2.tif'],
    reference_grid=reference,
    output_dir='./aligned/',
    method='bilinear'
)

# All grids now have same CRS and resolution!
```

Features:
- Automatically skips grids that already match (efficient!)
- Shows progress for each grid
- Returns list of output file paths
- Creates output directory if needed

#### Complete Workflow: Inspect → Reproject → Merge

The recommended workflow for heterogeneous datasets:

```python
from gridmerge import Grid, GridMerger
from gridmerge.utils import inspect_grids, reproject_grids_to_reference

# Step 1: Inspect to see what you're working with
grid_files = ['survey_a.tif', 'survey_b.tif', 'survey_c.tif']
info = inspect_grids(grid_files)
# Review the table to choose best reference (usually highest quality)

# Step 2: Reproject all to match reference
aligned_files = reproject_grids_to_reference(
    grid_files=grid_files,
    reference_index=0,  # Choose based on inspection
    output_dir='./aligned/',
    method='bilinear'
)

# Step 3: Load aligned grids and merge
grids = [Grid.read(f) for f in aligned_files]
merged = GridMerger.merge_with_auto_leveling(
    grids,
    use_dc_shift=True,
    polynomial_degree=1,
    feather_distance=10
)

# Step 4: Save final result
merged.write('final_merged.tif')
```

#### One-Line Convenience Function

For the common case of preparing grids for merging:

```python
from gridmerge.utils import prepare_grids_for_merge

# Prepare all grids to match the first one
prepared_files = prepare_grids_for_merge(
    grid_files=['a.tif', 'b.tif', 'c.tif'],
    reference_index=0,
    output_dir='./prepared/',
    method='bilinear'
)

# Ready to merge immediately
from gridmerge import Grid, GridMerger
grids = [Grid.read(f) for f in prepared_files]
merged = GridMerger.merge_with_auto_leveling(grids)
merged.write('merged.tif')
```

**See [examples/batch_reproject_demo.py](examples/batch_reproject_demo.py) for complete working examples.**

## File Format Support

GridMerge supports multiple grid formats with automatic format detection:

### ER Mapper (.ers)
- **Input/Output**: ER Mapper header (.ers) with binary data file
- **Data type**: IEEE 4-byte real
- **Structure**: Text header file (.ers) + binary data file
- **Metadata**: Projection, datum, coordinate system, cell size, null value
- **Always available** (no extra dependencies)

### GeoTIFF (.tif, .tiff)
- **Input/Output**: Industry-standard georeferenced TIFF format
- **Requirements**: `rasterio` or GDAL (`pip install rasterio`)
- **Metadata**: Full CRS support, geotransform
- **Widely compatible** with GIS software

### ASCII Grid (.asc, .grd)
- **Input/Output**: Simple text-based grid format
- **Structure**: Header rows + space-separated data values
- **Widely supported** by many GIS and geophysical software
- **Always available** (no extra dependencies)

### Format Mixing

**Key advantage**: You can mix formats freely! For example:
- Read GeoTIFF from remote sensing
- Read ASCII Grid from legacy surveys
- Read ER Mapper from recent geophysical surveys
- Merge them all together
- Output in your preferred format

## Algorithms

### DC Shift Correction

Calculates the mean difference in overlapping regions and adjusts the baseline:

```
DC_shift = mean(reference_grid - target_grid) in overlap
```

### Scale Adjustment

Matches the standard deviation between grids:

```
scale_factor = std(reference_grid) / std(target_grid) in overlap
```

### Polynomial Surface Fitting

Fits a polynomial surface to the difference in the overlap region:

- **Linear (degree 1)**: `z = a + bx + cy`
- **Quadratic (degree 2)**: `z = a + bx + cy + dx² + ey² + fxy`
- **Cubic (degree 3)**: `z = a + bx + cy + dx² + ey² + fxy + gx³ + hy³ + ix²y + jxy²`

### Feathering/Blending

Uses distance transform to create smooth weights that fade toward grid edges, ensuring seamless transitions in overlap regions.

## Requirements

- Python >= 3.8
- NumPy >= 1.20.0
- SciPy >= 1.7.0 (for distance transforms in feathering)

## Development

Run tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=gridmerge
```

## Background

This package is a reverse-engineered implementation based on the GridMerge software documentation from Minty Geophysics. GridMerge is widely used in geophysical data processing for leveling and merging airborne magnetic and radiometric survey grids.

The original GridMerge software is described at:
- https://www.mintygeophysics.com/GridMerge_Help/GridMerge_Help.html
- https://www.gridmerge.com.au/

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.
