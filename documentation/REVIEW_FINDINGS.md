# Code Review Findings: GridMerger

## Summary

A thorough code review of the GridMerger package identified **3 major bugs**, **3 minor bugs**, and several **improvement suggestions**. All bugs have been fixed and validated with new tests.

---

## Major Bugs Found and Fixed

### 1. Y-Axis Row Inversion in Overlap Detection and Merging

**Severity:** Major  
**Files affected:** `gridmerge/grid.py`, `gridmerge/merge.py`, `gridmerge/adjust.py`  
**Impact:** Incorrect overlap comparison, DC shift, polynomial fitting, and merge placement when grids have different Y-extents

**Description:**  
Grid data in all supported formats (ERS, GeoTIFF, ASCII Grid) is stored top-down: `data[0]` = northernmost (topmost) row, corresponding to `ymax`. However, the `get_overlap()` method computed row indices as if `data[0]` = southernmost (bottommost) row at `ymin`:

```python
# BEFORE (incorrect):
self_row_start = int(np.round((overlap_ymin - self.ymin) / self.cellsize))
self_row_end = int(np.round((overlap_ymax - self.ymin) / self.cellsize))
```

This caused overlap comparisons to extract the **wrong physical regions** when grids had different Y-extents. For example, when comparing grids at y=0..10 and y=5..15, the overlap (y=5..10) would instead extract y=0..5 from grid1 and y=10..15 from grid2.

The bug was masked in existing tests because all overlapping test grids shared the same Y-extent, making the row inversion invisible.

**Fix:**  
Changed row computation to measure from `ymax` (top) instead of `ymin` (bottom):

```python
# AFTER (correct):
self_row_start = int(np.round((self.ymax - overlap_ymax) / self.cellsize))
self_row_end = int(np.round((self.ymax - overlap_ymin) / self.cellsize))
```

Applied consistently in:
- `Grid.get_overlap()` — overlap slice computation
- `GridMerger.merge_two_grids()` — grid placement in output
- `GridAdjuster.fit_surface_in_overlap()` — polynomial fitting coordinates
- `GridAdjuster.apply_polynomial_correction()` — correction surface coordinates

**Tests added:** `TestYAxisOverlapFix` class with 5 tests validating correct behavior with different Y-extents.

---

### 2. ERS Format Does Not Preserve CRS Metadata

**Severity:** Major  
**Files affected:** `gridmerge/grid.py` (`write_ers`, `read_ers`)  
**Impact:** CRS information lost during ERS write/read round-trip; caused `test_inspect_grids` to fail

**Description:**  
When a Grid was created with `metadata={'crs': 'EPSG:32755'}` and written to ERS format, the CRS value was silently discarded. The `read_ers()` method only read standard ERS header fields (`Projection`, `Datum`, `CoordinateType`) and never restored the `crs` key in metadata.

**Fix:**  
- `write_ers()` now writes a `CRS = <value>` field to the ERS header when the metadata contains a `crs` key
- `read_ers()` now reads the `CRS` field from the header and stores it in `metadata['crs']`

**Tests added:** `TestERSCRSPreservation` class with 2 tests.

---

### 3. NaN and Infinite Values Not Handled in Valid Data Masks

**Severity:** Major  
**Files affected:** `gridmerge/grid.py` (`get_valid_mask`, `get_valid_data`)  
**Impact:** NaN and Inf values treated as valid data, corrupting statistical calculations

**Description:**  
The `get_valid_mask()` method only checked for equality with `nodata_value`. NaN and Inf values (common in geophysical data from division by zero or sensor errors) were treated as valid data, causing incorrect mean/std calculations in DC shift, scale factor, and other operations.

**Fix:**  
Added `np.isfinite()` check alongside the nodata check:

```python
# BEFORE:
return self.data != self.nodata_value

# AFTER:
return (self.data != self.nodata_value) & np.isfinite(self.data)
```

Also refactored `get_valid_data()` to use `get_valid_mask()` to avoid code duplication.

