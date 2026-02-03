"""
Example: Working with multiple grid formats.

This example demonstrates GridMerge's ability to work with different grid formats
without requiring conversion.
"""

import numpy as np
from gridmerge import Grid, GridMerger


def create_sample_grids():
    """Create sample grids in different formats."""
    print("Creating sample grids in different formats...")
    
    # Grid 1: Magnetic survey data
    mag_data = np.random.rand(50, 50) * 100 + 200
    mag_grid = Grid(mag_data.astype(np.float32), xmin=0, ymin=0, cellsize=10)
    mag_grid.metadata['survey_type'] = 'magnetic'
    
    # Grid 2: Radiometric survey data (overlaps with grid 1)
    rad_data = np.random.rand(50, 50) * 80 + 190
    rad_grid = Grid(rad_data.astype(np.float32), xmin=300, ymin=0, cellsize=10)
    rad_grid.metadata['survey_type'] = 'radiometric'
    
    # Grid 3: Legacy survey data (overlaps with both)
    legacy_data = np.random.rand(40, 60) * 90 + 195
    legacy_grid = Grid(legacy_data.astype(np.float32), xmin=150, ymin=200, cellsize=10)
    legacy_grid.metadata['survey_type'] = 'legacy'
    
    # Save in different formats (fallback if GeoTIFF not available)
    files = []
    
    try:
        print("  Saving magnetic survey as GeoTIFF...")
        mag_grid.write("/tmp/magnetic_survey.tif")
        files.append("/tmp/magnetic_survey.tif")
    except ImportError:
        print("  ⚠ GeoTIFF not available, using ASCII instead...")
        mag_grid.write("/tmp/magnetic_survey.asc")
        files.append("/tmp/magnetic_survey.asc")
    
    print("  Saving radiometric survey as ASCII Grid...")
    rad_grid.write("/tmp/radiometric_survey.asc")
    files.append("/tmp/radiometric_survey.asc")
    
    print("  Saving legacy survey as ER Mapper...")
    legacy_grid.write("/tmp/legacy_survey.ers")
    files.append("/tmp/legacy_survey.ers")
    
    return files


def demonstrate_format_conversion():
    """Demonstrate format conversion."""
    print("\n" + "=" * 60)
    print("Format Conversion Demo")
    print("=" * 60)
    
    # Create a test grid
    data = np.random.rand(30, 30) * 50 + 100
    grid = Grid(data.astype(np.float32), xmin=0, ymin=0, cellsize=5)
    
    print("\n1. Original grid created in memory")
    print(f"   Size: {grid.nrows}x{grid.ncols}")
    
    # Save as ASCII
    print("\n2. Saving as ASCII Grid (.asc)...")
    grid.write("/tmp/demo.asc")
    
    # Read ASCII and save as GeoTIFF (requires rasterio)
    print("3. Reading ASCII and converting to GeoTIFF...")
    grid2 = Grid.read("/tmp/demo.asc")
    try:
        grid2.write("/tmp/demo.tif")
        print("   ✓ Converted to GeoTIFF")
    except ImportError:
        print("   ⚠ GeoTIFF support not available (install rasterio)")
        print("   Falling back to ERS format...")
        grid2.write("/tmp/demo.ers")
    
    # Read back and save as ER Mapper
    print("4. Converting to ER Mapper format...")
    grid3 = Grid.read("/tmp/demo.asc")
    grid3.write("/tmp/demo_converted.ers")
    print("   ✓ Converted to ERS")


def demonstrate_mixed_format_merge():
    """Demonstrate merging grids from different formats."""
    print("\n" + "=" * 60)
    print("Mixed-Format Merge Demo")
    print("=" * 60)
    
    # Create sample grids
    files = create_sample_grids()
    
    # Load grids (different formats)
    print("\nLoading grids...")
    grids = []
    for filepath in files:
        grid = Grid.read(filepath)
        format_type = Grid.detect_format(filepath)
        print(f"  Loaded {filepath}")
        print(f"    Format: {format_type.upper()}")
        print(f"    Size: {grid.nrows}x{grid.ncols}")
        print(f"    Bounds: {grid.bounds}")
        grids.append(grid)
    
    # Merge with automatic leveling
    print("\nMerging grids with automatic leveling...")
    merged = GridMerger.merge_with_auto_leveling(
        grids,
        polynomial_degree=1,
        feather=True
    )
    
    print(f"  Merged grid size: {merged.nrows}x{merged.ncols}")
    print(f"  Merged bounds: {merged.bounds}")
    
    # Save merged result in different formats
    print("\nSaving merged result in multiple formats...")
    
    # Save as ASCII
    merged.write("/tmp/merged_result.asc")
    print("  ✓ Saved as ASCII Grid: /tmp/merged_result.asc")
    
    # Save as ERS
    merged.write("/tmp/merged_result.ers")
    print("  ✓ Saved as ER Mapper: /tmp/merged_result.ers")
    
    # Save as GeoTIFF (if available)
    try:
        merged.write("/tmp/merged_result.tif")
        print("  ✓ Saved as GeoTIFF: /tmp/merged_result.tif")
    except ImportError:
        print("  ⚠ GeoTIFF support not available (install rasterio)")
    
    # Display statistics
    valid_data = merged.get_valid_data()
    print(f"\nMerged grid statistics:")
    print(f"  Valid cells: {len(valid_data)} ({100*len(valid_data)/(merged.nrows*merged.ncols):.1f}%)")
    print(f"  Value range: {valid_data.min():.2f} to {valid_data.max():.2f}")
    print(f"  Mean: {valid_data.mean():.2f}")
    print(f"  Std dev: {valid_data.std():.2f}")


def main():
    """Main example function."""
    print("=" * 60)
    print("GridMerge Multi-Format Support Example")
    print("=" * 60)
    
    # Demonstrate format conversion
    demonstrate_format_conversion()
    
    # Demonstrate mixed-format merging
    demonstrate_mixed_format_merge()
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    print("\nKey takeaways:")
    print("1. GridMerge supports multiple formats: ERS, GeoTIFF, ASCII Grid")
    print("2. Format is auto-detected from file extension")
    print("3. You can merge grids from different formats")
    print("4. Easy conversion between formats")
    print("5. No need to pre-convert all data to the same format!")


if __name__ == "__main__":
    main()
