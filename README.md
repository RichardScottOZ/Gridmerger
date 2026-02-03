# GridMerge

A Python package for leveling and merging gridded geophysical data, particularly airborne magnetic and gamma-ray spectrometric data. This package is a reverse-engineered implementation based on the GridMerge software by Minty Geophysics.

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

## Installation

Install from the repository:

```bash
pip install -e .
```

For GeoTIFF support, install with rasterio:

```bash
pip install -e ".[geotiff]"
```

Or with all development dependencies:

```bash
pip install -e ".[dev,geotiff]"
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
