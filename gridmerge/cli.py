"""
Command-line interface for GridMerge.
"""

import argparse
import sys
import os
from typing import List
from .grid import Grid
from .merge import GridMerger
from .adjust import GridAdjuster


def merge_command(args):
    """Execute grid merge command."""
    # Load input grids
    print(f"Loading {len(args.input)} grid(s)...")
    grids = []
    for filepath in args.input:
        try:
            grid = Grid.read(filepath)  # Auto-detect format
            grids.append(grid)
            print(f"  Loaded: {filepath} ({grid.nrows}x{grid.ncols})")
        except Exception as e:
            print(f"  Error loading {filepath}: {e}", file=sys.stderr)
            return 1
    
    if not grids:
        print("No grids loaded successfully.", file=sys.stderr)
        return 1
    
    # Merge grids
    print("\nMerging grids...")
    try:
        if args.auto:
            # Auto leveling mode
            result = GridMerger.merge_with_auto_leveling(
                grids,
                polynomial_degree=args.polynomial_degree,
                feather=not args.no_feather
            )
        else:
            # Manual control
            result = GridMerger.merge_multiple_grids(
                grids,
                priorities=args.priorities,
                level_to_first=args.level,
                use_dc_shift=args.dc_shift,
                use_scale=args.scale,
                polynomial_degree=args.polynomial_degree if args.polynomial else None,
                feather=not args.no_feather
            )
        
        print(f"Merged grid: {result.nrows}x{result.ncols}")
    except Exception as e:
        print(f"Error during merge: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    # Save output
    print(f"\nSaving to {args.output}...")
    try:
        result.write(args.output)  # Auto-detect format
        print("Done!")
    except Exception as e:
        print(f"Error saving output: {e}", file=sys.stderr)
        return 1
    
    return 0


def level_command(args):
    """Execute grid leveling command."""
    # Load grids
    print(f"Loading reference grid: {args.reference}")
    try:
        reference = Grid.read(args.reference)  # Auto-detect format
        print(f"  Reference: {reference.nrows}x{reference.ncols}")
    except Exception as e:
        print(f"Error loading reference grid: {e}", file=sys.stderr)
        return 1
    
    print(f"Loading grid to adjust: {args.input}")
    try:
        grid = Grid.read(args.input)  # Auto-detect format
        print(f"  Input: {grid.nrows}x{grid.ncols}")
    except Exception as e:
        print(f"Error loading input grid: {e}", file=sys.stderr)
        return 1
    
    # Level grid
    print("\nLeveling grid...")
    try:
        result = GridAdjuster.level_to_reference(
            grid, reference,
            use_dc_shift=args.dc_shift,
            use_scale=args.scale,
            polynomial_degree=args.polynomial_degree if args.polynomial else None
        )
        print("Leveling complete.")
    except Exception as e:
        print(f"Error during leveling: {e}", file=sys.stderr)
        return 1
    
    # Save output
    print(f"\nSaving to {args.output}...")
    try:
        result.write(args.output)  # Auto-detect format
        print("Done!")
    except Exception as e:
        print(f"Error saving output: {e}", file=sys.stderr)
        return 1
    
    return 0


def info_command(args):
    """Display grid information."""
    for filepath in args.input:
        print(f"\nGrid: {filepath}")
        try:
            grid = Grid.read(filepath)  # Auto-detect format
            
            # Detect and display format
            detected_format = Grid.detect_format(filepath)
            print(f"  Format: {detected_format.upper()}")
            
            print(f"  Dimensions: {grid.nrows} rows x {grid.ncols} columns")
            print(f"  Cell size: {grid.cellsize}")
            print(f"  Bounds: ({grid.xmin}, {grid.ymin}) to ({grid.xmax}, {grid.ymax})")
            print(f"  NoData value: {grid.nodata_value}")
            
            valid_data = grid.get_valid_data()
            if len(valid_data) > 0:
                print(f"  Valid cells: {len(valid_data)} ({100*len(valid_data)/(grid.nrows*grid.ncols):.1f}%)")
                print(f"  Value range: {valid_data.min():.6f} to {valid_data.max():.6f}")
                print(f"  Mean: {valid_data.mean():.6f}")
                print(f"  Std dev: {valid_data.std():.6f}")
            else:
                print(f"  No valid data")
            
            if grid.metadata:
                print(f"  Projection: {grid.metadata.get('projection', 'Unknown')}")
                print(f"  Datum: {grid.metadata.get('datum', 'Unknown')}")
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
    
    return 0


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description='GridMerge: Level and merge gridded geophysical data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported Formats:
  - ER Mapper (.ers)
  - GeoTIFF (.tif, .tiff) - requires rasterio or GDAL
  - ASCII Grid (.asc, .grd)
  
  Format is auto-detected from file extension. You can mix different formats!

Examples:
  # Merge grids with automatic leveling (mixed formats)
  gridmerge merge grid1.tif grid2.asc grid3.ers -o merged.tif --auto
  
  # Merge with manual control
  gridmerge merge grid1.ers grid2.ers -o merged.tif --dc-shift --polynomial 1
  
  # Level one grid to another (different formats)
  gridmerge level reference.tif input.asc -o leveled.ers --dc-shift --polynomial 2
  
  # Display grid information
  gridmerge info grid1.tif grid2.asc grid3.ers
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Merge command
    merge_parser = subparsers.add_parser('merge', help='Merge multiple grids')
    merge_parser.add_argument('input', nargs='+', help='Input grid files (any supported format)')
    merge_parser.add_argument('-o', '--output', required=True, help='Output grid file (format auto-detected from extension)')
    merge_parser.add_argument('--auto', action='store_true',
                            help='Use automatic leveling with default settings')
    merge_parser.add_argument('--level', action='store_true', default=True,
                            help='Level all grids to first grid (default: True)')
    merge_parser.add_argument('--no-level', dest='level', action='store_false',
                            help='Do not level grids')
    merge_parser.add_argument('--dc-shift', action='store_true', default=True,
                            help='Apply DC shift correction (default: True)')
    merge_parser.add_argument('--no-dc-shift', dest='dc_shift', action='store_false',
                            help='Do not apply DC shift correction')
    merge_parser.add_argument('--scale', action='store_true', default=False,
                            help='Apply scale correction')
    merge_parser.add_argument('--polynomial', action='store_true', default=False,
                            help='Apply polynomial surface correction')
    merge_parser.add_argument('--polynomial-degree', type=int, default=1,
                            choices=[1, 2, 3], help='Polynomial degree (default: 1)')
    merge_parser.add_argument('--no-feather', action='store_true',
                            help='Disable feathering in overlap regions')
    merge_parser.add_argument('--priorities', type=int, nargs='+',
                            help='Priority values for each grid (higher = more important)')
    merge_parser.set_defaults(func=merge_command)
    
    # Level command
    level_parser = subparsers.add_parser('level', help='Level one grid to a reference')
    level_parser.add_argument('reference', help='Reference grid file (any supported format)')
    level_parser.add_argument('input', help='Input grid file to level (any supported format)')
    level_parser.add_argument('-o', '--output', required=True, help='Output grid file (format auto-detected from extension)')
    level_parser.add_argument('--dc-shift', action='store_true', default=True,
                            help='Apply DC shift correction (default: True)')
    level_parser.add_argument('--no-dc-shift', dest='dc_shift', action='store_false',
                            help='Do not apply DC shift correction')
    level_parser.add_argument('--scale', action='store_true', default=False,
                            help='Apply scale correction')
    level_parser.add_argument('--polynomial', action='store_true', default=False,
                            help='Apply polynomial surface correction')
    level_parser.add_argument('--polynomial-degree', type=int, default=1,
                            choices=[1, 2, 3], help='Polynomial degree (default: 1)')
    level_parser.set_defaults(func=level_command)
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Display grid information')
    info_parser.add_argument('input', nargs='+', help='Input grid file(s) (any supported format)')
    info_parser.set_defaults(func=info_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
