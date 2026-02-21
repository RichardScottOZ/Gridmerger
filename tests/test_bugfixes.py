"""
Tests for bug fixes identified during code review.

These tests validate fixes for:
- Y-axis row inversion with different y-extents
- NaN handling in valid data masks
- ERS CRS metadata preservation
- ASCII header parsing robustness
- Cellsize validation warning in merge
"""

import numpy as np
import pytest
import tempfile
import os
import warnings

from gridmerge import Grid, GridMerger, GridAdjuster


class TestYAxisOverlapFix:
    """Tests for the Y-axis row inversion fix in get_overlap."""

    def test_overlap_different_y_extents(self):
        """Test overlap detection when grids have different y-extents."""
        # Grid1: y=0 to y=10 (10 rows, cellsize=1)
        # Data has a gradient in y direction
        data1 = np.arange(100).reshape(10, 10).astype(np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        # Grid2: y=5 to y=15 (10 rows, cellsize=1)
        data2 = np.arange(200, 300).reshape(10, 10).astype(np.float32)
        grid2 = Grid(data2, xmin=0, ymin=5, cellsize=1)

        overlap = grid1.get_overlap(grid2)
        assert overlap is not None

        r1, c1, r2, c2 = overlap

        # Overlap is y=5 to y=10
        # In grid1 (ymax=10): rows 0-4 correspond to y=10 down to y=5
        # So overlap should be rows 0:5
        assert r1 == slice(0, 5)
        assert c1 == slice(0, 10)

        # In grid2 (ymax=15): rows 5-9 correspond to y=10 down to y=5
        # So overlap should be rows 5:10
        assert r2 == slice(5, 10)
        assert c2 == slice(0, 10)

    def test_overlap_same_y_extent(self):
        """Test that overlap still works for same y-extent grids."""
        data1 = np.ones((10, 10), dtype=np.float32) * 100
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        data2 = np.ones((10, 10), dtype=np.float32) * 110
        grid2 = Grid(data2, xmin=5, ymin=0, cellsize=1)

        overlap = grid1.get_overlap(grid2)
        assert overlap is not None

        r1, c1, r2, c2 = overlap
        # Full y-extent overlap
        assert r1 == slice(0, 10)
        assert r2 == slice(0, 10)
        # X overlap: x=5 to x=10
        assert c1 == slice(5, 10)
        assert c2 == slice(0, 5)

    def test_dc_shift_different_y_extents(self):
        """Test DC shift calculation with different y-extents and non-uniform data."""
        # Grid1: y=0 to y=10, data has y-gradient
        # row 0 = top (y=10), row 9 = bottom (y=0)
        data1 = np.zeros((10, 10), dtype=np.float32)
        for r in range(10):
            data1[r, :] = 100.0 + r  # Row 0=100, row 9=109

        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        # Grid2: y=5 to y=15, same pattern but with offset of 20
        data2 = np.zeros((10, 10), dtype=np.float32)
        for r in range(10):
            data2[r, :] = 120.0 + r

        grid2 = Grid(data2, xmin=0, ymin=5, cellsize=1)

        # Overlap region: y=5 to y=10
        # Grid1 overlap: rows 0-4 (y=10 down to y=5), values 100-104
        # Grid2 overlap: rows 5-9 (y=10 down to y=5), values 125-129
        # DC shift = mean(grid1_overlap - grid2_overlap)
        # = mean([100-125, 101-126, 102-127, 103-128, 104-129])
        # = mean([-25, -25, -25, -25, -25]) = -25
        dc_shift = GridAdjuster.calculate_dc_shift(grid1, grid2)
        assert dc_shift is not None
        assert abs(dc_shift - (-25.0)) < 0.01

    def test_merge_different_y_extents(self):
        """Test merging grids with different y-extents."""
        # Grid1: y=0 to y=5
        data1 = np.full((5, 10), 100.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        # Grid2: y=3 to y=8 (overlaps y=3-5 with grid1)
        data2 = np.full((5, 10), 200.0, dtype=np.float32)
        grid2 = Grid(data2, xmin=0, ymin=3, cellsize=1)

        merged = GridMerger.merge_two_grids(grid1, grid2, priority='first', feather=False)

        # Output should span y=0 to y=8
        assert merged.nrows == 8
        assert merged.ncols == 10

        # Grid1 data (y=0-5, rows 3-7 from top): should be 100
        # Grid2 non-overlap data (y=5-8, rows 0-2 from top): should be 200
        valid = merged.get_valid_data()
        assert 100.0 in valid  # Grid1 data present
        assert 200.0 in valid  # Grid2 data present

    def test_polynomial_fitting_different_y_extents(self):
        """Test polynomial fitting with different y-extents."""
        # Grid1: y=0 to y=10 with constant value
        data1 = np.full((10, 10), 50.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        # Grid2: y=5 to y=15 with constant offset
        data2 = np.full((10, 10), 60.0, dtype=np.float32)
        grid2 = Grid(data2, xmin=0, ymin=5, cellsize=1)

        coeffs = GridAdjuster.fit_surface_in_overlap(grid1, grid2, degree=1)
        assert coeffs is not None
        # Constant difference of -10, so coefficients should be ~[-10, 0, 0]
        assert abs(coeffs[0] - (-10.0)) < 1.0
        assert abs(coeffs[1]) < 0.5  # x coefficient near zero
        assert abs(coeffs[2]) < 0.5  # y coefficient near zero


class TestNaNHandling:
    """Tests for NaN handling in valid data masks."""

    def test_nan_excluded_from_valid_mask(self):
        """Test that NaN values are excluded from valid mask."""
        data = np.array([[1.0, np.nan, 3.0],
                         [4.0, 5.0, np.nan]], dtype=np.float32)
        grid = Grid(data, xmin=0, ymin=0, cellsize=1, nodata_value=-99999.0)

        mask = grid.get_valid_mask()
        assert mask[0, 0] is np.True_
        assert mask[0, 1] is np.False_  # NaN should be invalid
        assert mask[0, 2] is np.True_
        assert mask[1, 2] is np.False_  # NaN should be invalid

    def test_nan_excluded_from_valid_data(self):
        """Test that NaN values are excluded from valid data."""
        data = np.array([[1.0, np.nan, 3.0],
                         [4.0, 5.0, -99999.0]], dtype=np.float32)
        grid = Grid(data, xmin=0, ymin=0, cellsize=1, nodata_value=-99999.0)

        valid = grid.get_valid_data()
        assert len(valid) == 4  # 1.0, 3.0, 4.0, 5.0 (NaN and nodata excluded)
        assert not np.any(np.isnan(valid))

    def test_inf_excluded_from_valid_data(self):
        """Test that Inf values are excluded from valid data."""
        data = np.array([[1.0, np.inf, 3.0],
                         [4.0, -np.inf, 5.0]], dtype=np.float32)
        grid = Grid(data, xmin=0, ymin=0, cellsize=1, nodata_value=-99999.0)

        valid = grid.get_valid_data()
        assert len(valid) == 4  # 1.0, 3.0, 4.0, 5.0 (Inf values excluded)
        assert np.all(np.isfinite(valid))


class TestERSCRSPreservation:
    """Tests for ERS format CRS metadata preservation."""

    def test_crs_preserved_in_ers_round_trip(self):
        """Test that CRS is preserved when writing and reading ERS format."""
        data = np.random.rand(10, 10).astype(np.float32) * 100
        grid = Grid(data, xmin=500000, ymin=6500000, cellsize=100.0,
                    metadata={'crs': 'EPSG:32755'})

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'test.ers')
            grid.write(filepath)
            grid2 = Grid.read(filepath)

            assert grid2.metadata.get('crs') == 'EPSG:32755'

    def test_no_crs_still_works(self):
        """Test that grids without CRS still work correctly."""
        data = np.ones((5, 5), dtype=np.float32) * 42.0
        grid = Grid(data, xmin=0, ymin=0, cellsize=1.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'test.ers')
            grid.write(filepath)
            grid2 = Grid.read(filepath)

            assert 'crs' not in grid2.metadata or grid2.metadata.get('crs') is None


class TestASCIIHeaderParsing:
    """Tests for ASCII header parsing robustness."""

    def test_scientific_notation_nodata(self):
        """Test that scientific notation in headers is parsed correctly."""
        with tempfile.NamedTemporaryFile(suffix='.asc', mode='w', delete=False) as f:
            filepath = f.name
            f.write("ncols 3\n")
            f.write("nrows 2\n")
            f.write("xllcorner 0.0\n")
            f.write("yllcorner 0.0\n")
            f.write("cellsize 1e2\n")
            f.write("nodata_value -1e10\n")
            f.write("1.0 2.0 3.0\n")
            f.write("4.0 5.0 6.0\n")

        try:
            grid = Grid.read_ascii(filepath)
            assert grid.cellsize == 100.0
            assert grid.nodata_value == -1e10
            assert grid.ncols == 3
            assert grid.nrows == 2
        finally:
            os.unlink(filepath)


class TestCellsizeValidation:
    """Tests for cellsize validation in merge."""

    def test_different_cellsize_warning(self):
        """Test that merging grids with different cellsizes produces a warning."""
        grid1 = Grid(np.ones((10, 10), dtype=np.float32), xmin=0, ymin=0, cellsize=100)
        grid2 = Grid(np.ones((10, 10), dtype=np.float32), xmin=900, ymin=0, cellsize=101)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            GridMerger.merge_two_grids(grid1, grid2, feather=False)
            cellsize_warnings = [x for x in w if "cell sizes" in str(x.message).lower()]
            assert len(cellsize_warnings) == 1

    def test_same_cellsize_no_warning(self):
        """Test that merging grids with same cellsize produces no warning."""
        grid1 = Grid(np.ones((10, 10), dtype=np.float32), xmin=0, ymin=0, cellsize=100)
        grid2 = Grid(np.ones((10, 10), dtype=np.float32), xmin=900, ymin=0, cellsize=100)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            GridMerger.merge_two_grids(grid1, grid2, feather=False)
            cellsize_warnings = [x for x in w if "cell sizes" in str(x.message).lower()]
            assert len(cellsize_warnings) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
