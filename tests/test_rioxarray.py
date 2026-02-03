"""
Tests for rioxarray-based resampling and reprojection functionality.

These tests require xarray and rioxarray to be installed.
Run with: pytest tests/test_rioxarray.py
"""

import pytest
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gridmerge import Grid

# Check if rioxarray is available
try:
    import xarray as xr
    import rioxarray
    RIOXARRAY_AVAILABLE = True
except ImportError:
    RIOXARRAY_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not RIOXARRAY_AVAILABLE,
    reason="rioxarray not installed (pip install xarray rioxarray)"
)


def create_test_grid(ncols=50, nrows=50, cellsize=100, crs='EPSG:32755'):
    """Create a simple test grid."""
    data = np.random.rand(nrows, ncols).astype(np.float32) * 100 + 52000
    return Grid(
        data=data,
        xmin=500000,
        ymin=6000000,
        cellsize=cellsize,
        nodata_value=-99999.0,
        metadata={'crs': crs}
    )


class TestXArrayConversion:
    """Test conversion between Grid and xarray."""
    
    def test_to_xarray(self):
        """Test converting Grid to xarray DataArray."""
        grid = create_test_grid()
        da = grid.to_xarray()
        
        assert da.shape == grid.shape
        assert len(da.x) == grid.ncols
        assert len(da.y) == grid.nrows
        assert da.rio.crs is not None
        assert str(da.rio.crs) == 'EPSG:32755'
        assert da.rio.nodata == grid.nodata_value
    
    def test_from_xarray(self):
        """Test creating Grid from xarray DataArray."""
        grid_original = create_test_grid()
        da = grid_original.to_xarray()
        grid_back = Grid.from_xarray(da)
        
        assert grid_back.shape == grid_original.shape
        assert np.allclose(grid_back.cellsize, grid_original.cellsize, rtol=1e-5)
        assert np.allclose(grid_back.xmin, grid_original.xmin, rtol=1e-5)
        assert np.allclose(grid_back.ymin, grid_original.ymin, rtol=1e-5)
        assert np.allclose(grid_back.data, grid_original.data)
        assert grid_back.metadata['crs'] == grid_original.metadata['crs']
    
    def test_round_trip_conversion(self):
        """Test that Grid -> xarray -> Grid preserves data."""
        grid_original = create_test_grid(ncols=30, nrows=40)
        da = grid_original.to_xarray()
        grid_back = Grid.from_xarray(da)
        
        # Check data is preserved
        assert np.allclose(grid_back.data, grid_original.data)
        
        # Check spatial properties
        assert grid_back.ncols == grid_original.ncols
        assert grid_back.nrows == grid_original.nrows
        assert np.isclose(grid_back.cellsize, grid_original.cellsize)
        assert np.isclose(grid_back.xmin, grid_original.xmin)
        assert np.isclose(grid_back.ymin, grid_original.ymin)


class TestResampling:
    """Test grid resampling functionality."""
    
    def test_downsample_to_coarser(self):
        """Test downsampling to lower resolution."""
        grid = create_test_grid(ncols=100, nrows=100, cellsize=50)
        grid_resampled = grid.resample(target_cellsize=100, method='average')
        
        # Should have half the dimensions
        assert grid_resampled.ncols == 50
        assert grid_resampled.nrows == 50
        assert np.isclose(grid_resampled.cellsize, 100, rtol=1e-3)
        
        # Bounds should be approximately preserved
        assert np.isclose(grid_resampled.xmin, grid.xmin, rtol=1e-3)
        assert np.isclose(grid_resampled.ymin, grid.ymin, rtol=1e-3)
        assert np.isclose(grid_resampled.xmax, grid.xmax, rtol=1e-2)
        assert np.isclose(grid_resampled.ymax, grid.ymax, rtol=1e-2)
    
    def test_upsample_to_finer(self):
        """Test upsampling to higher resolution."""
        grid = create_test_grid(ncols=50, nrows=50, cellsize=100)
        grid_resampled = grid.resample(target_cellsize=50, method='bilinear')
        
        # Should have double the dimensions
        assert grid_resampled.ncols == 100
        assert grid_resampled.nrows == 100
        assert np.isclose(grid_resampled.cellsize, 50, rtol=1e-3)
        
        # Bounds should be approximately preserved
        assert np.isclose(grid_resampled.xmin, grid.xmin, rtol=1e-3)
        assert np.isclose(grid_resampled.ymin, grid.ymin, rtol=1e-3)
    
    def test_resample_methods(self):
        """Test different resampling methods."""
        grid = create_test_grid(ncols=50, nrows=50, cellsize=100)
        
        methods = ['nearest', 'bilinear', 'cubic', 'average']
        for method in methods:
            grid_resampled = grid.resample(target_cellsize=200, method=method)
            assert grid_resampled.ncols == 25
            assert grid_resampled.nrows == 25
            assert np.isclose(grid_resampled.cellsize, 200, rtol=1e-3)
    
    def test_resample_preserves_crs(self):
        """Test that resampling preserves CRS."""
        grid = create_test_grid(crs='EPSG:32755')
        grid_resampled = grid.resample(target_cellsize=200, method='bilinear')
        
        assert grid_resampled.metadata['crs'] == 'EPSG:32755'


