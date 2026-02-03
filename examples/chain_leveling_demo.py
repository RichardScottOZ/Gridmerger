"""
Example: Chain Leveling with Real-World Geophysical Surveys

This example demonstrates chain leveling using a realistic scenario:
- Multiple aeromagnetic surveys from different years
- Mix of TMI and RTP data
- Geographic overlaps forming a chain
- Comparison to direct leveling
"""

import numpy as np
from gridmerge import Grid, GridAdjuster, GridMerger


def create_realistic_magnetic_survey(xmin, ymin, size, base_value, survey_name, data_type="TMI"):
    """
    Create a synthetic grid simulating an aeromagnetic survey.
    
    Args:
        xmin, ymin: Position in meters
        size: Grid size (cells)
        base_value: Baseline magnetic field value
        survey_name: Name of survey
        data_type: "TMI" or "RTP"
    """
    # Create realistic magnetic anomaly pattern
    x, y = np.meshgrid(np.arange(size), np.arange(size))
    
    # Add some dipole-like anomalies
    data = base_value + np.zeros((size, size))
    
    # Add a few "magnetic sources"
    for _ in range(3):
        cx, cy = np.random.randint(10, size-10, 2)
        amplitude = np.random.uniform(50, 200)
        distance = np.sqrt((x - cx)**2 + (y - cy)**2)
        anomaly = amplitude / (1 + distance/10)
        data += anomaly
    
    # Add regional gradient
    data += 0.05 * x + 0.03 * y
    
    # Add noise
    data += np.random.normal(0, 10, data.shape)
    
    # Create grid
    grid = Grid(
        data.astype(np.float32),
        xmin=xmin,
        ymin=ymin,
        cellsize=100,  # 100m cells
        nodata_value=-9999
    )
    
    # Add metadata
    grid.metadata['survey_name'] = survey_name
    grid.metadata['data_type'] = data_type
    grid.metadata['original_baseline'] = base_value
    
    return grid


