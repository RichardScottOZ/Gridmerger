"""
Example: Non-intersecting grids and quality classification.

This example demonstrates:
1. How GridMerge handles grids that don't overlap
2. How to use quality classification (priorities)
3. The impact of both features
"""

import numpy as np
from gridmerge import Grid, GridMerger, GridAdjuster


def create_grid_at_position(xmin, ymin, size=50, base_value=100, grid_id=0):
    """Create a synthetic grid at a specific position."""
    data = np.random.rand(size, size).astype(np.float32) * 20 + base_value
    grid = Grid(data, xmin=xmin, ymin=ymin, cellsize=10, nodata_value=-9999)
    grid.metadata['grid_id'] = grid_id
    grid.metadata['base_value'] = base_value
    return grid


def demonstrate_non_intersecting():
    """Demonstrate non-intersecting grids scenario."""
    print("=" * 70)
    print("DEMONSTRATION: Non-Intersecting Grids")
    print("=" * 70)
    
    # Create grids with different overlap patterns
    print("\nCreating 5 grids:")
    print("  Grid 1: (0, 0) - Reference")
    print("  Grid 2: (400, 0) - Overlaps with Grid 1")
    print("  Grid 3: (200, 400) - Overlaps with Grid 1")
    print("  Grid 4: (2000, 0) - NO overlap with Grid 1!")
    print("  Grid 5: (2000, 500) - NO overlap with Grid 1!")
    
    grids = [
        create_grid_at_position(0, 0, base_value=100, grid_id=1),
        create_grid_at_position(400, 0, base_value=115, grid_id=2),
        create_grid_at_position(200, 400, base_value=95, grid_id=3),
        create_grid_at_position(2000, 0, base_value=150, grid_id=4),  # Far away!
        create_grid_at_position(2000, 500, base_value=145, grid_id=5),  # Far away!
    ]
    
    # Check overlaps with reference
    print("\nChecking overlaps with reference (Grid 1):")
    reference = grids[0]
    for i, grid in enumerate(grids[1:], 2):
        overlap = reference.get_overlap(grid)
        if overlap:
            print(f"  Grid {i}: ✓ HAS overlap")
            
            # Show DC shift
            dc_shift = GridAdjuster.calculate_dc_shift(reference, grid)
            if dc_shift is not None:
                print(f"           DC shift = {dc_shift:.2f}")
        else:
            print(f"  Grid {i}: ✗ NO overlap - will NOT be leveled!")
            dc_shift = GridAdjuster.calculate_dc_shift(reference, grid)
            print(f"           DC shift = {dc_shift} (None)")
    
    # Merge with leveling
    print("\nMerging with automatic leveling...")
    merged = GridMerger.merge_with_auto_leveling(grids, polynomial_degree=1)
    
    print(f"\nResult:")
    print(f"  Merged grid: {merged.nrows}x{merged.ncols}")
    print(f"  Bounds: {merged.bounds}")
    
    valid_data = merged.get_valid_data()
    print(f"  Data range: {valid_data.min():.2f} to {valid_data.max():.2f}")
    print(f"  Mean: {valid_data.mean():.2f}")
    
    # Explain what happened
    print("\n" + "─" * 70)
    print("EXPLANATION:")
    print("─" * 70)
    print("• Grids 2-3: Leveled to Grid 1 (overlaps detected)")
    print("• Grids 4-5: NOT leveled (no overlap with reference)")
    print("• Result: Mixed baseline in final mosaic")
    print("• Grids 4-5 retain their original baselines (~145-150)")
    print("• Grids 1-3 are on common baseline (~100)")
    
    return grids, merged


