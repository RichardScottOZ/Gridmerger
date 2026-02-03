"""
Grid data structure and I/O operations.

This module provides the Grid class for representing gridded geophysical data,
along with readers and writers for multiple formats:
- ER Mapper (.ers)
- GeoTIFF (.tif, .tiff) - requires rasterio or GDAL
- ASCII Grid (.asc, .grd)
"""

import numpy as np
import os
from typing import Optional, Tuple, Dict, Any
import struct
import warnings


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
    
    @staticmethod
    def read_ascii(filepath: str) -> 'Grid':
        """
        Read an ASCII Grid (.asc, .grd) format grid.
        
        Args:
            filepath: Path to ASCII grid file
            
        Returns:
            Grid object
        """
        header = {}
        header_lines = 0
        
        # Read header
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) == 2:
                    key = parts[0].lower()
                    if key in ['ncols', 'nrows', 'xllcorner', 'yllcorner', 
                              'xllcenter', 'yllcenter', 'cellsize', 'nodata_value']:
                        header[key] = float(parts[1]) if '.' in parts[1] else int(parts[1])
                        header_lines += 1
                    else:
                        break
                else:
                    break
        
        # Parse header
        ncols = int(header.get('ncols', 0))
        nrows = int(header.get('nrows', 0))
        cellsize = float(header.get('cellsize', 1.0))
        nodata_value = float(header.get('nodata_value', -9999.0))
        
        # Determine lower-left corner (can be corner or center)
        if 'xllcorner' in header:
            xmin = float(header['xllcorner'])
            ymin = float(header['yllcorner'])
        elif 'xllcenter' in header:
            xmin = float(header['xllcenter']) - cellsize / 2
            ymin = float(header['yllcenter']) - cellsize / 2
        else:
            xmin = 0.0
            ymin = 0.0
        
        # Read data
        data = np.loadtxt(filepath, skiprows=header_lines, dtype=np.float32)
        
        if data.shape != (nrows, ncols):
            raise ValueError(f"Data shape {data.shape} does not match header ({nrows}, {ncols})")
        
        return Grid(data, xmin, ymin, cellsize, nodata_value)
    
    def write_ascii(self, filepath: str):
        """
        Write grid to ASCII Grid (.asc) format.
        
        Args:
            filepath: Path for output ASCII grid file
        """
        with open(filepath, 'w') as f:
            f.write(f"ncols {self.ncols}\n")
            f.write(f"nrows {self.nrows}\n")
            f.write(f"xllcorner {self.xmin}\n")
            f.write(f"yllcorner {self.ymin}\n")
            f.write(f"cellsize {self.cellsize}\n")
            f.write(f"NODATA_value {self.nodata_value}\n")
            
            # Write data
            np.savetxt(f, self.data, fmt='%.6f')
    
    @staticmethod
    def read_geotiff(filepath: str) -> 'Grid':
        """
        Read a GeoTIFF (.tif, .tiff) format grid.
        
        Requires rasterio or GDAL to be installed.
        
        Args:
            filepath: Path to GeoTIFF file
            
        Returns:
            Grid object
        """
        try:
            import rasterio
            from rasterio.transform import Affine
            
            with rasterio.open(filepath) as src:
                data = src.read(1).astype(np.float32)
                transform = src.transform
                nodata_value = src.nodata if src.nodata is not None else -99999.0
                
                # Extract geotransform parameters
                xmin = transform.c
                ymax = transform.f
                cellsize = transform.a
                
                nrows, ncols = data.shape
                ymin = ymax - nrows * cellsize
                
                # Get projection info
                metadata = {
                    'projection': src.crs.to_string() if src.crs else 'GEODETIC',
                    'datum': 'WGS84',
                    'crs': src.crs
                }
                
                return Grid(data, xmin, ymin, cellsize, nodata_value, metadata)
                
        except ImportError:
            # Try GDAL as fallback
            try:
                from osgeo import gdal
                
                ds = gdal.Open(filepath)
                if ds is None:
                    raise ValueError(f"Could not open {filepath}")
                
                band = ds.GetRasterBand(1)
                data = band.ReadAsArray().astype(np.float32)
                nodata_value = band.GetNoDataValue()
                if nodata_value is None:
                    nodata_value = -99999.0
                
                geotransform = ds.GetGeoTransform()
                xmin = geotransform[0]
                ymax = geotransform[3]
                cellsize = geotransform[1]
                
                nrows, ncols = data.shape
                ymin = ymax - nrows * cellsize
                
                # Get projection
                proj = ds.GetProjection()
                metadata = {
                    'projection': proj if proj else 'GEODETIC',
                    'datum': 'WGS84'
                }
                
                ds = None  # Close dataset
                
                return Grid(data, xmin, ymin, cellsize, nodata_value, metadata)
                
            except ImportError:
                raise ImportError(
                    "GeoTIFF support requires either 'rasterio' or 'gdal' package. "
                    "Install with: pip install rasterio"
                )
    
    def write_geotiff(self, filepath: str):
        """
        Write grid to GeoTIFF (.tif) format.
        
        Requires rasterio or GDAL to be installed.
        
        Args:
            filepath: Path for output GeoTIFF file
        """
        try:
            import rasterio
            from rasterio.transform import Affine
            from rasterio.crs import CRS
            
            # Create transform
            transform = Affine.translation(self.xmin, self.ymax) * Affine.scale(self.cellsize, -self.cellsize)
            
            # Determine CRS
            if 'crs' in self.metadata:
                crs = self.metadata['crs']
            elif 'projection' in self.metadata:
                try:
                    crs = CRS.from_string(self.metadata['projection'])
                except:
                    crs = CRS.from_epsg(4326)  # Default to WGS84
            else:
                crs = CRS.from_epsg(4326)
            
            # Write file
            with rasterio.open(
                filepath,
                'w',
                driver='GTiff',
                height=self.nrows,
                width=self.ncols,
                count=1,
                dtype=self.data.dtype,
                crs=crs,
                transform=transform,
                nodata=self.nodata_value
            ) as dst:
                dst.write(self.data, 1)
                
        except ImportError:
            # Try GDAL as fallback
            try:
                from osgeo import gdal, osr
                
                driver = gdal.GetDriverByName('GTiff')
                ds = driver.Create(filepath, self.ncols, self.nrows, 1, gdal.GDT_Float32)
                
                # Set geotransform
                geotransform = (self.xmin, self.cellsize, 0, self.ymax, 0, -self.cellsize)
                ds.SetGeoTransform(geotransform)
                
                # Set projection
                srs = osr.SpatialReference()
                if 'projection' in self.metadata:
                    srs.ImportFromWkt(self.metadata['projection'])
                else:
                    srs.ImportFromEPSG(4326)
                ds.SetProjection(srs.ExportToWkt())
                
                # Write data
                band = ds.GetRasterBand(1)
                band.WriteArray(self.data)
                band.SetNoDataValue(self.nodata_value)
                
                ds.FlushCache()
                ds = None
                
            except ImportError:
                raise ImportError(
                    "GeoTIFF support requires either 'rasterio' or 'gdal' package. "
                    "Install with: pip install rasterio"
                )
    
    def to_xarray(self, crs: Optional[str] = None):
        """
        Convert Grid to xarray DataArray with rioxarray spatial extensions.
        
        Requires: xarray, rioxarray
        
        Args:
            crs: Coordinate reference system (e.g., 'EPSG:4326', 'EPSG:32755')
                 If None, uses metadata['crs'] if available
        
        Returns:
            xarray.DataArray with spatial metadata
        """
        try:
            import xarray as xr
            import rioxarray  # noqa: F401
        except ImportError:
            raise ImportError(
                "xarray and rioxarray are required for this functionality. "
                "Install with: pip install xarray rioxarray"
            )
        
        # Use provided CRS or metadata CRS
        if crs is None:
            crs = self.metadata.get('crs', None)
        
        # Create coordinate arrays
        x_coords = np.arange(self.xmin + self.cellsize/2, 
                            self.xmax, 
                            self.cellsize)[:self.ncols]
        y_coords = np.arange(self.ymax - self.cellsize/2, 
                            self.ymin, 
                            -self.cellsize)[:self.nrows]
        
        # Create DataArray
        da = xr.DataArray(
            self.data,
            coords={
                'y': y_coords,
                'x': x_coords
            },
            dims=['y', 'x'],
            attrs={
                'nodata': self.nodata_value,
                **self.metadata
            }
        )
        
        # Add spatial reference if CRS is provided
        if crs:
            da = da.rio.write_crs(crs)
            da = da.rio.write_nodata(self.nodata_value)
        
        return da
    
    @staticmethod
    def from_xarray(da, nodata_value: Optional[float] = None, 
                   metadata: Optional[Dict[str, Any]] = None):
        """
        Create Grid from xarray DataArray.
        
        Args:
            da: xarray.DataArray with x, y coordinates
            nodata_value: Override nodata value (uses da.rio.nodata if None)
            metadata: Additional metadata (merged with CRS from da)
        
        Returns:
            Grid object
        """
        try:
            import rioxarray  # noqa: F401
        except ImportError:
            raise ImportError(
                "rioxarray is required for this functionality. "
                "Install with: pip install rioxarray"
            )
        
        # Extract data
        data = da.values
        
        # Extract coordinates
        y = da.y.values
        x = da.x.values
        
        # Calculate cellsize and bounds
        if len(x) < 2 or len(y) < 2:
            raise ValueError(
                "DataArray must have at least 2 pixels in each dimension. "
                "Single-pixel grids are not supported for geophysical data."
            )
        
        cellsize_x = abs(float(x[1] - x[0]))
        cellsize_y = abs(float(y[1] - y[0]))
        cellsize = (cellsize_x + cellsize_y) / 2  # Average if slightly different
        
        xmin = float(x.min() - cellsize/2)
        ymin = float(y.min() - cellsize/2)
        
        # Get nodata value
        if nodata_value is None:
            try:
                nodata_value = float(da.rio.nodata)
            except (AttributeError, TypeError):
                nodata_value = da.attrs.get('nodata', -99999.0)
        
        # Extract CRS and metadata
        grid_metadata = metadata.copy() if metadata else {}
        try:
            crs = da.rio.crs
            if crs:
                grid_metadata['crs'] = str(crs)
        except AttributeError:
            pass
        
        # Merge any existing attributes
        for key, value in da.attrs.items():
            if key not in grid_metadata and key != 'nodata':
                grid_metadata[key] = value
        
        return Grid(
            data=data,
            xmin=xmin,
            ymin=ymin,
            cellsize=cellsize,
            nodata_value=nodata_value,
            metadata=grid_metadata
        )
    
    def resample(self, target_cellsize: float, method: str = 'bilinear') -> 'Grid':
        """
        Resample grid to a different resolution using rioxarray.
        
        Requires: xarray, rioxarray
        
        Args:
            target_cellsize: Target cell size (resolution)
            method: Resampling method ('bilinear', 'cubic', 'nearest', 'average')
        
        Returns:
            New Grid object at target resolution
        """
        try:
            import rioxarray  # noqa: F401
        except ImportError:
            raise ImportError(
                "xarray and rioxarray are required for resampling. "
                "Install with: pip install xarray rioxarray"
            )
        
        # Convert to xarray
        da = self.to_xarray()
        
        # Check if CRS is available for resampling
        if not da.rio.crs:
            warnings.warn(
                "Grid does not have a CRS defined. Assuming EPSG:4326 for resampling. "
                "Set metadata['crs'] for accurate results.",
                UserWarning
            )
        
        # Calculate new dimensions
        new_width = int(np.round((self.xmax - self.xmin) / target_cellsize))
        new_height = int(np.round((self.ymax - self.ymin) / target_cellsize))
        
        # Resample using rioxarray
        da_resampled = da.rio.reproject(
            da.rio.crs if da.rio.crs else 'EPSG:4326',
            shape=(new_height, new_width),
            resampling=self._get_rasterio_resampling(method),
            nodata=self.nodata_value
        )
        
        # Convert back to Grid
        return Grid.from_xarray(da_resampled, nodata_value=self.nodata_value)
    
    def reproject(self, target_crs: str, method: str = 'bilinear') -> 'Grid':
        """
        Reproject grid to a different coordinate reference system using rioxarray.
        
        Requires: xarray, rioxarray
        
        Args:
            target_crs: Target CRS (e.g., 'EPSG:4326', 'EPSG:32755')
            method: Resampling method ('bilinear', 'cubic', 'nearest', 'average')
        
        Returns:
            New Grid object in target CRS
        """
        try:
            import rioxarray  # noqa: F401
        except ImportError:
            raise ImportError(
                "xarray and rioxarray are required for reprojection. "
                "Install with: pip install xarray rioxarray"
            )
        
        # Convert to xarray
        da = self.to_xarray()
        
        if not da.rio.crs:
            raise ValueError(
                "Grid must have a CRS defined for reprojection. "
                "Set metadata['crs'] or use to_xarray(crs='EPSG:XXXX')"
            )
        
        # Reproject using rioxarray
        da_reprojected = da.rio.reproject(
            target_crs,
            resampling=self._get_rasterio_resampling(method),
            nodata=self.nodata_value
        )
        
        # Convert back to Grid
        return Grid.from_xarray(da_reprojected, nodata_value=self.nodata_value)
    
    def match_grid(self, reference: 'Grid', method: str = 'bilinear') -> 'Grid':
        """
        Resample and reproject this grid to match a reference grid's resolution and CRS.
        
        Requires: xarray, rioxarray
        
        Args:
            reference: Reference Grid to match
            method: Resampling method ('bilinear', 'cubic', 'nearest', 'average')
        
        Returns:
            New Grid object matching reference grid's spatial properties
        """
        try:
            import rioxarray  # noqa: F401
        except ImportError:
            raise ImportError(
                "xarray and rioxarray are required for grid matching. "
                "Install with: pip install xarray rioxarray"
            )
        
        # Convert both grids to xarray
        da_source = self.to_xarray()
        da_reference = reference.to_xarray()
        
        # Check if source has CRS
        if not da_source.rio.crs:
            # Assume same CRS as reference if not specified
            if da_reference.rio.crs:
                da_source = da_source.rio.write_crs(da_reference.rio.crs)
        
        # Reproject to match reference
        da_matched = da_source.rio.reproject_match(
            da_reference,
            resampling=self._get_rasterio_resampling(method),
            nodata=self.nodata_value
        )
        
        # Convert back to Grid
        return Grid.from_xarray(da_matched, nodata_value=self.nodata_value)
    
    @staticmethod
    def _get_rasterio_resampling(method: str):
        """
        Convert method string to rasterio Resampling enum.
        
        Args:
            method: Method name string
        
        Returns:
            rasterio.enums.Resampling value
        """
        try:
            from rasterio.enums import Resampling
        except ImportError:
            raise ImportError(
                "rasterio is required for resampling. "
                "Install with: pip install rasterio"
            )
        
        method_map = {
            'nearest': Resampling.nearest,
            'bilinear': Resampling.bilinear,
            'cubic': Resampling.cubic,
            'cubic_spline': Resampling.cubic_spline,
            'lanczos': Resampling.lanczos,
            'average': Resampling.average,
            'mode': Resampling.mode,
            'gauss': Resampling.gauss,
            'max': Resampling.max,
            'min': Resampling.min,
            'med': Resampling.med,
            'q1': Resampling.q1,
            'q3': Resampling.q3,
        }
        
        if method not in method_map:
            raise ValueError(
                f"Unknown resampling method: {method}. "
                f"Available methods: {list(method_map.keys())}"
            )
        
        return method_map[method]
    
    @staticmethod
    def detect_format(filepath: str) -> str:
        """
        Detect grid format from file extension.
        
        Args:
            filepath: Path to grid file
            
        Returns:
            Format string: 'ers', 'geotiff', or 'ascii'
        """
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext == '.ers':
            return 'ers'
        elif ext in ['.tif', '.tiff']:
            return 'geotiff'
        elif ext in ['.asc', '.grd']:
            return 'ascii'
        else:
            # Try to guess from content
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    magic = f.read(4)
                    if magic[:2] == b'II' or magic[:2] == b'MM':
                        return 'geotiff'
            
            # Default to ASCII if text file
            return 'ascii'
    
    @staticmethod
    def read(filepath: str, format: Optional[str] = None) -> 'Grid':
        """
        Read a grid from file, auto-detecting format if not specified.
        
        Args:
            filepath: Path to grid file
            format: Format string ('ers', 'geotiff', 'ascii') or None for auto-detect
            
        Returns:
            Grid object
        """
        if format is None:
            format = Grid.detect_format(filepath)
        
        format = format.lower()
        
        if format == 'ers':
            return Grid.read_ers(filepath)
        elif format == 'geotiff':
            return Grid.read_geotiff(filepath)
        elif format == 'ascii':
            return Grid.read_ascii(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def write(self, filepath: str, format: Optional[str] = None):
        """
        Write grid to file, auto-detecting format if not specified.
        
        Args:
            filepath: Path for output file
            format: Format string ('ers', 'geotiff', 'ascii') or None for auto-detect
        """
        if format is None:
            format = Grid.detect_format(filepath)
        
        format = format.lower()
        
        if format == 'ers':
            self.write_ers(filepath)
        elif format == 'geotiff':
            self.write_geotiff(filepath)
        elif format == 'ascii':
            self.write_ascii(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
