"""
Tests for multi-format grid I/O.
"""

import numpy as np
import pytest
import tempfile
import os
from gridmerge import Grid


def test_ascii_grid_write_read():
    """Test ASCII grid format write and read."""
    # Create test grid
    data = np.random.rand(10, 10) * 100
    grid = Grid(data, xmin=100, ymin=200, cellsize=5, nodata_value=-9999.0)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(suffix='.asc', delete=False) as f:
        filepath = f.name
    
    try:
        grid.write_ascii(filepath)
        
        # Read back
        grid2 = Grid.read_ascii(filepath)
        
        # Verify
        assert grid2.nrows == 10
        assert grid2.ncols == 10
        assert np.isclose(grid2.xmin, 100)
        assert np.isclose(grid2.ymin, 200)
        assert np.isclose(grid2.cellsize, 5)
        assert np.allclose(grid2.data, data, rtol=1e-5)
    finally:
        os.unlink(filepath)


def test_format_detection():
    """Test format detection from file extension."""
    assert Grid.detect_format('test.ers') == 'ers'
    assert Grid.detect_format('test.tif') == 'geotiff'
    assert Grid.detect_format('test.tiff') == 'geotiff'
    assert Grid.detect_format('test.asc') == 'ascii'
    assert Grid.detect_format('test.grd') == 'ascii'


def test_generic_read_write_ascii():
    """Test generic read/write with ASCII format."""
    data = np.full((5, 5), 42.0, dtype=np.float32)
    grid = Grid(data, xmin=0, ymin=0, cellsize=1, nodata_value=-9999.0)
    
    with tempfile.NamedTemporaryFile(suffix='.asc', delete=False) as f:
        filepath = f.name
    
    try:
        # Use generic write (auto-detect format)
        grid.write(filepath)
        
        # Use generic read (auto-detect format)
        grid2 = Grid.read(filepath)
        
        assert grid2.nrows == 5
        assert grid2.ncols == 5
        assert np.allclose(grid2.data, 42.0)
    finally:
        os.unlink(filepath)


def test_generic_read_write_ers():
    """Test generic read/write with ERS format."""
    data = np.full((5, 5), 123.0, dtype=np.float32)
    grid = Grid(data, xmin=10, ymin=20, cellsize=2, nodata_value=-99999.0)
    
    with tempfile.NamedTemporaryFile(suffix='.ers', delete=False) as f:
        filepath = f.name
    
    try:
        # Use generic write (auto-detect format)
        grid.write(filepath)
        
        # Use generic read (auto-detect format)
        grid2 = Grid.read(filepath)
        
        assert grid2.nrows == 5
        assert grid2.ncols == 5
        assert np.allclose(grid2.data, 123.0)
    finally:
        # Clean up both .ers and data file
        if os.path.exists(filepath):
            os.unlink(filepath)
        data_file = filepath.replace('.ers', '')
        if os.path.exists(data_file):
            os.unlink(data_file)


def test_explicit_format_read_write():
    """Test reading/writing with explicit format specification."""
    data = np.ones((8, 8)) * 99.0
    grid = Grid(data.astype(np.float32), xmin=0, ymin=0, cellsize=10)
    
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False) as f:
        filepath = f.name
    
    try:
        # Write with explicit format
        grid.write(filepath, format='ascii')
        
        # Read with explicit format
        grid2 = Grid.read(filepath, format='ascii')
        
        assert np.allclose(grid2.data, 99.0)
    finally:
        os.unlink(filepath)


def test_mixed_format_merge():
    """Test merging grids from different formats."""
    # Create two grids
    data1 = np.full((10, 10), 100.0, dtype=np.float32)
    data2 = np.full((10, 10), 100.0, dtype=np.float32)
    
    grid1 = Grid(data1, xmin=0, ymin=0, cellsize=1)
    grid2 = Grid(data2, xmin=5, ymin=0, cellsize=1)
    
    # Write in different formats
    with tempfile.NamedTemporaryFile(suffix='.ers', delete=False) as f1:
        file1 = f1.name
    with tempfile.NamedTemporaryFile(suffix='.asc', delete=False) as f2:
        file2 = f2.name
    
    try:
        grid1.write(file1)
        grid2.write(file2)
        
        # Read back in different formats
        loaded1 = Grid.read(file1)
        loaded2 = Grid.read(file2)
        
        # Verify they loaded correctly
        assert loaded1.nrows == 10
        assert loaded2.nrows == 10
        assert np.allclose(loaded1.data, 100.0)
        assert np.allclose(loaded2.data, 100.0)
        
    finally:
        # Clean up
        for f in [file1, file2]:
            if os.path.exists(f):
                os.unlink(f)
        # Clean up ERS data file
        data_file = file1.replace('.ers', '')
        if os.path.exists(data_file):
            os.unlink(data_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