class TestReprojection:
    """Test grid reprojection functionality."""
    
    def test_reproject_to_different_utm_zone(self):
        """Test reprojecting between UTM zones."""
        grid = create_test_grid(crs='EPSG:32755')  # UTM 55S
        grid_reproj = grid.reproject(target_crs='EPSG:32754', method='bilinear')  # UTM 54S
        
        assert grid_reproj.metadata['crs'] == 'EPSG:32754'
        # Bounds should change due to different projection
        assert grid_reproj.xmin != grid.xmin
    
    def test_reproject_to_geographic(self):
        """Test reprojecting from UTM to geographic coordinates."""
        grid = create_test_grid(crs='EPSG:32755')  # UTM 55S
        grid_reproj = grid.reproject(target_crs='EPSG:4326', method='bilinear')  # WGS84
        
        assert grid_reproj.metadata['crs'] == 'EPSG:4326'
        # Coordinates should now be in degrees (much smaller values)
        assert abs(grid_reproj.xmin) < 180
        assert abs(grid_reproj.ymin) < 90
    
    def test_reproject_requires_crs(self):
        """Test that reprojection fails without source CRS."""
        grid = create_test_grid()
        grid.metadata.pop('crs')  # Remove CRS
        
        with pytest.raises(ValueError, match="must have a CRS"):
            grid.reproject(target_crs='EPSG:4326')
    
    def test_reproject_methods(self):
        """Test different reprojection methods."""
        grid = create_test_grid(crs='EPSG:32755')
        
        methods = ['nearest', 'bilinear', 'cubic']
        for method in methods:
            grid_reproj = grid.reproject(target_crs='EPSG:4326', method=method)
            assert grid_reproj.metadata['crs'] == 'EPSG:4326'


class TestMatchGrid:
    """Test matching grid to reference."""
    
    def test_match_same_crs_different_resolution(self):
        """Test matching grid with different resolution, same CRS."""
        reference = create_test_grid(ncols=50, nrows=50, cellsize=100, crs='EPSG:32755')
        source = create_test_grid(ncols=100, nrows=100, cellsize=50, crs='EPSG:32755')
        
        matched = source.match_grid(reference, method='bilinear')
        
        # Should match reference resolution
        assert np.isclose(matched.cellsize, reference.cellsize, rtol=1e-3)
        assert matched.metadata['crs'] == reference.metadata['crs']
    
    def test_match_different_crs_same_resolution(self):
        """Test matching grid with different CRS, same resolution."""
        reference = create_test_grid(ncols=50, nrows=50, cellsize=100, crs='EPSG:32755')
        source = create_test_grid(ncols=50, nrows=50, cellsize=100, crs='EPSG:32754')
        
        matched = source.match_grid(reference, method='bilinear')
        
        # Should match reference CRS
        assert matched.metadata['crs'] == reference.metadata['crs']
    
    def test_match_different_crs_and_resolution(self):
        """Test matching grid with both different CRS and resolution."""
        reference = create_test_grid(ncols=50, nrows=50, cellsize=100, crs='EPSG:32755')
        source = create_test_grid(ncols=80, nrows=80, cellsize=200, crs='EPSG:32754')
        
        matched = source.match_grid(reference, method='bilinear')
        
        # Should match both CRS and resolution
        assert matched.metadata['crs'] == reference.metadata['crs']
        assert np.isclose(matched.cellsize, reference.cellsize, rtol=1e-3)
    
    def test_match_without_crs_assumes_same(self):
        """Test that matching without CRS assumes same CRS as reference."""
        reference = create_test_grid(ncols=50, nrows=50, cellsize=100, crs='EPSG:32755')
        source = create_test_grid(ncols=100, nrows=100, cellsize=50, crs=None)
        source.metadata.pop('crs')  # Remove CRS
        
        # Should not raise error, assumes same CRS as reference
        matched = source.match_grid(reference, method='bilinear')
        assert matched.metadata['crs'] == reference.metadata['crs']


class TestResamplingMethods:
    """Test various resampling method options."""
    
    def test_invalid_method_raises_error(self):
        """Test that invalid resampling method raises error."""
        grid = create_test_grid()
        
        with pytest.raises(ValueError, match="Unknown resampling method"):
            grid.resample(target_cellsize=200, method='invalid_method')
    
    def test_all_documented_methods(self):
        """Test that all documented methods work."""
        grid = create_test_grid(ncols=50, nrows=50, cellsize=100)
        
        # These should all work without error
        methods = [
            'nearest', 'bilinear', 'cubic', 'cubic_spline',
            'lanczos', 'average', 'mode', 'gauss',
            'max', 'min', 'med', 'q1', 'q3'
        ]
        
        for method in methods:
            grid_resampled = grid.resample(target_cellsize=200, method=method)
            assert grid_resampled.cellsize == 200


class TestImportErrors:
    """Test proper error handling when rioxarray is not available."""
    
    def test_resample_without_rioxarray(self, monkeypatch):
        """Test that resampling fails gracefully without rioxarray."""
        grid = create_test_grid()
        
        # Mock import error
        def mock_import(name, *args, **kwargs):
            if name == 'rioxarray':
                raise ImportError("No module named 'rioxarray'")
            return __builtins__.__import__(name, *args, **kwargs)
        
        monkeypatch.setattr('builtins.__import__', mock_import)
        
        # Should raise helpful error
        with pytest.raises(ImportError, match="rioxarray"):
            grid.resample(target_cellsize=200)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