def demonstrate_chain_leveling():
    """Demonstrate chain leveling for non-intersecting grids."""
    print("\n\n" + "=" * 70)
    print("SOLUTION: Chain Leveling")
    print("=" * 70)
    
    print("\nCreating 4 grids in a chain:")
    print("  Grid 1: (0, 0)")
    print("  Grid 2: (400, 0) - overlaps Grid 1")
    print("  Grid 3: (800, 0) - overlaps Grid 2, NOT Grid 1")
    print("  Grid 4: (1200, 0) - overlaps Grid 3, NOT Grid 1 or 2")
    
    grids = [
        create_grid_at_position(0, 0, base_value=100, grid_id=1),
        create_grid_at_position(400, 0, base_value=112, grid_id=2),
        create_grid_at_position(800, 0, base_value=125, grid_id=3),
        create_grid_at_position(1200, 0, base_value=138, grid_id=4),
    ]
    
    # Show the problem with normal leveling
    print("\nProblem: Normal leveling to Grid 1:")
    for i, grid in enumerate(grids[1:], 2):
        overlap = grids[0].get_overlap(grid)
        if overlap:
            dc_shift = GridAdjuster.calculate_dc_shift(grids[0], grid)
            print(f"  Grid {i}: Can be leveled (DC shift = {dc_shift:.2f})")
        else:
            print(f"  Grid {i}: Cannot be leveled (no overlap with Grid 1)")
    
    # Chain leveling solution
    print("\nSolution: Chain leveling:")
    leveled_grids = [grids[0]]  # Start with reference
    
    for i in range(1, len(grids)):
        # Level to previous grid in chain
        prev_grid = leveled_grids[i-1]
        current_grid = grids[i]
        
        dc_shift = GridAdjuster.calculate_dc_shift(prev_grid, current_grid)
        if dc_shift is not None:
            leveled = GridAdjuster.level_to_reference(
                current_grid, prev_grid,
                use_dc_shift=True,
                polynomial_degree=1
            )
            print(f"  Grid {i+1}: Leveled to Grid {i} (DC shift = {dc_shift:.2f})")
            leveled_grids.append(leveled)
        else:
            print(f"  Grid {i+1}: No overlap with Grid {i}!")
            leveled_grids.append(current_grid)
    
    # Merge the chain-leveled grids
    merged = GridMerger.merge_multiple_grids(
        leveled_grids,
        level_to_first=False,  # Already leveled
        feather=True
    )
    
    print(f"\nResult:")
    print(f"  All grids now on common baseline")
    valid_data = merged.get_valid_data()
    print(f"  Data range: {valid_data.min():.2f} to {valid_data.max():.2f}")
    print(f"  Mean: {valid_data.mean():.2f}")
    
    return leveled_grids, merged


def demonstrate_priorities():
    """Demonstrate quality classification with priorities."""
    print("\n\n" + "=" * 70)
    print("DEMONSTRATION: Quality Classification (Priorities)")
    print("=" * 70)
    
    print("\nCreating 6 grids with different quality levels:")
    
    grids = []
    qualities = []
    
    # High quality grids (recent surveys)
    for i in range(2):
        grid = create_grid_at_position(i * 400, 0, base_value=100, grid_id=i+1)
        grid.metadata['quality'] = 'High (2023 survey)'
        grid.metadata['year'] = 2023
        grids.append(grid)
        qualities.append('High')
    
    # Medium quality grids (2015 survey)
    for i in range(2):
        grid = create_grid_at_position(i * 400, 500, base_value=110, grid_id=i+3)
        grid.metadata['quality'] = 'Medium (2015 survey)'
        grid.metadata['year'] = 2015
        grids.append(grid)
        qualities.append('Medium')
    
    # Low quality grids (legacy 2000 survey)
    for i in range(2):
        grid = create_grid_at_position(i * 400 + 200, 250, base_value=120, grid_id=i+5)
        grid.metadata['quality'] = 'Low (2000 survey)'
        grid.metadata['year'] = 2000
        grids.append(grid)
        qualities.append('Low')
    
    for i, (grid, quality) in enumerate(zip(grids, qualities)):
        print(f"  Grid {i+1}: {quality} quality")
    
    # Assign priorities
    priorities = []
    for grid in grids:
        year = grid.metadata.get('year', 2000)
        if year >= 2020:
            priority = 100
        elif year >= 2010:
            priority = 80
        else:
            priority = 60
        priorities.append(priority)
    
    print("\nPriority assignment:")
    for i, (priority, quality) in enumerate(zip(priorities, qualities)):
        print(f"  Grid {i+1}: priority={priority} ({quality})")
    
    # Merge WITHOUT priorities
    print("\n--- Merge WITHOUT priorities ---")
    merged_no_priority = GridMerger.merge_with_auto_leveling(grids)
    print(f"Result: {merged_no_priority.nrows}x{merged_no_priority.ncols}")
    
    # Merge WITH priorities
    print("\n--- Merge WITH priorities ---")
    merged_with_priority = GridMerger.merge_multiple_grids(
        grids,
        priorities=priorities,
        level_to_first=True,
        use_dc_shift=True,
        polynomial_degree=1,
        feather=True
    )
    print(f"Result: {merged_with_priority.nrows}x{merged_with_priority.ncols}")
    
    print("\n" + "─" * 70)
    print("IMPACT OF PRIORITIES:")
    print("─" * 70)
    print("• High priority grids (100) processed first")
    print("• Ensures best quality data establishes baseline")
    print("• Lower quality grids blended into result")
    print("• All overlaps still use feathering/blending")
    print("• Order matters: high quality → medium → low")
    
    return grids, merged_with_priority