def demonstrate_chain_leveling():
    """Demonstrate chain leveling with realistic survey scenario."""
    
    print("=" * 80)
    print("CHAIN LEVELING: Real-World Aeromagnetic Survey Example")
    print("=" * 80)
    
    print("\nScenario: Regional magnetic compilation")
    print("-" * 80)
    print("You have 4 aeromagnetic surveys from different years:")
    print("  • Central area (2010): TMI, baseline ~52,000 nT")
    print("  • East area (2015): TMI, baseline ~52,150 nT")
    print("  • Far East (2020): RTP, baseline ~320 nT (different processing!)")
    print("  • Far Far East (2023): RTP, baseline ~310 nT")
    print("\nProblem: Only Central-East overlap. Far regions don't touch Central.")
    print("Solution: Chain leveling through geographic overlaps")
    
    # Create surveys
    print("\n" + "=" * 80)
    print("STEP 1: Creating Survey Grids")
    print("=" * 80)
    
    surveys = {
        'Central_2010_TMI': create_realistic_magnetic_survey(
            xmin=0, ymin=0, size=50, base_value=52000,
            survey_name="Central Survey 2010", data_type="TMI"
        ),
        'East_2015_TMI': create_realistic_magnetic_survey(
            xmin=4500, ymin=0, size=50, base_value=52150,
            survey_name="East Survey 2015", data_type="TMI"
        ),
        'FarEast_2020_RTP': create_realistic_magnetic_survey(
            xmin=9000, ymin=0, size=50, base_value=320,
            survey_name="Far East Survey 2020", data_type="RTP"
        ),
        'FarFarEast_2023_RTP': create_realistic_magnetic_survey(
            xmin=13500, ymin=0, size=50, base_value=310,
            survey_name="Far Far East Survey 2023", data_type="RTP"
        ),
    }
    
    grids = list(surveys.values())
    names = list(surveys.keys())
    
    for name, grid in surveys.items():
        mean_val = grid.get_valid_data().mean()
        print(f"\n{name}:")
        print(f"  Position: ({grid.xmin}m, {grid.ymin}m) to ({grid.xmax}m, {grid.ymax}m)")
        print(f"  Size: {grid.nrows}x{grid.ncols} (50x50 cells, 100m spacing)")
        print(f"  Coverage: {(grid.xmax-grid.xmin)/1000:.1f}km x {(grid.ymax-grid.ymin)/1000:.1f}km")
        print(f"  Data type: {grid.metadata['data_type']}")
        print(f"  Baseline: {mean_val:.1f} nT")
    
    # Check overlaps
    print("\n" + "=" * 80)
    print("STEP 2: Analyzing Geographic Overlaps")
    print("=" * 80)
    
    print("\nOverlap Analysis (GEOGRAPHIC connection, not data type!):")
    for i in range(len(grids)-1):
        grid1 = grids[i]
        grid2 = grids[i+1]
        name1 = names[i]
        name2 = names[i+1]
        
        overlap = grid1.get_overlap(grid2)
        
        type1 = grid1.metadata['data_type']
        type2 = grid2.metadata['data_type']
        
        if overlap:
            r1, c1, r2, c2 = overlap
            overlap_area = r1.stop - r1.start
            print(f"\n  {name1} ↔ {name2}")
            print(f"    Data types: {type1} ↔ {type2}")
            print(f"    ✓ OVERLAPS geographically")
            print(f"    Overlap: {overlap_area} cells = {overlap_area * 100}m")
            print(f"    → Can use for chain leveling")
        else:
            print(f"\n  {name1} ↔ {name2}")
            print(f"    Data types: {type1} ↔ {type2}")
            print(f"    ✗ NO overlap")
            print(f"    → Cannot level directly")
    
    # Check if Central overlaps with Far East
    print(f"\n  {names[0]} ↔ {names[2]}")
    if grids[0].get_overlap(grids[2]):
        print(f"    ✓ Direct overlap")
    else:
        print(f"    ✗ NO direct overlap")
        print(f"    Distance: {grids[2].xmin - grids[0].xmax}m apart")
        print(f"    → Need chain leveling through {names[1]}")
    
    # Problem demonstration
    print("\n" + "=" * 80)
    print("STEP 3: Problem with Standard Leveling")
    print("=" * 80)
    
    print("\nAttempting standard leveling to Central_2010_TMI:")
    
    reference = grids[0]
    for i, (name, grid) in enumerate(zip(names, grids)):
        if i == 0:
            print(f"  {name}: Reference grid")
        else:
            overlap = reference.get_overlap(grid)
            if overlap:
                dc_shift = GridAdjuster.calculate_dc_shift(reference, grid)
                print(f"  {name}: ✓ Can level (DC shift = {dc_shift:.1f} nT)")
            else:
                print(f"  {name}: ✗ CANNOT level (no overlap with reference)")
                print(f"       → Will retain baseline of {grid.get_valid_data().mean():.1f} nT")
    
    print("\nResult: Far surveys remain at wrong baseline!")
    print("  Central: ~52,000 nT ✓")
    print("  East: ~52,000 nT (leveled) ✓")
    print("  FarEast: ~320 nT (NOT leveled) ✗")
    print("  FarFarEast: ~310 nT (NOT leveled) ✗")
    
    # Chain leveling solution
    print("\n" + "=" * 80)
    print("STEP 4: Chain Leveling Solution")
    print("=" * 80)
    
    print("\nChain leveling through GEOGRAPHIC neighbors:")
    print("  (Note: Data type changes from TMI→RTP, but GEOGRAPHY connects them)")
    
    # Perform chain leveling
    leveled = [grids[0].copy()]
    
    print(f"\n  1. {names[0]}: Reference")
    print(f"     Baseline: {leveled[0].get_valid_data().mean():.1f} nT ({leveled[0].metadata['data_type']})")
    
    for i in range(1, len(grids)):
        prev_name = names[i-1]
        curr_name = names[i]
        
        # Level current to previous (in chain)
        dc_shift = GridAdjuster.calculate_dc_shift(leveled[i-1], grids[i])
        
        leveled_grid = GridAdjuster.level_to_reference(
            grids[i],
            leveled[i-1],
            use_dc_shift=True,
            polynomial_degree=1
        )
        leveled.append(leveled_grid)
        
        new_baseline = leveled_grid.get_valid_data().mean()
        old_baseline = grids[i].get_valid_data().mean()
        
        print(f"\n  {i+1}. {curr_name}: Leveled to {prev_name}")
        print(f"     Data types: {grids[i].metadata['data_type']} leveled to {leveled[i-1].metadata['data_type']}")
        print(f"     DC shift: {dc_shift:.1f} nT")
        print(f"     Baseline: {old_baseline:.1f} nT → {new_baseline:.1f} nT")
    
    # Verify results
    print("\n" + "=" * 80)
    print("STEP 5: Verification")
    print("=" * 80)
    
    print("\nAll grids now on common baseline:")
    for i, (name, grid) in enumerate(zip(names, leveled)):
        baseline = grid.get_valid_data().mean()
        data_type = grid.metadata['data_type']
        print(f"  {name}: {baseline:.1f} nT ({data_type})")
    
    # Check overlap consistency
    print("\nOverlap consistency check:")
    for i in range(len(leveled)-1):
        grid1 = leveled[i]
        grid2 = leveled[i+1]
        
        overlap = grid1.get_overlap(grid2)
        if overlap:
            r1, c1, r2, c2 = overlap
            data1 = grid1.data[r1, c1]
            data2 = grid2.data[r2, c2]
            
            mask1 = data1 != grid1.nodata_value
            mask2 = data2 != grid2.nodata_value
            valid_mask = mask1 & mask2
            
            if np.any(valid_mask):
                diff = data1[valid_mask] - data2[valid_mask]
                rms = np.sqrt(np.mean(diff**2))
                
                print(f"  {names[i]} ↔ {names[i+1]}: RMS diff = {rms:.2f} nT")
    
    # Merge
    print("\n" + "=" * 80)
    print("STEP 6: Merging Chain-Leveled Grids")
    print("=" * 80)
    
    merged = GridMerger.merge_multiple_grids(
        leveled,
        level_to_first=False,  # Already leveled through chain
        feather=True
    )
    
    print(f"\nMerged result:")
    print(f"  Grid size: {merged.nrows}x{merged.ncols}")
    print(f"  Coverage: {(merged.xmax-merged.xmin)/1000:.1f}km x {(merged.ymax-merged.ymin)/1000:.1f}km")
    print(f"  Baseline: {merged.get_valid_data().mean():.1f} nT")
    print(f"  Data range: {merged.get_valid_data().min():.1f} to {merged.get_valid_data().max():.1f} nT")
    
    # Save results
    try:
        merged.write("/tmp/chain_leveled_regional_magnetic.asc")
        print(f"\n✓ Saved: /tmp/chain_leveled_regional_magnetic.asc")
        
        # Also save individual leveled grids
        for name, grid in zip(names, leveled):
            filename = f"/tmp/leveled_{name}.asc"
            grid.write(filename)
        print(f"✓ Saved individual leveled grids to /tmp/")
        
    except Exception as e:
        print(f"\n⚠ Could not save files: {e}")
    
    return leveled, merged


