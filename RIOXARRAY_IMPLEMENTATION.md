# rioxarray Implementation Summary



## What Was Added

### Core Functionality (gridmerge/grid.py)

Five new methods added to the `Grid` class:

1. **`to_xarray(crs=None)`** - Convert Grid to xarray DataArray
   - Enables integration with xarray ecosystem
   - Preserves spatial metadata and CRS

2. **`from_xarray(da, nodata_value=None, metadata=None)`** - Create Grid from xarray
   - Round-trip conversion Grid ↔ xarray
   - Extracts CRS and spatial properties automatically

3. **`resample(target_cellsize, method='bilinear')`** - Resample to different resolution
   - Downsample (coarsen): 50m → 100m using 'average'
   - Upsample (refine): 100m → 50m using 'bilinear' or 'cubic'
   - 13+ resampling methods supported

4. **`reproject(target_crs, method='bilinear')`** - Reproject to different CRS
   - Transform between UTM zones: UTM 55S → UTM 54S
   - Geographic conversion: UTM → WGS84 lat/lon
   - Any EPSG code or PROJ string supported

5. **`match_grid(reference, method='bilinear')`** - Match resolution AND CRS to reference
   - One-step solution for heterogeneous datasets
   - Automatically reprojects + resamples
   - Output matches reference extent, resolution, and CRS

### Installation (pyproject.toml)

Added new optional dependency group:

```toml
[project.optional-dependencies]
rioxarray = [
    "xarray>=0.20.0",
    "rioxarray>=0.13.0",
    "rasterio>=1.2.0",
]
all = [
    "rasterio>=1.2.0",
    "xarray>=0.20.0",
    "rioxarray>=0.13.0",
]
```

Install with:
```bash
pip install -e ".[rioxarray]"  # Just rioxarray features
pip install -e ".[all]"        # All optional features
```

### Documentation

#### README.md
Added 100+ line section on rioxarray functionality with:
- Installation instructions
- Quick start examples
- Complete workflow for heterogeneous datasets
- List of resampling methods
- Links to comprehensive guides

#### RIOXARRAY_GUIDE.md (New, 550+ lines)
Comprehensive guide covering:
- Overview and core concepts
- Resampling (up/down) with examples
- Reprojection between CRS
- Matching to reference grid
- Complete workflows (3 real-world scenarios)
- Resampling methods comparison table
- Best practices
- xarray integration
- Comparison to manual GDAL approaches

### Examples (examples/rioxarray_demo.py)

New 450+ line demonstration script with 5 complete scenarios:

1. **Demo 1**: Resampling to different resolutions
   - Create high-res grid (50m)
   - Downsample to 100m, 200m
   - Upsample to 25m

2. **Demo 2**: Reprojection to different CRS
   - UTM Zone 55S → Geographic WGS84
   - UTM Zone 55S → UTM Zone 54S

3. **Demo 3**: Matching to reference grid
   - Different resolution, same CRS
   - Different CRS, different resolution

4. **Demo 4**: Merging heterogeneous datasets
   - 3 surveys: different resolutions AND CRS
   - Match all to reference
   - Merge with leveling

5. **Demo 5**: xarray interoperability
   - Convert Grid ↔ xarray
   - Use xarray operations
   - Integration with ecosystem

Run with: `python examples/rioxarray_demo.py`

### Tests (tests/test_rioxarray.py)

New 360+ line test suite with 20+ test cases:

**TestXArrayConversion**:
- to_xarray conversion
- from_xarray conversion
- Round-trip preservation

**TestResampling**:
- Downsample to coarser resolution
- Upsample to finer resolution
- Multiple resampling methods
- CRS preservation

**TestReprojection**:
- Reproject between UTM zones
- Reproject to geographic coordinates
- CRS validation
- Multiple methods

**TestMatchGrid**:
- Match different resolution, same CRS
- Match different CRS, same resolution
- Match both different
- CRS assumption handling

**TestResamplingMethods**:
- Invalid method error handling
- All 13+ documented methods

**TestImportErrors**:
- Graceful failures without rioxarray

Run with: `pytest tests/test_rioxarray.py` (requires rioxarray installed)

## Usage Examples

### Basic Resampling

```python
from gridmerge import Grid

# Load grid
grid = Grid.read("survey_50m.tif")

# Downsample to 100m
grid_100m = grid.resample(target_cellsize=100, method='average')
grid_100m.write("survey_100m.tif")

# Upsample to 25m
grid_25m = grid.resample(target_cellsize=25, method='bilinear')
grid_25m.write("survey_25m.tif")
```

### Basic Reprojection

```python
from gridmerge import Grid

# Load grid in UTM Zone 55S
grid_utm55 = Grid.read("survey_utm55.tif")

# Reproject to UTM Zone 54S
grid_utm54 = grid_utm55.reproject(target_crs='EPSG:32754', method='bilinear')
grid_utm54.write("survey_utm54.tif")

# Reproject to Geographic (WGS84)
grid_geo = grid_utm55.reproject(target_crs='EPSG:4326', method='bilinear')
grid_geo.write("survey_geo.tif")
```

### Match to Reference (Complete Workflow)

