"""
Utility functions for grid inspection and batch processing.

This module provides helper functions for:
- Inspecting multiple grids to see their properties
- Batch reprojection of grids to a common reference
- Interactive workflows for grid processing
"""

import os
from typing import List, Dict, Optional, Tuple, Any
import warnings

from .grid import Grid


def inspect_grids(grid_files: List[str]) -> List[Dict[str, Any]]:
    """
    Inspect multiple grid files and return their properties.
    
    This function loads metadata from each grid file and returns detailed
    information about resolution, CRS, bounds, and dimensions.
    
    Args:
        grid_files: List of paths to grid files
    
    Returns:
        List of dictionaries containing grid information:
        - filename: Original filename
        - cellsize: Grid resolution
        - crs: Coordinate reference system (if available)
        - bounds: (xmin, ymin, xmax, ymax)
        - shape: (nrows, ncols)
        - size_mb: Approximate file size
    
    Example:
        >>> from gridmerge.utils import inspect_grids
        >>> info = inspect_grids(['survey1.tif', 'survey2.tif'])
        >>> for grid_info in info:
        ...     print(f"{grid_info['filename']}: {grid_info['crs']}")
    """
    grid_info_list = []
    
    print("\n" + "="*80)
    print("GRID INSPECTION REPORT")
    print("="*80)
    
    for i, filepath in enumerate(grid_files):
        print(f"\n[{i}] Loading: {os.path.basename(filepath)}")
        
        try:
            # Load grid
            grid = Grid.read(filepath)
            
            # Get CRS if available
            crs = grid.metadata.get('crs', 'Not specified')
            
            # Calculate approximate size
            size_mb = (grid.data.nbytes / (1024 * 1024))
            
            # Create info dict
            info = {
                'index': i,
                'filename': os.path.basename(filepath),
                'filepath': filepath,
                'cellsize': grid.cellsize,
                'crs': crs,
                'bounds': grid.bounds,
                'shape': grid.shape,
                'size_mb': size_mb,
                'nodata': grid.nodata_value
            }
            
            grid_info_list.append(info)
            
            # Print details
            print(f"    Resolution:  {grid.cellsize:.6f} units")
            print(f"    CRS:         {crs}")
            print(f"    Bounds:      {grid.bounds}")
            print(f"    Dimensions:  {grid.nrows} rows × {grid.ncols} cols")
            print(f"    Size:        {size_mb:.2f} MB")
            print(f"    NoData:      {grid.nodata_value}")
            
        except Exception as e:
            print(f"    ERROR: Could not load grid: {e}")
            # Still add entry with error
            info = {
                'index': i,
                'filename': os.path.basename(filepath),
                'filepath': filepath,
                'error': str(e)
            }
            grid_info_list.append(info)
    
    # Print summary table
    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)
    print(f"{'#':<4} {'Filename':<30} {'Resolution':<15} {'CRS':<20}")
    print("-"*80)
    
    for info in grid_info_list:
        if 'error' in info:
            print(f"{info['index']:<4} {info['filename']:<30} {'ERROR':<15} {'':<20}")
        else:
            crs_short = str(info['crs'])[:18] + '..' if len(str(info['crs'])) > 20 else str(info['crs'])
            print(f"{info['index']:<4} {info['filename']:<30} {info['cellsize']:<15.6f} {crs_short:<20}")
    
    print("="*80 + "\n")
    
    return grid_info_list