def demonstrate_combined():
    """Demonstrate both non-intersecting grids AND priorities."""
    print("\n\n" + "=" * 70)
    print("COMBINED: Non-Intersecting + Quality Classification")
    print("=" * 70)
    
    print("\nScenario: 8 grids in two regions with mixed quality")
    print("\nRegion A (North): 4 grids, some overlap")
    print("Region B (South): 4 grids, some overlap")
    print("NO overlap between regions!")
    
    grids = []
    priorities = []
    
    # Region A (north) - high quality
    print("\n  Region A (high quality):")
    for i in range(4):
        grid = create_grid_at_position(i * 300, 0, base_value=100, grid_id=i+1)
        grid.metadata['region'] = 'A'
        grid.metadata['quality'] = 'High'
        grids.append(grid)
        priorities.append(100)
        print(f"    Grid {i+1}: (x={i*300}, y=0), priority=100")
    
    # Region B (south) - lower quality, FAR AWAY
    print("\n  Region B (medium quality):")
    for i in range(4):
        grid = create_grid_at_position(i * 300, 2000, base_value=130, grid_id=i+5)
        grid.metadata['region'] = 'B'
        grid.metadata['quality'] = 'Medium'
        grids.append(grid)
        priorities.append(70)
        print(f"    Grid {i+5}: (x={i*300}, y=2000), priority=70")
    
    # Check overlaps
    print("\nOverlap analysis:")
    reference = grids[0]
    region_a_overlaps = 0
    region_b_no_overlaps = 0
    
    for i, grid in enumerate(grids[1:], 2):
        overlap = reference.get_overlap(grid)
        region = grid.metadata['region']
        if overlap:
            region_a_overlaps += 1
            print(f"  Grid {i} (Region {region}): ✓ overlaps with reference")
        else:
            if region == 'B':
                region_b_no_overlaps += 1
            print(f"  Grid {i} (Region {region}): ✗ no overlap")
    
    # Merge with priorities
    print("\nMerging with priorities...")
    merged = GridMerger.merge_multiple_grids(
        grids,
        priorities=priorities,
        level_to_first=True,
        use_dc_shift=True,
        polynomial_degree=1,
        feather=True
    )
    
    print(f"\nResult:")
    print(f"  Merged: {merged.nrows}x{merged.ncols}")
    print(f"  Bounds: {merged.bounds}")
    
    print("\n" + "─" * 70)
    print("OUTCOME:")
    print("─" * 70)
    print(f"• Region A: {region_a_overlaps} grids leveled (overlaps detected)")
    print(f"• Region B: {region_b_no_overlaps} grids NOT leveled (no overlap)")
    print("• Priority 100 (Region A) processed before priority 70 (Region B)")
    print("• BUT: Regions still have different baselines")
    print("• Region A baseline: ~100, Region B baseline: ~130")
    print("\nConclusion: Priorities help organize merge but don't solve")
    print("           the non-intersection problem.")
    
    return grids, merged


def main():
    """Run all demonstrations."""
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Non-Intersecting Grids & Quality Classification".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Demo 1: Non-intersecting grids
    grids1, merged1 = demonstrate_non_intersecting()
    
    # Demo 2: Chain leveling solution
    grids2, merged2 = demonstrate_chain_leveling()
    
    # Demo 3: Quality classification
    grids3, merged3 = demonstrate_priorities()
    
    # Demo 4: Combined scenario
    grids4, merged4 = demonstrate_combined()
    
    # Save examples
    print("\n\n" + "=" * 70)
    print("SAVING EXAMPLE OUTPUTS")
    print("=" * 70)
    
    try:
        merged1.write("/tmp/example_non_intersecting.asc")
        print("✓ Saved: /tmp/example_non_intersecting.asc")
        
        merged2.write("/tmp/example_chain_leveled.asc")
        print("✓ Saved: /tmp/example_chain_leveled.asc")
        
        merged3.write("/tmp/example_with_priorities.asc")
        print("✓ Saved: /tmp/example_with_priorities.asc")
        
        merged4.write("/tmp/example_combined.asc")
        print("✓ Saved: /tmp/example_combined.asc")
    except Exception as e:
        print(f"⚠ Could not save files: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
Key Lessons:

1. NON-INTERSECTING GRIDS:
   • DC shift/leveling requires overlap
   • Non-overlapping grids retain original baseline
   • Use chain leveling or regional references as solutions

2. QUALITY CLASSIFICATION (PRIORITIES):
   • Controls merge order (high priority first)
   • Ensures best data establishes baseline
   • Does NOT override blending in overlaps
   • Useful for organizing heterogeneous datasets

3. COMBINED SCENARIOS:
   • Priorities help but don't solve non-intersection
   • Need multiple strategies for complex datasets
   • Document limitations when regions don't connect

For more details, see NON_INTERSECTING_GRIDS.md
    """)


if __name__ == "__main__":
    main()
