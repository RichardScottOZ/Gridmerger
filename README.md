# GridMerge

A Python package for leveling and merging gridded geophysical data, particularly airborne magnetic and gamma-ray spectrometric data. This package is a reverse-engineered implementation based on the GridMerge software by Minty Geophysics.

## Features

GridMerge provides comprehensive tools for:

- **Grid I/O**: Read and write ER Mapper (.ers) format grids
- **Grid Leveling**: Adjust grids to match reference levels using:
  - DC shift (baseline correction)
  - Scale adjustment
  - Polynomial fitting for tilt and gradient removal (1D and 2D)
- **Grid Merging**: Seamlessly merge multiple grids with:
  - Automatic overlap detection
  - Priority-based merging
  - Feathering/blending in overlap regions
  - Support for hundreds of grids

## Installation

Install from the repository:

```bash
pip install -e .
```

Or with development dependencies:

```bash
pip install -e ".[dev]"
```

## Quick Start

### Python API

```python
from gridmerge import Grid, GridMerger, GridAdjuster

# Load grids
grid1 = Grid.read_ers("survey1.ers")
grid2 = Grid.read_ers("survey2.ers")

# Automatic merging with leveling
merged = GridMerger.merge_with_auto_leveling(
    [grid1, grid2],
    polynomial_degree=1,
    feather=True
)

# Save result
merged.write_ers("merged_output.ers")
```

### Command-Line Interface

Merge multiple grids with automatic leveling:
```bash
gridmerge merge grid1.ers grid2.ers grid3.ers -o merged.ers --auto
```

Merge with specific adjustments:
```bash
gridmerge merge grid1.ers grid2.ers -o merged.ers --dc-shift --polynomial --polynomial-degree 2
```

Level one grid to a reference:
```bash
gridmerge level reference.ers input.ers -o leveled.ers --dc-shift --polynomial 1
```

Display grid information:
```bash
gridmerge info grid1.ers grid2.ers
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

# Load grids
reference = Grid.read_ers("reference.ers")
grid = Grid.read_ers("input.ers")

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
```

### Advanced Merging

```python
from gridmerge import Grid, GridMerger

# Load multiple grids
grids = [Grid.read_ers(f"grid{i}.ers") for i in range(1, 6)]

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

# Save result
merged.write_ers("merged.ers")
```

## File Format Support

GridMerge currently supports the **ER Mapper (.ers)** format:

- **Input**: ER Mapper header (.ers) with binary data file
- **Output**: ER Mapper format with IEEE 4-byte real data type

The ER Mapper format consists of:
- A text header file (.ers) containing metadata
- A binary data file containing grid values

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