def reproject_grids_to_reference(
    grid_files: List[str],
    reference_index: Optional[int] = None,
    reference_grid: Optional[Grid] = None,
    output_dir: Optional[str] = None,
    output_suffix: str = '_reprojected',
    method: str = 'bilinear',
    skip_matching: bool = True
) -> List[str]:
    """
    Reproject multiple grids to match a reference grid's CRS and resolution.
    
    This function takes a list of grid files and reprojects them all to match
    a reference grid's spatial properties (CRS, resolution, extent). Useful for
    preparing heterogeneous datasets for merging.
    
    Args:
        grid_files: List of paths to grid files to reproject
        reference_index: Index of grid in grid_files to use as reference (default: 0)
        reference_grid: Explicit reference Grid object (overrides reference_index)
        output_dir: Directory for output files (default: same as input)
        output_suffix: Suffix to add to output filenames (default: '_reprojected')
        method: Resampling method ('bilinear', 'cubic', 'nearest', etc.)
        skip_matching: If True, grids already matching reference are just copied
    
    Returns:
        List of output file paths (in same order as input)
    
    Raises:
        ImportError: If rioxarray is not installed
        ValueError: If reference_index is invalid
    
    Example:
        >>> from gridmerge.utils import reproject_grids_to_reference
        >>> # Reproject all grids to match the first one
        >>> outputs = reproject_grids_to_reference(
        ...     grid_files=['a.tif', 'b.tif', 'c.tif'],
        ...     reference_index=0,
        ...     output_dir='./aligned/'
        ... )
        >>> print(outputs)
        ['./aligned/a_reprojected.tif', './aligned/b_reprojected.tif', ...]
    """
    # Check for rioxarray
    try:
        import rioxarray  # noqa: F401
    except ImportError:
        raise ImportError(
            "rioxarray is required for batch reprojection. "
            "Install with: pip install rioxarray"
        )
    
    # Validate inputs
    if reference_grid is None and reference_index is None:
        reference_index = 0
        print(f"No reference specified, using first grid (index {reference_index}) as reference")
    
    if reference_grid is None:
        if reference_index < 0 or reference_index >= len(grid_files):
            raise ValueError(
                f"reference_index {reference_index} out of range for {len(grid_files)} grids"
            )
    
    # Create output directory if specified
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    print("\n" + "="*80)
    print("BATCH REPROJECTION TO REFERENCE")
    print("="*80)
    
    # Load or use reference grid
    if reference_grid is None:
        print(f"\nLoading reference grid: {grid_files[reference_index]}")
        reference_grid = Grid.read(grid_files[reference_index])
    else:
        print(f"\nUsing provided reference grid")
    
    ref_crs = reference_grid.metadata.get('crs', 'Not specified')
    print(f"Reference CRS:        {ref_crs}")
    print(f"Reference resolution: {reference_grid.cellsize:.6f}")
    print(f"Reference bounds:     {reference_grid.bounds}")
    
    # Process each grid
    output_files = []
    
    for i, filepath in enumerate(grid_files):
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)
        
        # Determine output path
        if output_dir:
            output_path = os.path.join(output_dir, f"{name}{output_suffix}{ext}")
        else:
            input_dir = os.path.dirname(filepath) or '.'
            output_path = os.path.join(input_dir, f"{name}{output_suffix}{ext}")
        
        print(f"\n[{i+1}/{len(grid_files)}] Processing: {filename}")
        
        try:
            # Load grid
            grid = Grid.read(filepath)
            grid_crs = grid.metadata.get('crs', 'Not specified')
            
            # Check if reprojection is needed
            needs_reproject = True
            
            if skip_matching and grid_crs == ref_crs:
                # Check if resolution matches too
                cellsize_diff = abs(grid.cellsize - reference_grid.cellsize)
                if cellsize_diff < 1e-6:  # Essentially same resolution
                    print(f"    Already matches reference (CRS and resolution)")
                    needs_reproject = False
            
            if needs_reproject:
                print(f"    Current CRS:  {grid_crs}")
                print(f"    Current res:  {grid.cellsize:.6f}")
                print(f"    Reprojecting to match reference...")
                
                # Reproject using match_grid
                reprojected = grid.match_grid(reference_grid, method=method)
                
                print(f"    New CRS:      {reprojected.metadata.get('crs', 'Not specified')}")
                print(f"    New res:      {reprojected.cellsize:.6f}")
                print(f"    Saving to:    {output_path}")
                
                # Save reprojected grid
                reprojected.write(output_path)
            else:
                # Just copy/save the grid as-is
                print(f"    Saving (unchanged) to: {output_path}")
                grid.write(output_path)
            
            output_files.append(output_path)
            
        except Exception as e:
            print(f"    ERROR: {e}")
            warnings.warn(f"Failed to reproject {filename}: {e}")
            output_files.append(None)
    
    print("\n" + "="*80)
    print("BATCH REPROJECTION COMPLETE")
    print("="*80)
    successful = sum(1 for f in output_files if f is not None)
    print(f"Successfully processed: {successful}/{len(grid_files)} grids")
    print(f"Output directory: {output_dir or 'same as input'}")
    print("="*80 + "\n")
    
    return output_files