**Tests added:** `TestNaNHandling` class with 3 tests covering NaN, Inf, and -Inf values.

---

## Minor Bugs Found and Fixed

### 4. Bare `except:` Clause in `write_geotiff()`

**File:** `gridmerge/grid.py`, line ~456  
**Impact:** Could catch `SystemExit`, `KeyboardInterrupt`, and other non-Exception types

**Fix:** Changed `except:` to `except Exception:` for the CRS parsing fallback.

---

### 5. ASCII Header Parsing Fails with Scientific Notation

**File:** `gridmerge/grid.py` (`read_ascii`)  
**Impact:** Reading ASCII grids with scientific notation values (e.g., `cellsize 1e2`) would crash

**Description:**  
The header parser used `'.' in parts[1]` to decide between `int()` and `float()` parsing. Values in scientific notation like `1e2` or `1e-5` don't contain a dot, so `int('1e2')` would raise `ValueError`.

**Fix:**  
Changed to try `int()` first with `float()` fallback:

```python
try:
    header[key] = int(parts[1])
except ValueError:
    header[key] = float(parts[1])
```

**Tests added:** `TestASCIIHeaderParsing` with 1 test for scientific notation.

---

### 6. No Cellsize Validation in `merge_two_grids()`

**File:** `gridmerge/merge.py`  
**Impact:** Silently produced incorrect results when merging grids with different cell sizes

**Description:**  
`merge_two_grids()` used `grid1.cellsize` for the output without checking if `grid2.cellsize` matched. While `get_overlap()` validates cellsize compatibility, `merge_two_grids()` does not call `get_overlap()` for non-overlap cases.

**Fix:** Added a `np.isclose()` check with a `warnings.warn()` if cellsizes differ.

**Tests added:** `TestCellsizeValidation` with 2 tests.

---

## Improvement Suggestions (Not Implemented)

### 1. Non-Square Pixel Support in GeoTIFF

The `read_geotiff()` method uses `transform.a` (x-pixel-size) for both x and y dimensions. If a GeoTIFF has non-square pixels (`transform.a != abs(transform.e)`), the y-extent calculation will be incorrect. Consider adding a check and warning.

### 2. `feather_distance` Parameter Not Propagated

The `merge_two_grids()` method accepts a `feather_distance` parameter, but `merge_multiple_grids()` and `merge_with_auto_leveling()` do not pass it through. Users cannot control feather distance when merging multiple grids.

### 3. `interactive_reproject()` Has No Timeout

The function uses `input()` for interactive prompts, which would hang indefinitely in automated environments (CI/CD, scripts). Consider adding a non-interactive mode or timeout.

### 4. ASCII Grid Format Robustness

The ASCII grid reader breaks parsing on the first line that doesn't match expected header keys. Some ASCII grid files may have comments, extra metadata, or non-standard header fields that would cause premature header parsing termination.

### 5. Memory Efficiency for Large Merges

The `merge_two_grids()` method creates multiple full-size arrays (output, weights, contributions) simultaneously. For very large grids, this could be memory-intensive. Consider streaming or chunked processing for large datasets.

### 6. Progress Tracking for Large-Scale Operations

The `merge_multiple_grids()` method processes grids sequentially without progress reporting. For large numbers of grids (47+), adding optional progress callbacks or logging would improve user experience.

---

## Test Coverage Summary

| Category | Tests Added | Status |
|---|---|---|
| Y-axis overlap fix | 5 | ✅ All passing |
| NaN handling | 3 | ✅ All passing |
| ERS CRS preservation | 2 | ✅ All passing |
| ASCII header parsing | 1 | ✅ All passing |
| Cellsize validation | 2 | ✅ All passing |
| **Total new tests** | **13** | **✅ All passing** |
| **Total tests (existing + new)** | **87 (65 passing, 22 skipped)** | **✅ No failures** |

The 22 skipped tests require `rioxarray` which is an optional dependency.