```python
from gridmerge import Grid, GridMerger

# Load grids with different resolutions and CRS
reference = Grid.read("ref_100m_utm55.tif")      # Reference: 100m, UTM 55S
survey_a = Grid.read("survey_50m_utm55.tif")     # 50m, same CRS
survey_b = Grid.read("survey_200m_utm54.tif")    # 200m, different CRS!

# Match all to reference (one line each!)
survey_a_matched = survey_a.match_grid(reference, method='average')
survey_b_matched = survey_b.match_grid(reference, method='bilinear')

# Now all grids have:
# - Same resolution (100m)
# - Same CRS (UTM 55S)
# - Same/compatible extent

# Merge seamlessly with leveling
merged = GridMerger.merge_with_auto_leveling(
    [reference, survey_a_matched, survey_b_matched],
    use_dc_shift=True,
    polynomial_degree=1,
    feather_distance=10
)

merged.write("regional_compilation.tif")
```

### Automatic Multi-Grid Processing

```python
from gridmerge import Grid, GridMerger
import statistics

# Load all surveys (mixed resolutions and CRS)
files = ["survey1.tif", "survey2.tif", "survey3.tif", "survey4.tif"]
grids = [Grid.read(f) for f in files]

# Choose reference (e.g., finest resolution)
reference = min(grids, key=lambda g: g.cellsize)
print(f"Reference: {reference.cellsize}m, {reference.metadata['crs']}")

# Match all others to reference
grids_matched = [reference.copy()]
for grid in grids:
    if grid is not reference:
        matched = grid.match_grid(reference, method='bilinear')
        grids_matched.append(matched)

# Merge with automatic leveling
merged = GridMerger.merge_with_auto_leveling(
    grids_matched,
    use_dc_shift=True,
    polynomial_degree=1
)

merged.write("unified_compilation.tif")
```

## Key Benefits

1. **No External Preprocessing**: Do everything in Python, no GDAL command-line needed
2. **Seamless Integration**: Works with existing GridMerge leveling and merging
3. **One-Line Operations**: Simple API for complex transformations
4. **Reference Matching**: Unified solution for heterogeneous datasets
5. **Flexible Methods**: 13+ resampling methods for different data types
6. **xarray Ecosystem**: Integration with scientific Python stack
7. **Optional Dependency**: Graceful fallback if rioxarray not installed

## Resampling Methods Available

| Method | Best For | Use Case |
|--------|----------|----------|
| `'average'` | Downsampling continuous data | Magnetic, gravity surveys |
| `'bilinear'` | General purpose | Default choice |
| `'cubic'` | Smooth interpolation | High-quality upsampling |
| `'nearest'` | Discrete/classification data | Preserving exact values |
| `'lanczos'` | High-quality upsampling | Sharp edges |
| `'med'` | Noise reduction | Downsampling noisy data |
| `'min'`/`'max'` | Anomaly detection | Preserving extremes |

Plus: `cubic_spline`, `gauss`, `mode`, `q1`, `q3`

## Error Handling & Validation

- **Graceful import errors**: Clear messages when rioxarray not installed
- **CRS validation**: Raises error if CRS required but missing
- **CRS warnings**: Warns when assuming EPSG:4326 as fallback
- **Single-pixel rejection**: Clear error for invalid single-pixel grids
- **Method validation**: Helpful error for invalid resampling methods

## Backward Compatibility

- ✅ All existing functionality preserved
- ✅ Optional dependency (doesn't break without rioxarray)
- ✅ No changes to core Grid/Merger/Adjuster APIs
- ✅ All previous tests still pass
- ✅ Works with all supported formats (ERS, GeoTIFF, ASCII)

## Performance Characteristics

- **Memory efficient**: Uses rioxarray's chunked operations
- **Lazy evaluation**: Operations computed only when needed
- **Scalable**: Works with large grids via xarray/dask
- **Fast**: Optimized GDAL reprojection algorithms

## Related Documentation

- [README.md](README.md) - Main documentation with quick start
- [RIOXARRAY_GUIDE.md](RIOXARRAY_GUIDE.md) - Comprehensive 550+ line guide
- [DIFFERENT_RESOLUTIONS.md](DIFFERENT_RESOLUTIONS.md) - Manual resampling approaches
- [examples/rioxarray_demo.py](examples/rioxarray_demo.py) - 5 complete demonstrations
- [tests/test_rioxarray.py](tests/test_rioxarray.py) - 20+ test cases

## Commit History

1. **36e311d**: Add rioxarray support for resampling and reprojection
   - Core functionality in grid.py
   - Tests and examples
   - README updates
   - pyproject.toml dependencies

2. **0842c22**: Add comprehensive rioxarray documentation guide
   - RIOXARRAY_GUIDE.md (550+ lines)

3. **f8bbe9e**: Improve error handling and add clarifying comments
   - Better single-pixel validation
   - CRS assumption warnings
   - Clarifying comments

## Summary

**Complete implementation** of rioxarray-based resampling and reprojection functionality as requested. Users can now:

✅ Resample grids to any resolution (up or down)
✅ Reproject grids to any CRS (UTM, Geographic, State Plane, etc.)
✅ Match grids to reference (resolution + CRS + extent in one call)
✅ Merge heterogeneous datasets seamlessly (different resolutions AND projections)
✅ Use 13+ resampling methods optimized for different data types
✅ Integrate with xarray ecosystem for advanced workflows

All with clean API, comprehensive documentation, working examples, and thorough testing.
