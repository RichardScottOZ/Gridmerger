"""
Grid data structure and I/O operations.

This module provides the Grid class for representing gridded geophysical data,
along with readers and writers for ER Mapper (.ers) format.
"""

import numpy as np
import os
from typing import Optional, Tuple, Dict, Any
import struct


class Grid:
    """
    Represents a gridded geophysical dataset.
    
    Attributes:
        data (np.ndarray): 2D array of grid values
        nrows (int): Number of rows
        ncols (int): Number of columns
        xmin (float): Minimum X coordinate
        ymin (float): Minimum Y coordinate
        cellsize (float): Cell size (assumes square cells)
        nodata_value (float): Value representing no data/null
        metadata (dict): Additional metadata (projection, datum, etc.)
    """
    
    def __init__(self, data: np.ndarray, xmin: float, ymin: float, 
                 cellsize: float, nodata_value: float = -99999.0,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a Grid object.
        
        Args:
            data: 2D numpy array of grid values
            xmin: Minimum X coordinate (left edge)
            ymin: Minimum Y coordinate (bottom edge)
            cellsize: Size of each cell
            nodata_value: Value representing no data
            metadata: Additional metadata dictionary
        """
        self.data = np.asarray(data, dtype=np.float32)
        self.nrows, self.ncols = self.data.shape
        self.xmin = xmin
        self.ymin = ymin
        self.cellsize = cellsize
        self.nodata_value = nodata_value
        self.metadata = metadata or {}
        
    @property
    def xmax(self) -> float:
        """Maximum X coordinate (right edge)."""
        return self.xmin + self.ncols * self.cellsize
    
    @property
    def ymax(self) -> float:
        """Maximum Y coordinate (top edge)."""
        return self.ymin + self.nrows * self.cellsize
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Grid bounds as (xmin, ymin, xmax, ymax)."""
        return (self.xmin, self.ymin, self.xmax, self.ymax)
    
    @property
    def shape(self) -> Tuple[int, int]:
        """Grid shape as (nrows, ncols)."""
        return (self.nrows, self.ncols)
    
    def get_valid_data(self) -> np.ndarray:
        """
        Get valid (non-nodata) grid values.
        
        Returns:
            1D array of valid grid values
        """
        mask = self.data != self.nodata_value
        return self.data[mask]
    
    def get_valid_mask(self) -> np.ndarray:
        """
        Get boolean mask of valid data.
        
        Returns:
            2D boolean array (True for valid data, False for nodata)
        """
        return self.data != self.nodata_value
    
    def copy(self) -> 'Grid':
        """
        Create a deep copy of the grid.
        
        Returns:
            New Grid object with copied data
        """
        return Grid(
            data=self.data.copy(),
            xmin=self.xmin,
            ymin=self.ymin,
            cellsize=self.cellsize,
            nodata_value=self.nodata_value,
            metadata=self.metadata.copy()
        )
    
    def get_overlap(self, other: 'Grid') -> Optional[Tuple[slice, slice, slice, slice]]:
        """
        Find overlap region with another grid.
        
        Args:
            other: Another Grid object
            
        Returns:
            Tuple of (self_row_slice, self_col_slice, other_row_slice, other_col_slice)
            or None if no overlap
        """
        # Check if grids have compatible cell sizes
        if not np.isclose(self.cellsize, other.cellsize, rtol=1e-5):
            raise ValueError("Grids must have the same cell size for overlap detection")
        
        # Find overlap bounds
        overlap_xmin = max(self.xmin, other.xmin)
        overlap_ymin = max(self.ymin, other.ymin)
        overlap_xmax = min(self.xmax, other.xmax)
        overlap_ymax = min(self.ymax, other.ymax)
        
        # Check if there's actual overlap
        if overlap_xmin >= overlap_xmax or overlap_ymin >= overlap_ymax:
            return None
        
        # Convert to pixel coordinates for self
        self_col_start = int(np.round((overlap_xmin - self.xmin) / self.cellsize))
        self_col_end = int(np.round((overlap_xmax - self.xmin) / self.cellsize))
        self_row_start = int(np.round((overlap_ymin - self.ymin) / self.cellsize))
        self_row_end = int(np.round((overlap_ymax - self.ymin) / self.cellsize))
        
        # Convert to pixel coordinates for other
        other_col_start = int(np.round((overlap_xmin - other.xmin) / other.cellsize))
        other_col_end = int(np.round((overlap_xmax - other.xmin) / other.cellsize))
        other_row_start = int(np.round((overlap_ymin - other.ymin) / other.cellsize))
        other_row_end = int(np.round((overlap_ymax - other.ymin) / other.cellsize))
        
        return (
            slice(self_row_start, self_row_end),
            slice(self_col_start, self_col_end),
            slice(other_row_start, other_row_end),
            slice(other_col_start, other_col_end)
        )
    
    @staticmethod
    def read_ers(filepath: str) -> 'Grid':
        """
        Read an ER Mapper (.ers) format grid.
        
        Args:
            filepath: Path to .ers header file
            
        Returns:
            Grid object
        """
        # Read header file
        header = {}
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    header[key.strip()] = value.strip()
        
        # Parse essential parameters
        nrows = int(header.get('NrOfLines', 0))
        ncols = int(header.get('NrOfCellsPerLine', 0))
        cellsize = float(header.get('CellSize', 1.0))
        
        # Registration coordinates (top-left corner in ER Mapper)
        reg_x = float(header.get('RegistrationCellX', 0))
        reg_y = float(header.get('RegistrationCellY', 0))
        reg_coord_x = float(header.get('RegistrationCoordX', 0))
        reg_coord_y = float(header.get('RegistrationCoordY', 0))
        
        # Calculate xmin, ymin (bottom-left corner)
        xmin = reg_coord_x - reg_x * cellsize
        ymax = reg_coord_y - reg_y * cellsize
        ymin = ymax - nrows * cellsize
        
        # Null value
        nodata_value = float(header.get('NullCellValue', -99999.0))
        
        # Data type
        data_type = header.get('DataType', 'IEEE4ByteReal')
        
        # Binary data file
        data_file = filepath.replace('.ers', '')
        if not os.path.exists(data_file):
            # Try common extensions
            for ext in ['', '.raw', '.bil']:
                if os.path.exists(filepath.replace('.ers', ext)):
                    data_file = filepath.replace('.ers', ext)
                    break
        
        # Read binary data
        if data_type == 'IEEE4ByteReal':
            dtype = np.float32
        elif data_type == 'IEEE8ByteReal':
            dtype = np.float64
        else:
            dtype = np.float32
        
        data = np.fromfile(data_file, dtype=dtype)
        data = data.reshape((nrows, ncols))
        
        # Store metadata
        metadata = {
            'projection': header.get('CoordinateSpace.Projection', 'GEODETIC'),
            'datum': header.get('CoordinateSpace.Datum', 'WGS84'),
            'units': header.get('CoordinateSpace.CoordinateType', 'EN'),
            'header': header
        }
        
        return Grid(data, xmin, ymin, cellsize, nodata_value, metadata)
    
    def write_ers(self, filepath: str):
        """
        Write grid to ER Mapper (.ers) format.
        
        Args:
            filepath: Path for output .ers header file
        """
        # Ensure .ers extension
        if not filepath.endswith('.ers'):
            filepath += '.ers'
        
        # Binary data file (same name without .ers)
        data_file = filepath.replace('.ers', '')
        
        # Write binary data
        self.data.astype(np.float32).tofile(data_file)
        
        # Calculate registration point (use top-left corner, cell 0,0)
        reg_x = 0.0
        reg_y = 0.0
        reg_coord_x = self.xmin
        reg_coord_y = self.ymax
        
        # Write header file
        with open(filepath, 'w') as f:
            f.write("DatasetHeader Begin\n")
            f.write(f"    Version = \"6.0\"\n")
            f.write(f"    Name = \"{os.path.basename(filepath)}\"\n")
            f.write(f"    LastUpdated = {{}}\n")
            f.write("    DatasetHeader End\n")
            f.write("\n")
            f.write("DatasetType = ERStorage\n")
            f.write("DataType = IEEE4ByteReal\n")
            f.write("ByteOrder = LSBFirst\n")
            f.write(f"NrOfLines = {self.nrows}\n")
            f.write(f"NrOfCellsPerLine = {self.ncols}\n")
            f.write(f"NrOfBands = 1\n")
            f.write("\n")
            f.write("CoordinateSpace Begin\n")
            f.write(f"    Datum = \"{self.metadata.get('datum', 'WGS84')}\"\n")
            f.write(f"    Projection = \"{self.metadata.get('projection', 'GEODETIC')}\"\n")
            f.write(f"    CoordinateType = {self.metadata.get('units', 'EN')}\n")
            f.write("CoordinateSpace End\n")
            f.write("\n")
            f.write("RasterInfo Begin\n")
            f.write(f"    CellType = IEEE4ByteReal\n")
            f.write(f"    NullCellValue = {self.nodata_value}\n")
            f.write(f"    CellSize = {self.cellsize}\n")
            f.write(f"    RegistrationCellX = {reg_x}\n")
            f.write(f"    RegistrationCellY = {reg_y}\n")
            f.write(f"    RegistrationCoordX = {reg_coord_x}\n")
            f.write(f"    RegistrationCoordY = {reg_coord_y}\n")
            f.write("RasterInfo End\n")
