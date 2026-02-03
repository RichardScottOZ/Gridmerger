# Multi-Format Support - User Guide

## Overview

GridMerge now supports multiple grid formats, allowing you to work with different data sources without manual conversion. **The key benefit: you can mix and match formats freely!**

## Supported Formats

### 1. ER Mapper (.ers)
- **Extensions**: `.ers`
- **Requirements**: None (always available)
- **Description**: Industry-standard geophysical data format
- **Structure**: Text header (.ers) + binary data file
- **Metadata**: Full projection, datum, coordinate system support

### 2. ASCII Grid (.asc, .grd)
- **Extensions**: `.asc`, `.grd`
- **Requirements**: None (always available)
- **Description**: Simple text-based grid format
- **Structure**: Header rows + space-separated values
- **Compatibility**: Widely supported by GIS and geophysical software

### 3. GeoTIFF (.tif, .tiff)
- **Extensions**: `.tif`, `.tiff`
- **Requirements**: `rasterio` package (optional)
  ```bash
  pip install rasterio
  # or
  pip install -e ".[geotiff]"
  ```
- **Description**: Industry-standard georeferenced raster format
- **Metadata**: Full CRS and geotransform support
- **Compatibility**: Universal GIS format

## Format Auto-Detection

GridMerge automatically detects the format based on file extension:

```python
from gridmerge import Grid

# Auto-detect from extension
grid1 = Grid.read("survey.tif")    # GeoTIFF
grid2 = Grid.read("survey.asc")    # ASCII Grid
grid3 = Grid.read("survey.ers")    # ER Mapper
```

You can also explicitly specify the format:

```python
# Read a file with non-standard extension
grid = Grid.read("mydata.dat", format="ascii")

# Write with explicit format
grid.write("output.xyz", format="geotiff")
```

## Format Conversion

Converting between formats is simple:

```python
from gridmerge import Grid

# Read in one format, write in another
grid = Grid.read("input.asc")
grid.write("output.tif")  # Convert ASCII → GeoTIFF
grid.write("output.ers")  # Convert ASCII → ER Mapper
```

### Batch Conversion Example

```python
import glob
from gridmerge import Grid

# Convert all ASCII grids to GeoTIFF
for asc_file in glob.glob("data/*.asc"):
    grid = Grid.read(asc_file)
    tif_file = asc_file.replace(".asc", ".tif")
    grid.write(tif_file)
    print(f"Converted {asc_file} → {tif_file}")
```

## Mixing Formats

**The killer feature**: Merge grids from different formats without conversion!

### Python API Example

```python
from gridmerge import Grid, GridMerger

# Load grids in different formats
magnetic = Grid.read("magnetic_survey.tif")      # GeoTIFF
radiometric = Grid.read("radiometric_survey.asc") # ASCII
legacy = Grid.read("legacy_survey.ers")          # ER Mapper

# Merge them directly!
merged = GridMerger.merge_with_auto_leveling(
    [magnetic, radiometric, legacy],
    polynomial_degree=1,
    feather=True
)

# Save in your preferred format
merged.write("combined_survey.tif")
```

### Command-Line Example

```bash
# Merge mixed formats
gridmerge merge \
    data/survey1.tif \
    data/survey2.asc \
    data/survey3.ers \
    -o output/merged.tif \
    --auto

# Level one format to another
gridmerge level reference.tif input.asc -o leveled.ers --dc-shift --polynomial 2

# Get info on any format
gridmerge info data/*.tif data/*.asc data/*.ers
```

## Real-World Workflow Examples

### Scenario 1: Combining Legacy and New Data

```python
from gridmerge import Grid, GridMerger

# Legacy survey from 1990s (ER Mapper format)
legacy = Grid.read("surveys/1995_magnetic.ers")

# Recent survey from contractor (GeoTIFF)
recent = Grid.read("surveys/2024_magnetic.tif")

# Your internal data (ASCII Grid)
internal = Grid.read("surveys/2020_magnetic.asc")

# Merge and level all surveys
merged = GridMerger.merge_with_auto_leveling(
    [legacy, recent, internal],
    polynomial_degree=2,  # Remove larger-scale trends
    feather=True
)

# Output in modern format
merged.write("final/compiled_magnetic_survey.tif")
```

### Scenario 2: Format Standardization

```python
import os
from gridmerge import Grid

def standardize_to_geotiff(input_dir, output_dir):
    """Convert all grids to GeoTIFF format."""
    for filename in os.listdir(input_dir):
        if filename.endswith(('.ers', '.asc', '.grd')):
            input_path = os.path.join(input_dir, filename)
            output_name = os.path.splitext(filename)[0] + '.tif'
            output_path = os.path.join(output_dir, output_name)
            
            grid = Grid.read(input_path)
            grid.write(output_path)
            print(f"Converted: {filename} → {output_name}")

standardize_to_geotiff("raw_data/", "processed/")
```

### Scenario 3: Quick Format Check

```bash
# Check what formats you have
gridmerge info data/*

# Output will show format for each file:
# Grid: data/survey1.tif
#   Format: GEOTIFF
#   ...
# Grid: data/survey2.asc
#   Format: ASCII
#   ...
```

## Format Compatibility Notes

### ASCII Grid
- **Pros**: Human-readable, no dependencies, universal support
- **Cons**: Larger file size, slower I/O
- **Best for**: Small grids, data exchange, debugging

### ER Mapper
- **Pros**: Compact, standard in geophysics, no dependencies
- **Cons**: Requires two files (.ers + binary), less common outside geophysics
- **Best for**: Geophysical surveys, legacy data

### GeoTIFF
- **Pros**: Universal GIS format, single file, efficient
- **Cons**: Requires rasterio/GDAL library
- **Best for**: Modern workflows, integration with GIS software

## Troubleshooting

### GeoTIFF Support Not Available

If you get an error about GeoTIFF support:

```
ImportError: GeoTIFF support requires either 'rasterio' or 'gdal' package.
```

Install rasterio:
```bash
pip install rasterio
```

Or use ASCII/ERS formats which have no extra dependencies.

### Mixed Cell Sizes

All grids must have the same cell size for merging:

```python
# Check cell sizes
grid1 = Grid.read("survey1.tif")
grid2 = Grid.read("survey2.asc")
print(f"Grid 1 cell size: {grid1.cellsize}")
print(f"Grid 2 cell size: {grid2.cellsize}")

# They must match!
```

### Coordinate Systems

GridMerge doesn't reproject data. Ensure all grids are in the same coordinate system:

```python
# Check coordinate systems
print(f"Grid 1 CRS: {grid1.metadata.get('projection')}")
print(f"Grid 2 CRS: {grid2.metadata.get('projection')}")
```

## Performance Tips

1. **ASCII Grid**: Slowest I/O, but no dependencies
2. **ER Mapper**: Fast I/O, compact files
3. **GeoTIFF**: Fast I/O, but requires rasterio

For large datasets:
- Use ER Mapper or GeoTIFF for better performance
- Convert ASCII grids to binary formats if processing frequently

## Summary

✅ **No conversion required** - Mix formats freely  
✅ **Auto-detection** - Just specify the filename  
✅ **Easy conversion** - Read one format, write another  
✅ **Backward compatible** - Existing ERS code still works  
✅ **Optional dependencies** - ASCII/ERS always available  

**Bottom line**: Use whatever format your data comes in. GridMerge handles the rest!
