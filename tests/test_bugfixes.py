"""
Tests for bug fixes identified during code review.

These tests validate fixes for:
- Y-axis row inversion with different y-extents
- NaN handling in valid data masks
- ERS CRS metadata preservation
- ASCII header parsing robustness
- Cellsize validation warning in merge
- Large UTM coordinates causing LAPACK DGELSD error (Intel oneMKL Parameter 6)
- NaN/Inf filtering in DC shift, scale, and polynomial overlap calculations
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
        assert mask[0, 0] == True
        assert mask[0, 1] == False  # NaN should be invalid
        assert mask[0, 2] == True
        assert mask[1, 2] == False  # NaN should be invalid

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


class TestFeatheringSmallOverlap:
    """Tests for feathering bug: second grid becomes null with small overlap and nulls."""

    def test_nan_in_grid1_does_not_propagate_to_grid2_area(self):
        """NaN values in grid1 must not propagate into grid2's area via feathering."""
        # Grid1 has NaN in the region that overlaps with grid2
        data1 = np.full((10, 20), 100.0, dtype=np.float32)
        data1[:, 8:12] = np.nan  # NaN in the overlap zone
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1, nodata_value=-99999.0)

        data2 = np.full((10, 10), 200.0, dtype=np.float32)
        grid2 = Grid(data2, xmin=10, ymin=0, cellsize=1)

        merged = GridMerger.merge_two_grids(grid1, grid2, priority='blend', feather=True)

        # grid2's area (x=10 to x=20) must have no NaN
        grid2_area = merged.data[:, 10:]
        assert not np.any(np.isnan(grid2_area)), "NaN from grid1 must not propagate into grid2 area"
        assert (grid2_area != -99999.0).all(), "grid2 area must not become null due to NaN propagation"

    def test_small_overlap_with_nulls_grid2_unique_area_preserved(self):
        """Grid2's unique area must remain valid even with a small overlap and nulls in it."""
        data1 = np.full((20, 20), 100.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        # Grid2 has nulls in its overlap columns but valid data in its unique area
        data2 = np.full((20, 20), 200.0, dtype=np.float32)
        data2[:, :5] = -99999.0  # nulls in the 5-cell overlap region
        grid2 = Grid(data2, xmin=15, ymin=0, cellsize=1, nodata_value=-99999.0)

        merged = GridMerger.merge_two_grids(grid1, grid2, priority='blend', feather=True)

        # grid2's unique area (x=20 to x=35) must be fully valid (200.0)
        unique_area = merged.data[:, 20:]
        assert (unique_area != -99999.0).all(), "grid2 unique area must not become null"
        assert not np.any(np.isnan(unique_area)), "grid2 unique area must not become NaN"
        # Verify values are approximately 200.0
        assert np.allclose(unique_area, 200.0, atol=0.01)

    def test_small_overlap_one_cell_grid2_valid_area_preserved(self):
        """Grid2's data must appear in output even with a 1-cell overlap."""
        data1 = np.full((10, 10), 100.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        # Grid2 overlaps by 1 column (x=9-10)
        data2 = np.full((10, 10), 200.0, dtype=np.float32)
        grid2 = Grid(data2, xmin=9, ymin=0, cellsize=1)

        merged = GridMerger.merge_two_grids(grid1, grid2, priority='blend', feather=True)

        # grid2's unique area (x=10 to x=19) must be valid
        unique_area = merged.data[:, 10:]
        assert (unique_area != -99999.0).all(), "grid2 unique area must not be null with 1-cell overlap"
        assert not np.any(np.isnan(unique_area))

    def test_grid2_with_scattered_nulls_unique_area_preserved(self):
        """Grid2 with scattered nulls and small overlap must preserve its unique valid cells."""
        np.random.seed(42)
        data1 = np.full((20, 20), 100.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        # Grid2: scattered nulls, 2-cell overlap
        data2 = np.where(np.random.rand(20, 20) > 0.3, 200.0, -99999.0).astype(np.float32)
        grid2 = Grid(data2, xmin=18, ymin=0, cellsize=1, nodata_value=-99999.0)

        merged = GridMerger.merge_two_grids(grid1, grid2, priority='blend', feather=True)

        # Check that valid cells in grid2's unique area appear in merged output
        unique_valid_expected = (data2[:, 2:] != -99999.0).sum()
        unique_area_merged = merged.data[:, 20:]
        unique_valid_actual = (unique_area_merged != -99999.0).sum()
        assert unique_valid_actual == unique_valid_expected, \
            f"Expected {unique_valid_expected} valid cells in grid2 unique area, got {unique_valid_actual}"
        assert not np.any(np.isnan(unique_area_merged))

    def test_feather_distance_parameter_respected(self):
        """feather_distance parameter must limit the feathering zone."""
        data1 = np.full((10, 20), 100.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        data2 = np.full((10, 10), 200.0, dtype=np.float32)
        grid2 = Grid(data2, xmin=15, ymin=0, cellsize=1)

        # With feather_distance=1 (1 cell), cells at distance>1 from any null
        # should get full weight (be closer to their own grid value)
        merged_fd1 = GridMerger.merge_two_grids(
            grid1, grid2, priority='blend', feather=True, feather_distance=1
        )
        merged_fd5 = GridMerger.merge_two_grids(
            grid1, grid2, priority='blend', feather=True, feather_distance=5
        )

        # Both should produce valid output (no NaN, no extra nulls)
        assert not np.any(np.isnan(merged_fd1.data))
        assert not np.any(np.isnan(merged_fd5.data))
        assert (merged_fd1.data[:, 20:] != -99999.0).all()
        assert (merged_fd5.data[:, 20:] != -99999.0).all()


class TestLargeUTMCoordinates:
    """Tests for polynomial fitting with large UTM-scale coordinates.

    Real projected coordinate systems (e.g. EPSG:32754 UTM zone 54S) have
    easting values ~100 000–900 000 and northing values ~0–10 000 000.
    Without coordinate normalisation, the design matrix becomes extremely
    ill-conditioned and LAPACK's DGELSD routine raises:
      "Intel oneMKL ERROR: Parameter 6 was incorrect on entry to DGELSD"
    """

    def test_polynomial_fit_utm_coordinates_degree1(self):
        """fit_surface_in_overlap must not raise a LAPACK error for UTM coordinates."""
        # Simulate two overlapping grids with EPSG:32754-scale coordinates
        # (UTM zone 54S: easting ~500000, northing ~7000000)
        data1 = np.full((100, 100), 50.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=500000.0, ymin=7000000.0, cellsize=100.0)

        data2 = np.full((100, 100), 60.0, dtype=np.float32)
        grid2 = Grid(data2, xmin=505000.0, ymin=7000000.0, cellsize=100.0)

        # Must complete without error and return valid coefficients
        coeffs = GridAdjuster.fit_surface_in_overlap(grid1, grid2, degree=1)
        assert coeffs is not None
        # Constant difference of -10.0 → intercept ≈ -10, slopes ≈ 0
        assert abs(coeffs[0] - (-10.0)) < 0.1
        assert abs(coeffs[1]) < 0.01
        assert abs(coeffs[2]) < 0.01

    def test_polynomial_fit_utm_coordinates_degree2(self):
        """Degree-2 polynomial fitting must work with UTM-scale coordinates."""
        data1 = np.full((100, 100), 50.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=500000.0, ymin=7000000.0, cellsize=100.0)

        data2 = np.full((100, 100), 60.0, dtype=np.float32)
        grid2 = Grid(data2, xmin=505000.0, ymin=7000000.0, cellsize=100.0)

        coeffs = GridAdjuster.fit_surface_in_overlap(grid1, grid2, degree=2)
        assert coeffs is not None

    def test_merge_with_auto_leveling_utm_coordinates(self):
        """merge_with_auto_leveling must succeed with UTM-scale coordinates."""
        data1 = np.full((100, 100), 50.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=500000.0, ymin=7000000.0, cellsize=100.0)

        data2 = np.full((100, 100), 60.0, dtype=np.float32)
        grid2 = Grid(data2, xmin=505000.0, ymin=7000000.0, cellsize=100.0)

        merged = GridMerger.merge_with_auto_leveling([grid1, grid2],
                                                      polynomial_degree=1)
        assert merged is not None
        valid = merged.get_valid_data()
        assert len(valid) > 0
        assert np.all(np.isfinite(valid))

    def test_dc_shift_utm_coordinates(self):
        """DC shift calculation must work with UTM-scale coordinates."""
        data1 = np.full((50, 50), 100.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=300000.0, ymin=6500000.0, cellsize=1000.0)

        data2 = np.full((50, 50), 115.0, dtype=np.float32)
        grid2 = Grid(data2, xmin=320000.0, ymin=6500000.0, cellsize=1000.0)

        dc_shift = GridAdjuster.calculate_dc_shift(grid1, grid2)
        assert dc_shift is not None
        assert abs(dc_shift - (-15.0)) < 0.1


class TestNaNFilteringInAdjustment:
    """Tests for NaN/Inf filtering in DC shift, scale, and polynomial adjustment."""

    def test_dc_shift_ignores_nan_in_overlap(self):
        """DC shift must ignore NaN values in the overlap region."""
        data1 = np.full((10, 20), 100.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        data2 = np.full((10, 20), 110.0, dtype=np.float32)
        data2[:, :5] = np.nan  # NaN in first columns (overlap zone)
        grid2 = Grid(data2, xmin=10, ymin=0, cellsize=1)

        # Should still compute a valid DC shift from non-NaN overlap cells
        dc_shift = GridAdjuster.calculate_dc_shift(grid1, grid2)
        assert dc_shift is not None
        assert abs(dc_shift - (-10.0)) < 0.5

    def test_scale_factor_ignores_nan_in_overlap(self):
        """Scale factor calculation must ignore NaN values in the overlap region."""
        np.random.seed(1)
        data1 = (np.random.rand(20, 20) * 10 + 100).astype(np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        data2 = (np.random.rand(20, 20) * 20 + 100).astype(np.float32)
        data2[:3, 10:] = np.nan  # some NaN in the overlap
        grid2 = Grid(data2, xmin=10, ymin=0, cellsize=1)

        scale = GridAdjuster.calculate_scale_factor(grid1, grid2)
        assert scale is not None
        assert np.isfinite(scale)

    def test_polynomial_fit_ignores_nan_values(self):
        """fit_surface_in_overlap must ignore NaN values when computing the fit."""
        data1 = np.full((20, 20), 50.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        data2 = np.full((20, 20), 60.0, dtype=np.float32)
        data2[:5, 10:] = np.nan  # NaN in part of the overlap
        grid2 = Grid(data2, xmin=10, ymin=0, cellsize=1)

        coeffs = GridAdjuster.fit_surface_in_overlap(grid1, grid2, degree=1)
        assert coeffs is not None
        # Constant difference −10 in valid cells → intercept ≈ −10
        assert abs(coeffs[0] - (-10.0)) < 1.0

    def test_polynomial_fit_insufficient_points_returns_none(self):
        """fit_surface_in_overlap returns None when not enough valid overlap points."""
        # grid1 and grid2 share exactly 1 column of overlap (x=4..5)
        # In that column, all cells in grid2 are NaN → 0 valid points → None
        data1 = np.full((5, 5), 100.0, dtype=np.float32)
        grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)

        data2 = np.full((5, 5), 110.0, dtype=np.float32)
        data2[:, 0] = np.nan  # NaN in the single overlap column of grid2
        grid2 = Grid(data2, xmin=4, ymin=0, cellsize=1)

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            coeffs = GridAdjuster.fit_surface_in_overlap(grid1, grid2, degree=1)
        # Zero valid overlap points → must return None
        assert coeffs is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
