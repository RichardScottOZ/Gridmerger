# GridMerge Python Package - Implementation Summary

## Overview
This document summarizes the implementation of the GridMerge Python package, which was reverse-engineered from the Minty Geophysics GridMerge documentation at https://www.mintygeophysics.com/GridMerge_Help/GridMerge_Help.html.

## Package Structure

```
gridmerge/
├── __init__.py          # Package initialization and exports
├── grid.py              # Grid data structure and ER Mapper I/O
├── adjust.py            # Grid adjustment algorithms
├── merge.py             # Grid merging algorithms
└── cli.py               # Command-line interface

examples/
└── merge_synthetic_grids.py  # Example usage

tests/
└── test_basic.py        # Test suite (12 tests)
```

## Core Components

### 1. Grid Class (grid.py)
- **Purpose**: Represents gridded geophysical data
- **Features**:
  - 2D numpy array storage with metadata
  - ER Mapper (.ers) format I/O
  - Coordinate system support
  - Overlap detection between grids
  - Valid data extraction (excluding nodata values)

### 2. GridAdjuster Class (adjust.py)
- **Purpose**: Provides grid adjustment and leveling algorithms
- **Features**:
  - DC shift calculation and application (baseline correction)
  - Scale factor calculation and application
  - 2D polynomial surface fitting (degrees 1-3)
  - Polynomial surface evaluation
  - Automatic leveling to reference grid

### 3. GridMerger Class (merge.py)
- **Purpose**: Merges multiple grids into seamless composites
- **Features**:
  - Two-grid merging with priority control
  - Multi-grid merging with automatic leveling
  - Distance-based feathering for smooth transitions
  - Priority-based merging
  - Automatic overlap detection and blending

### 4. Command-Line Interface (cli.py)
- **Commands**:
  - `merge`: Merge multiple grids with leveling options
  - `level`: Level one grid to a reference
  - `info`: Display grid information and statistics

## Algorithms Implemented

### DC Shift Correction
Corrects baseline offset differences between grids by calculating the mean difference in overlapping regions:
```
DC_shift = mean(reference_grid - target_grid) in overlap region
```

### Scale Adjustment
Matches the amplitude/variance between grids:
```
scale_factor = std(reference_grid) / std(target_grid) in overlap region
```

### Polynomial Surface Fitting
Fits polynomial surfaces to remove smooth trends, tilts, and gradients:
- **Linear (degree 1)**: `z = a + bx + cy`
- **Quadratic (degree 2)**: `z = a + bx + cy + dx² + ey² + fxy`
- **Cubic (degree 3)**: `z = a + bx + cy + dx² + ey² + fxy + gx³ + hy³ + ix²y + jxy²`

Uses least-squares fitting to determine coefficients from overlap data.

### Feathering/Blending
Uses distance transform to create smooth weight arrays that fade toward grid edges, ensuring seamless transitions in overlap regions.

## File Format Support

### ER Mapper (.ers) Format
- **Input**: Text header (.ers) + binary data file
- **Output**: IEEE 4-byte real data type
- **Metadata**: Projection, datum, coordinate system, cell size, null value
- **Registration**: Top-left corner registration point

## Usage Examples

### Python API
```python
from gridmerge import Grid, GridMerger

# Load grids
grid1 = Grid.read_ers("survey1.ers")
grid2 = Grid.read_ers("survey2.ers")

# Merge with automatic leveling
merged = GridMerger.merge_with_auto_leveling(
    [grid1, grid2],
    polynomial_degree=1,
    feather=True
)

# Save result
merged.write_ers("merged.ers")
```

### Command Line
```bash
# Merge grids with automatic leveling
gridmerge merge grid1.ers grid2.ers -o merged.ers --auto

# Level one grid to another
gridmerge level reference.ers input.ers -o leveled.ers --dc-shift --polynomial 1

# Display grid information
gridmerge info grid.ers
```

## Testing
- **Test Suite**: 12 comprehensive tests covering all core functionality
- **Coverage**: Grid operations, adjustments, leveling, and merging
- **Status**: All tests passing

## Dependencies
- Python >= 3.8
- NumPy >= 1.20.0 (numerical operations)
- SciPy >= 1.7.0 (distance transforms for feathering)

## Key Design Decisions

1. **ER Mapper Format**: Chosen as the primary format based on GridMerge documentation
2. **Modular Design**: Separate classes for Grid, Adjuster, and Merger for flexibility
3. **NumPy-based**: Efficient array operations for large grids
4. **Distance-based Feathering**: Uses SciPy's distance_transform_edt for smooth blending
5. **Least-squares Fitting**: Standard polynomial fitting for surface corrections

## Limitations & Future Enhancements

### Current Limitations
- Only supports ER Mapper format (can be extended to GeoTIFF, ASCII, etc.)
- Assumes grids have same cell size
- Single-band grids only

### Potential Enhancements
- Additional file format support (GeoTIFF, ASCII Grid, Geosoft GRD)
- Multi-band grid support
- Parallel processing for large datasets
- GUI application
- Advanced interpolation for non-aligned grids
- Visualization tools

## References

1. Minty Geophysics GridMerge Documentation:
   - https://www.mintygeophysics.com/GridMerge_Help/GridMerge_Help.html
   - https://www.gridmerge.com.au/

2. Related Software:
   - Intrepid Geophysics Grid Merge
   - Geosoft Oasis montaj
   - ER Mapper (historical)

## License
MIT License - See LICENSE file for details