def interactive_reproject(grid_files: List[str], output_dir: str = './reprojected/') -> None:
    """
    Interactive workflow for inspecting and reprojecting grids.
    
    This function provides an interactive command-line workflow:
    1. Inspects all grids and displays their properties
    2. Prompts user to select reference grid
    3. Reprojects all grids to match reference
    4. Optionally merges the reprojected grids
    
    Args:
        grid_files: List of paths to grid files
        output_dir: Directory for output files
    
    Example:
        >>> from gridmerge.utils import interactive_reproject
        >>> interactive_reproject(['survey1.tif', 'survey2.tif', 'survey3.tif'])
        # Displays grid info and prompts for choices
    """
    print("\n" + "="*80)
    print("INTERACTIVE GRID REPROJECTION WORKFLOW")
    print("="*80)
    
    # Step 1: Inspect grids
    print("\nStep 1: Inspecting grids...")
    grid_info = inspect_grids(grid_files)
    
    # Check for errors
    valid_indices = [info['index'] for info in grid_info if 'error' not in info]
    if not valid_indices:
        print("ERROR: No valid grids found. Exiting.")
        return
    
    # Step 2: Select reference
    print("\nStep 2: Select reference grid")
    print("Enter the index number of the grid to use as reference")
    print(f"Valid indices: {valid_indices}")
    
    while True:
        try:
            user_input = input(f"Reference grid index (default: {valid_indices[0]}): ").strip()
            if not user_input:
                ref_index = valid_indices[0]
            else:
                ref_index = int(user_input)
            
            if ref_index not in valid_indices:
                print(f"Invalid index. Please choose from: {valid_indices}")
                continue
            break
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled by user.")
            return
    
    print(f"\nUsing grid #{ref_index} as reference: {grid_info[ref_index]['filename']}")
    
    # Step 3: Choose resampling method
    print("\nStep 3: Select resampling method")
    methods = ['bilinear', 'cubic', 'nearest', 'average']
    print(f"Available methods: {', '.join(methods)}")
    
    while True:
        method = input("Resampling method (default: bilinear): ").strip().lower()
        if not method:
            method = 'bilinear'
        if method in methods:
            break
        print(f"Invalid method. Please choose from: {', '.join(methods)}")
    
    # Step 4: Reproject
    print(f"\nStep 4: Reprojecting all grids to match reference...")
    print(f"Output directory: {output_dir}")
    
    try:
        output_files = reproject_grids_to_reference(
            grid_files=grid_files,
            reference_index=ref_index,
            output_dir=output_dir,
            method=method
        )
        
        valid_outputs = [f for f in output_files if f is not None]
        
        if not valid_outputs:
            print("\nERROR: No grids were successfully reprojected.")
            return
        
        # Step 5: Ask about merging
        print("\nStep 5: Merge reprojected grids?")
        merge = input("Merge all reprojected grids? (y/n, default: n): ").strip().lower()
        
        if merge == 'y':
            from .merge import GridMerger
            
            print("\nLoading reprojected grids...")
            grids = []
            for filepath in valid_outputs:
                try:
                    grid = Grid.read(filepath)
                    grids.append(grid)
                    print(f"  Loaded: {os.path.basename(filepath)}")
                except Exception as e:
                    print(f"  ERROR loading {os.path.basename(filepath)}: {e}")
            
            if grids:
                print(f"\nMerging {len(grids)} grids with auto-leveling...")
                merged = GridMerger.merge_with_auto_leveling(
                    grids,
                    use_dc_shift=True,
                    polynomial_degree=1
                )
                
                output_path = os.path.join(output_dir, 'merged_output.tif')
                merged.write(output_path)
                print(f"\nMerged grid saved to: {output_path}")
            else:
                print("\nNo grids available for merging.")
        
        print("\n" + "="*80)
        print("WORKFLOW COMPLETE")
        print("="*80)
        print(f"Reprojected grids saved to: {output_dir}")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\nERROR during reprojection: {e}")
        import traceback
        traceback.print_exc()


def prepare_grids_for_merge(
    grid_files: List[str],
    reference_index: int = 0,
    output_dir: str = './prepared/',
    method: str = 'bilinear'
) -> List[str]:
    """
    Convenience function to prepare grids for merging.
    
    This is a simplified wrapper around reproject_grids_to_reference
    specifically for the common use case of preparing grids for merging.
    
    Args:
        grid_files: List of paths to grid files
        reference_index: Index of reference grid (default: 0 = first grid)
        output_dir: Output directory for prepared grids
        method: Resampling method
    
    Returns:
        List of prepared grid file paths
    
    Example:
        >>> from gridmerge import Grid, GridMerger
        >>> from gridmerge.utils import prepare_grids_for_merge
        >>> 
        >>> # Prepare grids
        >>> prepared_files = prepare_grids_for_merge(
        ...     ['a.tif', 'b.tif', 'c.tif'],
        ...     output_dir='./aligned/'
        ... )
        >>> 
        >>> # Load and merge
        >>> grids = [Grid.read(f) for f in prepared_files]
        >>> merged = GridMerger.merge_with_auto_leveling(grids)
        >>> merged.write('final.tif')
    """
    return reproject_grids_to_reference(
        grid_files=grid_files,
        reference_index=reference_index,
        output_dir=output_dir,
        output_suffix='_aligned',
        method=method,
        skip_matching=True
    )
