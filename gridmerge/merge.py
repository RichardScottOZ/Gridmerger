"""
Grid merging functionality.

This module provides algorithms for merging multiple grids with:
- Priority-based merging
- Feathering/blending in overlap regions
- Multi-grid merge support
"""

import numpy as np
from typing import List, Optional, Tuple
from .grid import Grid
from .adjust import GridAdjuster


class GridMerger:
    """
    Provides algorithms for merging multiple grids.
    """
    
    @staticmethod
    def create_distance_weight(shape: Tuple[int, int], valid_mask: np.ndarray) -> np.ndarray:
        """
        Create distance-based weight array for feathering.
        
        Uses distance transform to create smooth weights that fade toward edges.
        
        Args:
            shape: Shape of the grid (nrows, ncols)
            valid_mask: Boolean mask of valid data
            
        Returns:
            Weight array (0 to 1)
        """
        from scipy import ndimage
        
        # Calculate distance from invalid cells
        distance = ndimage.distance_transform_edt(valid_mask)
        
        # Normalize to 0-1 range
        if distance.max() > 0:
            weights = distance / distance.max()
        else:
            weights = valid_mask.astype(float)
        
        return weights
    
    @staticmethod
    def merge_two_grids(grid1: Grid, grid2: Grid, priority: str = 'first',
                       feather: bool = True, feather_distance: Optional[float] = None) -> Grid:
        """
        Merge two grids.
        
        Args:
            grid1: First grid
            grid2: Second grid
            priority: Priority mode ('first', 'second', 'blend')
            feather: Whether to apply feathering in overlap regions
            feather_distance: Distance for feathering (in cells), None for auto
            
        Returns:
            Merged grid
        """
        # Determine output grid bounds
        xmin = min(grid1.xmin, grid2.xmin)
        ymin = min(grid1.ymin, grid2.ymin)
        xmax = max(grid1.xmax, grid2.xmax)
        ymax = max(grid1.ymax, grid2.ymax)
        
        # Use first grid's cell size (assume they match)
        cellsize = grid1.cellsize
        
        # Calculate output grid dimensions
        ncols = int(np.round((xmax - xmin) / cellsize))
        nrows = int(np.round((ymax - ymin) / cellsize))
        
        # Initialize output grid
        output_data = np.full((nrows, ncols), grid1.nodata_value, dtype=np.float32)
        
        # Create weight arrays if feathering
        if feather:
            weight1 = np.zeros((nrows, ncols), dtype=np.float32)
            weight2 = np.zeros((nrows, ncols), dtype=np.float32)
        
        # Place grid1 data
        col1_start = int(np.round((grid1.xmin - xmin) / cellsize))
        row1_start = int(np.round((grid1.ymin - ymin) / cellsize))
        col1_end = col1_start + grid1.ncols
        row1_end = row1_start + grid1.nrows
        
        valid1 = grid1.data != grid1.nodata_value
        output_data[row1_start:row1_end, col1_start:col1_end][valid1] = grid1.data[valid1]
        
        if feather:
            from scipy import ndimage
            distance1 = ndimage.distance_transform_edt(valid1)
            if distance1.max() > 0:
                w1 = distance1 / distance1.max()
            else:
                w1 = valid1.astype(float)
            weight1[row1_start:row1_end, col1_start:col1_end] = w1
        
        # Place grid2 data
        col2_start = int(np.round((grid2.xmin - xmin) / cellsize))
        row2_start = int(np.round((grid2.ymin - ymin) / cellsize))
        col2_end = col2_start + grid2.ncols
        row2_end = row2_start + grid2.nrows
        
        valid2 = grid2.data != grid2.nodata_value
        
        # Determine how to handle overlap
        if priority == 'second':
            # Grid2 overwrites grid1
            output_data[row2_start:row2_end, col2_start:col2_end][valid2] = grid2.data[valid2]
        elif priority == 'first':
            # Grid1 has priority, only fill where grid1 has no data
            overlap_slice = (slice(row2_start, row2_end), slice(col2_start, col2_end))
            no_data_in_grid1 = output_data[overlap_slice] == grid1.nodata_value
            mask = valid2 & no_data_in_grid1
            output_data[row2_start:row2_end, col2_start:col2_end][mask] = grid2.data[mask]
        elif priority == 'blend' and feather:
            # Blend using feathering
            from scipy import ndimage
            distance2 = ndimage.distance_transform_edt(valid2)
            if distance2.max() > 0:
                w2 = distance2 / distance2.max()
            else:
                w2 = valid2.astype(float)
            weight2[row2_start:row2_end, col2_start:col2_end] = w2
            
            # Blend in overlap regions
            total_weight = weight1 + weight2
            overlap_mask = total_weight > 0
            
            # Get grid1 contribution
            grid1_contrib = np.full((nrows, ncols), 0.0, dtype=np.float32)
            grid1_contrib[row1_start:row1_end, col1_start:col1_end][valid1] = grid1.data[valid1]
            
            # Get grid2 contribution
            grid2_contrib = np.full((nrows, ncols), 0.0, dtype=np.float32)
            grid2_contrib[row2_start:row2_end, col2_start:col2_end][valid2] = grid2.data[valid2]
            
            # Weighted blend
            output_data[overlap_mask] = (
                (weight1[overlap_mask] * grid1_contrib[overlap_mask] +
                 weight2[overlap_mask] * grid2_contrib[overlap_mask]) /
                total_weight[overlap_mask]
            )
        else:
            # Default: blend mode without feathering (simple average)
            overlap_slice = (slice(row2_start, row2_end), slice(col2_start, col2_end))
            has_data_in_grid1 = output_data[overlap_slice] != grid1.nodata_value
            mask = valid2 & has_data_in_grid1
            
            if mask.any():
                # Average in overlap
                output_data[row2_start:row2_end, col2_start:col2_end][mask] = (
                    (output_data[row2_start:row2_end, col2_start:col2_end][mask] +
                     grid2.data[mask]) / 2.0
                )
            
            # Fill non-overlapping areas
            mask_no_overlap = valid2 & ~has_data_in_grid1
            output_data[row2_start:row2_end, col2_start:col2_end][mask_no_overlap] = \
                grid2.data[mask_no_overlap]
        
        # Create output Grid
        metadata = grid1.metadata.copy()
        output_grid = Grid(output_data, xmin, ymin, cellsize, grid1.nodata_value, metadata)
        
        return output_grid
    
    @staticmethod
    def merge_multiple_grids(grids: List[Grid], priorities: Optional[List[int]] = None,
                            level_to_first: bool = True,
                            use_dc_shift: bool = True,
                            use_scale: bool = False,
                            polynomial_degree: Optional[int] = None,
                            feather: bool = True) -> Grid:
        """
        Merge multiple grids.
        
        Args:
            grids: List of Grid objects to merge
            priorities: List of priority values (higher = more important), or None for order-based
            level_to_first: Whether to level all grids to the first grid
            use_dc_shift: Whether to use DC shift correction
            use_scale: Whether to use scale correction
            polynomial_degree: Polynomial degree for surface fitting (None to skip)
            feather: Whether to apply feathering
            
        Returns:
            Merged grid
        """
        if not grids:
            raise ValueError("No grids provided for merging")
        
        if len(grids) == 1:
            return grids[0].copy()
        
        # Level grids if requested
        working_grids = []
        reference_grid = grids[0]
        
        for i, grid in enumerate(grids):
            if i == 0:
                working_grids.append(grid)
            elif level_to_first:
                # Level to reference
                leveled = GridAdjuster.level_to_reference(
                    grid, reference_grid,
                    use_dc_shift=use_dc_shift,
                    use_scale=use_scale,
                    polynomial_degree=polynomial_degree
                )
                working_grids.append(leveled)
            else:
                working_grids.append(grid)
        
        # Sort by priority if provided
        if priorities is not None:
            if len(priorities) != len(working_grids):
                raise ValueError("Number of priorities must match number of grids")
            # Sort in descending priority order
            sorted_pairs = sorted(zip(priorities, working_grids), reverse=True)
            working_grids = [g for _, g in sorted_pairs]
        
        # Merge grids sequentially
        result = working_grids[0].copy()
        
        for grid in working_grids[1:]:
            result = GridMerger.merge_two_grids(
                result, grid,
                priority='blend',
                feather=feather
            )
        
        return result
    
    @staticmethod
    def merge_with_auto_leveling(grids: List[Grid],
                                 polynomial_degree: int = 1,
                                 feather: bool = True) -> Grid:
        """
        Merge grids with automatic leveling.
        
        This is a convenience method that applies the most common settings:
        - DC shift correction
        - Polynomial leveling
        - Feathering in overlaps
        
        Args:
            grids: List of Grid objects to merge
            polynomial_degree: Polynomial degree for leveling (1=linear, 2=quadratic)
            feather: Whether to apply feathering
            
        Returns:
            Merged grid
        """
        return GridMerger.merge_multiple_grids(
            grids,
            priorities=None,
            level_to_first=True,
            use_dc_shift=True,
            use_scale=False,
            polynomial_degree=polynomial_degree,
            feather=feather
        )
