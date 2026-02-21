"""
Grid adjustment algorithms.

This module provides algorithms for adjusting grids including:
- DC shift (baseline correction)
- Scaling adjustment
- Polynomial fitting for tilt and gradient removal
"""

import numpy as np
from typing import Tuple, Optional
from .grid import Grid


class GridAdjuster:
    """
    Provides algorithms for adjusting and leveling grids.
    """
    
    @staticmethod
    def calculate_dc_shift(grid1: Grid, grid2: Grid) -> Optional[float]:
        """
        Calculate DC shift (baseline offset) between two grids in overlap region.
        
        Args:
            grid1: First grid (reference)
            grid2: Second grid to adjust
            
        Returns:
            DC shift value to add to grid2, or None if no valid overlap
        """
        overlap = grid1.get_overlap(grid2)
        if overlap is None:
            return None
        
        r1, c1, r2, c2 = overlap
        
        # Get overlap data
        data1 = grid1.data[r1, c1]
        data2 = grid2.data[r2, c2]
        
        # Get valid data (exclude nodata values)
        mask1 = data1 != grid1.nodata_value
        mask2 = data2 != grid2.nodata_value
        valid_mask = mask1 & mask2
        
        if not np.any(valid_mask):
            return None
        
        valid1 = data1[valid_mask]
        valid2 = data2[valid_mask]
        
        # Calculate mean difference
        dc_shift = np.mean(valid1 - valid2)
        
        return dc_shift
    
    @staticmethod
    def calculate_scale_factor(grid1: Grid, grid2: Grid) -> Optional[float]:
        """
        Calculate scale factor between two grids in overlap region.
        
        Args:
            grid1: First grid (reference)
            grid2: Second grid to scale
            
        Returns:
            Scale factor to multiply grid2 by, or None if no valid overlap
        """
        overlap = grid1.get_overlap(grid2)
        if overlap is None:
            return None
        
        r1, c1, r2, c2 = overlap
        
        # Get overlap data
        data1 = grid1.data[r1, c1]
        data2 = grid2.data[r2, c2]
        
        # Get valid data
        mask1 = data1 != grid1.nodata_value
        mask2 = data2 != grid2.nodata_value
        valid_mask = mask1 & mask2
        
        if not np.any(valid_mask):
            return None
        
        valid1 = data1[valid_mask]
        valid2 = data2[valid_mask]
        
        # Calculate scale factor using standard deviations
        std1 = np.std(valid1)
        std2 = np.std(valid2)
        
        if std2 == 0:
            return None
        
        scale_factor = std1 / std2
        
        return scale_factor
    
    @staticmethod
    def apply_dc_shift(grid: Grid, shift: float) -> Grid:
        """
        Apply DC shift to a grid.
        
        Args:
            grid: Input grid
            shift: DC shift value to add
            
        Returns:
            New grid with DC shift applied
        """
        result = grid.copy()
        valid_mask = result.data != result.nodata_value
        result.data[valid_mask] += shift
        return result
    
    @staticmethod
    def apply_scale(grid: Grid, scale: float) -> Grid:
        """
        Apply scale factor to a grid.
        
        Args:
            grid: Input grid
            scale: Scale factor to multiply
            
        Returns:
            New grid with scaling applied
        """
        result = grid.copy()
        valid_mask = result.data != result.nodata_value
        result.data[valid_mask] *= scale
        return result
    
    @staticmethod
    def fit_polynomial_1d(x: np.ndarray, y: np.ndarray, degree: int = 1) -> np.ndarray:
        """
        Fit 1D polynomial to data.
        
        Args:
            x: X coordinates
            y: Y values
            degree: Polynomial degree
            
        Returns:
            Polynomial coefficients
        """
        coeffs = np.polyfit(x, y, degree)
        return coeffs
    
    @staticmethod
    def fit_polynomial_2d(x: np.ndarray, y: np.ndarray, z: np.ndarray, 
                         degree: int = 1) -> np.ndarray:
        """
        Fit 2D polynomial surface to data.
        
        Args:
            x: X coordinates (1D array)
            y: Y coordinates (1D array)
            z: Z values (1D array)
            degree: Polynomial degree
            
        Returns:
            Polynomial coefficients
        """
        # Build design matrix
        if degree == 1:
            # Linear: z = a + bx + cy
            A = np.column_stack([np.ones_like(x), x, y])
        elif degree == 2:
            # Quadratic: z = a + bx + cy + dx^2 + ey^2 + fxy
            A = np.column_stack([np.ones_like(x), x, y, x**2, y**2, x*y])
        elif degree == 3:
            # Cubic
            A = np.column_stack([np.ones_like(x), x, y, x**2, y**2, x*y,
                                x**3, y**3, x**2*y, x*y**2])
        else:
            raise ValueError(f"Polynomial degree {degree} not supported")
        
        # Least squares fit
        coeffs, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
        
        return coeffs
    
    @staticmethod
    def evaluate_polynomial_2d(x: np.ndarray, y: np.ndarray, 
                               coeffs: np.ndarray, degree: int = 1) -> np.ndarray:
        """
        Evaluate 2D polynomial surface.
        
        Args:
            x: X coordinates (can be 2D array)
            y: Y coordinates (can be 2D array)
            coeffs: Polynomial coefficients from fit_polynomial_2d
            degree: Polynomial degree
            
        Returns:
            Evaluated surface values
        """
        if degree == 1:
            # Linear: z = a + bx + cy
            z = coeffs[0] + coeffs[1]*x + coeffs[2]*y
        elif degree == 2:
            # Quadratic: z = a + bx + cy + dx^2 + ey^2 + fxy
            z = (coeffs[0] + coeffs[1]*x + coeffs[2]*y + 
                 coeffs[3]*x**2 + coeffs[4]*y**2 + coeffs[5]*x*y)
        elif degree == 3:
            # Cubic
            z = (coeffs[0] + coeffs[1]*x + coeffs[2]*y + 
                 coeffs[3]*x**2 + coeffs[4]*y**2 + coeffs[5]*x*y +
                 coeffs[6]*x**3 + coeffs[7]*y**3 + 
                 coeffs[8]*x**2*y + coeffs[9]*x*y**2)
        else:
            raise ValueError(f"Polynomial degree {degree} not supported")
        
        return z
    
    @staticmethod
    def fit_surface_in_overlap(grid1: Grid, grid2: Grid, 
                               degree: int = 1) -> Optional[np.ndarray]:
        """
        Fit polynomial surface to difference in overlap region.
        
        Args:
            grid1: First grid (reference)
            grid2: Second grid to adjust
            degree: Polynomial degree
            
        Returns:
            Polynomial coefficients, or None if no valid overlap
        """
        overlap = grid1.get_overlap(grid2)
        if overlap is None:
            return None
        
        r1, c1, r2, c2 = overlap
        
        # Get overlap data
        data1 = grid1.data[r1, c1]
        data2 = grid2.data[r2, c2]
        
        # Calculate difference
        diff = data1 - data2
        
        # Get valid data
        mask1 = data1 != grid1.nodata_value
        mask2 = data2 != grid2.nodata_value
        valid_mask = mask1 & mask2
        
        if not np.any(valid_mask):
            return None
        
        # Get coordinates for overlap region in grid2's coordinate system
        rows, cols = np.mgrid[r2.start:r2.stop, c2.start:c2.stop]
        
        # Convert to real-world coordinates
        # Row 0 = topmost (ymax), so y decreases with increasing row index
        x = grid2.xmin + cols * grid2.cellsize
        y = grid2.ymax - rows * grid2.cellsize
        
        # Flatten and filter
        x_flat = x[valid_mask].flatten()
        y_flat = y[valid_mask].flatten()
        z_flat = diff[valid_mask].flatten()
        
        # Fit polynomial
        coeffs = GridAdjuster.fit_polynomial_2d(x_flat, y_flat, z_flat, degree)
        
        return coeffs
    
    @staticmethod
    def apply_polynomial_correction(grid: Grid, coeffs: np.ndarray, 
                                   degree: int = 1) -> Grid:
        """
        Apply polynomial surface correction to grid.
        
        Args:
            grid: Input grid
            coeffs: Polynomial coefficients
            degree: Polynomial degree
            
        Returns:
            New grid with polynomial correction applied
        """
        result = grid.copy()
        
        # Create coordinate arrays
        # Row 0 = topmost (ymax), so y decreases with increasing row index
        rows, cols = np.mgrid[0:grid.nrows, 0:grid.ncols]
        x = grid.xmin + cols * grid.cellsize
        y = grid.ymax - rows * grid.cellsize
        
        # Evaluate polynomial
        correction = GridAdjuster.evaluate_polynomial_2d(x, y, coeffs, degree)
        
        # Apply correction to valid data
        valid_mask = result.data != result.nodata_value
        result.data[valid_mask] += correction[valid_mask]
        
        return result
    
    @staticmethod
    def level_to_reference(grid_to_adjust: Grid, reference_grid: Grid,
                          use_dc_shift: bool = True,
                          use_scale: bool = False,
                          polynomial_degree: Optional[int] = None) -> Grid:
        """
        Level one grid to match a reference grid.
        
        Args:
            grid_to_adjust: Grid to be adjusted
            reference_grid: Reference grid
            use_dc_shift: Whether to apply DC shift correction
            use_scale: Whether to apply scale correction
            polynomial_degree: Polynomial degree for surface fitting (None to skip)
            
        Returns:
            Adjusted grid
        """
        result = grid_to_adjust.copy()
        
        # Apply scale correction first
        if use_scale:
            scale = GridAdjuster.calculate_scale_factor(reference_grid, result)
            if scale is not None:
                result = GridAdjuster.apply_scale(result, scale)
        
        # Apply DC shift
        if use_dc_shift:
            dc_shift = GridAdjuster.calculate_dc_shift(reference_grid, result)
            if dc_shift is not None:
                result = GridAdjuster.apply_dc_shift(result, dc_shift)
        
        # Apply polynomial correction
        if polynomial_degree is not None:
            coeffs = GridAdjuster.fit_surface_in_overlap(
                reference_grid, result, polynomial_degree
            )
            if coeffs is not None:
                result = GridAdjuster.apply_polynomial_correction(
                    result, coeffs, polynomial_degree
                )
        
        return result