def demonstrate_comparison():
    """Compare with and without chain leveling."""
    
    print("\n\n" + "=" * 80)
    print("COMPARISON: With vs Without Chain Leveling")
    print("=" * 80)
    
    # Create simple chain
    grids = [
        create_realistic_magnetic_survey(0, 0, 30, 52000, "Survey A", "TMI"),
        create_realistic_magnetic_survey(2500, 0, 30, 52150, "Survey B", "TMI"),
        create_realistic_magnetic_survey(5000, 0, 30, 320, "Survey C", "RTP"),
    ]
    
    print("\nScenario: 3 surveys (A↔B↔C)")
    print("  A overlaps B: Yes")
    print("  B overlaps C: Yes")
    print("  A overlaps C: No")
    
    # Without chain leveling
    print("\n--- WITHOUT Chain Leveling ---")
    merged_no_chain = GridMerger.merge_with_auto_leveling(grids)
    print(f"Standard leveling to Survey A:")
    print(f"  A: Reference at {grids[0].get_valid_data().mean():.0f} nT")
    print(f"  B: Leveled to {grids[0].get_valid_data().mean():.0f} nT ✓")
    print(f"  C: NOT leveled, stays at {grids[2].get_valid_data().mean():.0f} nT ✗")
    print(f"Result baseline: {merged_no_chain.get_valid_data().mean():.0f} nT")
    print(f"Problem: Huge baseline mismatch in merged grid!")
    
    # With chain leveling
    print("\n--- WITH Chain Leveling ---")
    leveled = [grids[0].copy()]
    leveled.append(GridAdjuster.level_to_reference(grids[1], leveled[0]))
    leveled.append(GridAdjuster.level_to_reference(grids[2], leveled[1]))
    
    merged_chain = GridMerger.merge_multiple_grids(leveled, level_to_first=False, feather=True)
    
    print(f"Chain leveling A→B→C:")
    print(f"  A: Reference at {leveled[0].get_valid_data().mean():.0f} nT")
    print(f"  B: Leveled to {leveled[1].get_valid_data().mean():.0f} nT ✓")
    print(f"  C: Leveled to {leveled[2].get_valid_data().mean():.0f} nT ✓ (via B!)")
    print(f"Result baseline: {merged_chain.get_valid_data().mean():.0f} nT")
    print(f"Success: All on common baseline!")
    
    return merged_no_chain, merged_chain


def main():
    """Run all demonstrations."""
    
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  Chain Leveling: Real-World Aeromagnetic Survey Example".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Main demonstration
    leveled, merged = demonstrate_chain_leveling()
    
    # Comparison
    merged_no_chain, merged_chain = demonstrate_comparison()
    
    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
Key Points:

1. GEOGRAPHIC CONNECTION:
   • Chain leveling uses GEOGRAPHIC overlaps
   • NOT about matching data types (TMI, RTP, etc.)
   • Grids must physically overlap in space

2. WORKS ACROSS DATA TYPES:
   • TMI → TMI: Works ✓
   • TMI → RTP: Works ✓ (if both magnetic data)
   • RTP → Analytic Signal: Works ✓
   • Magnetics → Gravity: Don't do this ✗

3. REAL-WORLD APPLICATION:
   • Regional survey compilation
   • Multi-year datasets
   • Different processing/enhancements
   • When direct overlap doesn't exist

4. THE CHAIN:
   • Central (TMI) ↔ East (TMI) ↔ FarEast (RTP) ↔ FarFarEast (RTP)
   • Data type changes: TMI→RTP
   • But GEOGRAPHY connects them
   • All leveled to common baseline

For more details, see CHAIN_LEVELING.md
    """)


if __name__ == "__main__":
    main()
