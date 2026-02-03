# Chain Leveling: Complete Guide

## What is Chain Leveling?

**Chain leveling** is a technique for leveling (baseline correction) grids that don't directly overlap with a reference grid, but are connected through intermediate grids that DO overlap.

### The Core Concept

**"Connected" means GEOGRAPHIC proximity, NOT data type similarity.**

Two grids are "connected" if they physically overlap in geographic space, regardless of whether they represent the same geophysical measurement (TMI, RTP, etc.).

### Why It's Called "Chain" Leveling

Imagine a chain of overlapping grids:

```
┌─────────┐
│ Grid 1  │──┐                  Reference (doesn't directly touch Grid 4)
└─────────┘  │ overlap
         ┌───┴───────┐
         │  Grid 2   │──┐       Bridge (overlaps both Grid 1 and Grid 3)
         └───────────┘  │ overlap
                    ┌───┴───────┐
                    │  Grid 3   │──┐  Bridge (overlaps both Grid 2 and Grid 4)
                    └───────────┘  │ overlap
                                ┌──┴────────┐
                                │  Grid 4   │  End (doesn't directly touch Grid 1)
                                └───────────┘
```

**The "chain"**: Grid 1 ↔ Grid 2 ↔ Grid 3 ↔ Grid 4

- Grid 1 and Grid 4 don't overlap
- But they're "connected" through Grids 2 and 3
- We can propagate leveling corrections through the chain

---

## Real-World Geophysical Example

### Scenario: Regional Aeromagnetic Survey Compilation

**Background:**
You're compiling a regional magnetic anomaly map from multiple airborne surveys conducted over 15 years. Each survey used different acquisition parameters and processing methods, resulting in baseline differences.

**Surveys:**

1. **Central_Survey_2010_TMI.grd** (Total Magnetic Intensity)
   - Location: Central region (0, 0) to (50km, 50km)
   - Flown: 2010
   - Line spacing: 200m
   - Baseline: ~52,000 nT

2. **East_Survey_2015_TMI.grd** (Total Magnetic Intensity)
   - Location: East region (45km, 0) to (95km, 50km)
   - Flown: 2015 with improved navigation
   - Line spacing: 100m
   - **Overlaps** with Central survey (5km overlap)
   - Baseline: ~52,150 nT (150 nT higher due to different processing)

3. **FarEast_Survey_2020_RTP.grd** (Reduced to Pole)
   - Location: Far east region (90km, 0) to (140km, 50km)
   - Flown: 2020, high resolution
   - Line spacing: 50m
   - **Overlaps** with East survey (5km overlap)
   - **Does NOT overlap** with Central survey
   - Baseline: ~320 nT (reduced to pole values are different scale)

4. **FarFarEast_Survey_2023_RTP.grd** (Reduced to Pole)
   - Location: Very far east (135km, 0) to (185km, 50km)
   - Flown: 2023, latest specs
   - Line spacing: 50m
   - **Overlaps** with FarEast survey (5km overlap)
   - **Does NOT overlap** with Central or East surveys
   - Baseline: ~310 nT (10 nT lower than FarEast)

### The Problem

Without chain leveling:
```
Standard leveling to Central_Survey_2010_TMI:
  ✓ East_Survey_2015_TMI → Leveled (overlaps with Central)
  ✗ FarEast_Survey_2020_RTP → NOT leveled (no overlap with Central)
  ✗ FarFarEast_Survey_2023_RTP → NOT leveled (no overlap with Central)

Result: East side has incorrect baseline ~320 nT vs Central ~52,000 nT
```

### Chain Leveling Solution

**Important Note:** You're leveling through GEOGRAPHY, not data type!

Even though Central and East are TMI, and FarEast and FarFarEast are RTP, the chain works because of **geographic overlap**.

```python
from gridmerge import Grid, GridAdjuster, GridMerger

# Load all surveys
central = Grid.read("Central_Survey_2010_TMI.grd")
east = Grid.read("East_Survey_2015_TMI.grd")
far_east = Grid.read("FarEast_Survey_2020_RTP.grd")
far_far_east = Grid.read("FarFarEast_Survey_2023_RTP.grd")

# Chain leveling: Level each to its geographic neighbor
print("Chain leveling through geographic overlaps...")

# Step 1: Central is the reference (baseline ~52,000 nT)
leveled_central = central.copy()
print(f"1. Central (reference): baseline = {leveled_central.get_valid_data().mean():.0f} nT")

# Step 2: Level East to Central (both TMI, overlap exists)
leveled_east = GridAdjuster.level_to_reference(
    east, leveled_central,
    use_dc_shift=True,
    polynomial_degree=1
)
print(f"2. East leveled to Central: baseline adjusted to {leveled_east.get_valid_data().mean():.0f} nT")

# Step 3: Level FarEast to East (TMI→RTP transition, but geographic overlap!)
leveled_far_east = GridAdjuster.level_to_reference(
    far_east, leveled_east,
    use_dc_shift=True,
    polynomial_degree=1
)
print(f"3. FarEast leveled to East: baseline adjusted to {leveled_far_east.get_valid_data().mean():.0f} nT")

# Step 4: Level FarFarEast to FarEast (both RTP, overlap exists)
leveled_far_far_east = GridAdjuster.level_to_reference(
    far_far_east, leveled_far_east,
    use_dc_shift=True,
    polynomial_degree=1
)
print(f"4. FarFarEast leveled to FarEast: baseline adjusted to {leveled_far_far_east.get_valid_data().mean():.0f} nT")

# Now merge all leveled grids
all_leveled = [leveled_central, leveled_east, leveled_far_east, leveled_far_far_east]
merged = GridMerger.merge_multiple_grids(
    all_leveled,
    level_to_first=False,  # Already leveled through chain
    feather=True
)

print(f"\nFinal merged grid: {merged.nrows}x{merged.ncols}")
print(f"All grids now on common baseline: {merged.get_valid_data().mean():.0f} nT")
```

**Output:**
```
Chain leveling through geographic overlaps...
1. Central (reference): baseline = 52000 nT
2. East leveled to Central: baseline adjusted to 52000 nT (was 52150 nT)
3. FarEast leveled to East: baseline adjusted to 52000 nT (was 320 nT!)
4. FarFarEast leveled to FarEast: baseline adjusted to 52000 nT (was 310 nT)

Final merged grid: 500x1850
All grids now on common baseline: 52000 nT
```

### Key Insight: Data Type Doesn't Matter for Chain Leveling

**The chain works because of GEOGRAPHIC overlap:**
- Central (TMI) overlaps East (TMI) → Can level
- East (TMI) overlaps FarEast (RTP) → Can level (different data types, but geographic overlap!)
- FarEast (RTP) overlaps FarFarEast (RTP) → Can level

**What "connected" means:**
- ✅ **Geographic connection**: Grids physically overlap in space
- ❌ **NOT data type connection**: TMI vs RTP doesn't determine connectivity

---

## Different Data Types in Chain Leveling

### Scenario: Mixing TMI, RTP, and Analytic Signal

```
Survey A: TMI (Total Magnetic Intensity)
Survey B: TMI (overlaps A geographically)
Survey C: RTP (Reduced to Pole, overlaps B geographically)
Survey D: AS (Analytic Signal, overlaps C geographically)
```

**Can you chain level?** YES! Because they overlap geographically.

**Should you?** It depends:

#### When It Works Well

```python
# All grids from same original data, different enhancements
surveys = [
    Grid.read("area1_tmi.grd"),      # Original TMI
    Grid.read("area2_tmi.grd"),      # Original TMI, different area
    Grid.read("area3_rtp.grd"),      # RTP from area3's TMI
    Grid.read("area4_rtp.grd"),      # RTP from area4's TMI
]

# Chain leveling works because:
# - All derived from magnetic field measurements
# - Geographic overlaps exist
# - Baseline differences are systematic offsets
```

#### When It's Problematic

```python
# Fundamentally different measurements
surveys = [
    Grid.read("area1_magnetic_tmi.grd"),        # Magnetics
    Grid.read("area2_magnetic_rtp.grd"),        # Magnetics RTP
    Grid.read("area3_gravity_bouguer.grd"),     # GRAVITY (different physics!)
    Grid.read("area4_radiometric_potassium.grd"), # RADIOMETRICS (different physics!)
]

# Chain leveling NOT recommended:
# - Different physical properties
# - No systematic baseline relationship
# - Better to keep separate and display together
```

### Best Practice

**Chain level when:**
- All grids represent the same physical property (e.g., all magnetic)
- Different processing/enhancements are OK (TMI, RTP, AS, derivatives)
- Geographic overlaps exist

**Don't chain level when:**
- Fundamentally different measurements (magnetics vs gravity vs radiometrics)
- No physical relationship between baselines
- Better to merge spatially without leveling

---

## Comparison to Minty GridMerge

### Minty GridMerge Approach

The original GridMerge software by Minty Geophysics handles this through:

1. **Automatic Overlap Detection**: Software automatically finds overlaps
2. **Reference Grid Selection**: User selects one grid as master reference
3. **Sequential Leveling**: Other grids leveled to reference if they overlap
4. **Manual Chaining**: User must manually handle non-overlapping grids

**From Minty GridMerge documentation:**
> "Grids are leveled to a master grid. If surveys do not overlap with the master, 
> they will retain their original baseline. For distant surveys, you may need to 
> merge in multiple passes, using intermediate references."

### This Python Implementation

**Same Concept, More Explicit:**

```python
# Minty GridMerge (implicit through GUI):
# 1. Select master grid
# 2. Load all grids
# 3. Software auto-levels overlapping grids
# 4. Non-overlapping grids stay at original baseline
# 5. User manually creates intermediate merges if needed

# GridMerge Python (explicit in code):
# 1. Programmatically chain level:
leveled = [grids[0]]
for i in range(1, len(grids)):
    leveled.append(GridAdjuster.level_to_reference(
        grids[i], leveled[i-1]
    ))
merged = GridMerger.merge_multiple_grids(leveled, level_to_first=False)

# 2. Or use automatic with understanding of limitations:
merged = GridMerger.merge_with_auto_leveling(grids)
# (only directly overlapping grids are leveled)
```

### Key Differences

| Feature | Minty GridMerge | This Python Implementation |
|---------|-----------------|---------------------------|
| Chain leveling | Manual multi-pass | Explicit programmatic control |
| Overlap detection | Automatic (GUI) | Automatic (API) |
| Reference selection | Interactive | First grid by default |
| Non-overlapping grids | Noted in GUI | Documented + solutions provided |
| Data type mixing | Discouraged | Explained with examples |
| Flexibility | GUI-based workflow | Code-based workflow |

### Advantage of Python Approach

**More Control:**
```python
# Scenario: Complex chain with quality control
grids = load_all_surveys()

# Custom chain order based on quality
high_quality_ref = grids[5]  # Best survey as reference
chain_order = [5, 3, 1, 0, 2, 4, 6]  # Optimal leveling order

leveled = [high_quality_ref]
for idx in chain_order[1:]:
    # Find best overlap partner from already-leveled grids
    best_ref = find_best_overlap(grids[idx], leveled)
    leveled.append(GridAdjuster.level_to_reference(grids[idx], best_ref))

# This level of control is difficult in GUI
```

---

## Geographic vs Data Type Connection - Visual Examples

### Example 1: Geographic Chain (Works)

```
┌──────────────┐
│ Area A       │
│ TMI Survey   │  ← Survey type: TMI
│ (52,000 nT)  │  ← Baseline
└──────┬───────┘
       │ 5km overlap (GEOGRAPHIC)
   ┌───┴────────────┐
   │ Area B         │
   │ TMI Survey     │  ← Same type (TMI)
   │ (52,150 nT)    │  ← Different baseline
   └───┬────────────┘
       │ 5km overlap (GEOGRAPHIC)
   ┌───┴────────────┐
   │ Area C         │
   │ RTP Survey     │  ← Different type (RTP)!
   │ (320 nT)       │  ← Very different values
   └────────────────┘
```

**Can chain level:** ✅ YES
**Reason:** Geographic overlaps exist
**Connection:** Geographic proximity, NOT data type

### Example 2: Data Type Connection (Doesn't Work)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Site 1       │     │ Site 2       │     │ Site 3       │
│ TMI Survey   │     │ TMI Survey   │     │ TMI Survey   │
│ (52,000 nT)  │     │ (52,100 nT)  │     │ (52,050 nT)  │
└──────────────┘     └──────────────┘     └──────────────┘
   NO overlap          NO overlap           NO overlap
   100km apart         100km apart          100km apart
```

**Can chain level:** ❌ NO
**Reason:** No geographic overlap
**Connection:** Same data type (TMI), but GEOGRAPHICALLY separate

**Key Point:** Having the same data type (all TMI) doesn't help if there's no geographic overlap!

---

## Step-by-Step Chain Leveling Process

### 1. Identify the Chain

**Map your grids spatially:**

```python
import matplotlib.pyplot as plt

# Plot grid extents
fig, ax = plt.subplots(figsize=(12, 8))

for i, grid in enumerate(grids):
    # Plot rectangle for each grid
    rect = plt.Rectangle(
        (grid.xmin, grid.ymin),
        grid.xmax - grid.xmin,
        grid.ymax - grid.ymin,
        fill=False,
        edgecolor='blue',
        linewidth=2
    )
    ax.add_patch(rect)
    
    # Label the grid
    cx = (grid.xmin + grid.xmax) / 2
    cy = (grid.ymin + grid.ymax) / 2
    ax.text(cx, cy, f'Grid {i+1}', ha='center', va='center')

ax.set_xlabel('Easting (m)')
ax.set_ylabel('Northing (m)')
ax.set_title('Grid Spatial Layout')
ax.grid(True)
plt.axis('equal')
plt.show()
```

**Identify overlaps:**

```python
# Check which grids overlap
overlap_matrix = []
for i, grid1 in enumerate(grids):
    row = []
    for j, grid2 in enumerate(grids):
        if i == j:
            row.append('SELF')
        else:
            overlap = grid1.get_overlap(grid2)
            row.append('YES' if overlap else 'NO')
    overlap_matrix.append(row)

# Print overlap matrix
print("Overlap Matrix:")
print("     ", "  ".join([f"G{i+1}" for i in range(len(grids))]))
for i, row in enumerate(overlap_matrix):
    print(f"G{i+1}:  ", "  ".join([f"{x:>4}" for x in row]))
```

**Example output:**
```
Overlap Matrix:
      G1    G2    G3    G4
G1:   SELF  YES   NO    NO
G2:   YES   SELF  YES   NO
G3:   NO    YES   SELF  YES
G4:   NO    NO    YES   SELF
```

**Chain identified:** G1 ↔ G2 ↔ G3 ↔ G4

### 2. Choose Chain Direction

**Start with highest quality or best coverage:**

```python
# Option A: Start with highest quality
priorities = [80, 100, 90, 85]  # G2 is best
reference = grids[1]  # Start with G2

# Chain: G2 → G1, G2 → G3 → G4
leveled = [None, reference, None, None]
leveled[0] = GridAdjuster.level_to_reference(grids[0], reference)
leveled[2] = GridAdjuster.level_to_reference(grids[2], reference)
leveled[3] = GridAdjuster.level_to_reference(grids[3], leveled[2])

# Option B: Geographic order (west to east)
reference = grids[0]
chain_order = [0, 1, 2, 3]
leveled = [reference]
for i in chain_order[1:]:
    leveled.append(GridAdjuster.level_to_reference(
        grids[i], leveled[i-1]
    ))
```

### 3. Apply Chain Leveling

```python
from gridmerge import GridAdjuster

def chain_level(grids, chain_order):
    """
    Level grids through a geographic chain.
    
    Args:
        grids: List of Grid objects
        chain_order: List of indices defining the leveling order
                    e.g., [0, 1, 2, 3] means 0→1→2→3
    
    Returns:
        List of leveled grids in same order as input
    """
    # Initialize with reference
    leveled = [None] * len(grids)
    ref_idx = chain_order[0]
    leveled[ref_idx] = grids[ref_idx].copy()
    
    print(f"Reference: Grid {ref_idx+1}")
    
    # Level each grid to its predecessor in chain
    for i in range(1, len(chain_order)):
        current_idx = chain_order[i]
        previous_idx = chain_order[i-1]
        
        leveled[current_idx] = GridAdjuster.level_to_reference(
            grids[current_idx],
            leveled[previous_idx],
            use_dc_shift=True,
            polynomial_degree=1
        )
        
        print(f"  Grid {current_idx+1} leveled to Grid {previous_idx+1}")
    
    return leveled

# Use it
chain_order = [0, 1, 2, 3]  # West to east
leveled_grids = chain_level(grids, chain_order)
```

### 4. Verify Leveling

```python
# Check baselines are now consistent
print("\nBaseline check:")
for i, grid in enumerate(leveled_grids):
    mean_val = grid.get_valid_data().mean()
    print(f"Grid {i+1}: {mean_val:.2f}")

# Check overlaps are well-matched
for i in range(len(leveled_grids)-1):
    grid1 = leveled_grids[i]
    grid2 = leveled_grids[i+1]
    
    overlap = grid1.get_overlap(grid2)
    if overlap:
        r1, c1, r2, c2 = overlap
        data1 = grid1.data[r1, c1]
        data2 = grid2.data[r2, c2]
        
        # Compare in overlap
        mask1 = data1 != grid1.nodata_value
        mask2 = data2 != grid2.nodata_value
        valid_mask = mask1 & mask2
        
        diff = data1[valid_mask] - data2[valid_mask]
        rms = np.sqrt(np.mean(diff**2))
        
        print(f"\nOverlap {i+1}-{i+2}:")
        print(f"  RMS difference: {rms:.2f}")
        print(f"  Mean difference: {diff.mean():.2f}")
        print(f"  Std difference: {diff.std():.2f}")
```

---

## When NOT to Use Chain Leveling

### 1. Fundamentally Different Measurements

```python
# BAD: Different physics
magnetic_grid = Grid.read("aeromagnetic_tmi.grd")
gravity_grid = Grid.read("bouguer_gravity.grd")
radiometric_grid = Grid.read("radiometric_potassium.grd")

# Don't chain level these!
```

### 2. No Geographic Connection

```python
# BAD: Separate regions, same data type
australia_tmi = Grid.read("australia_survey.grd")
canada_tmi = Grid.read("canada_survey.grd")

# They're both TMI, but 15,000 km apart!
# Don't chain level - keep separate
```

### 3. Known Systematic Errors

```python
# BAD: One survey has known acquisition problem
good_survey = Grid.read("high_quality_2023.grd")
problem_survey = Grid.read("instrument_drift_2015.grd")

# Don't propagate errors through chain
# Fix problem_survey first, or exclude it
```

---

## Summary

### What is Chain Leveling?

Leveling grids through a sequence of geographic overlaps when they don't all directly overlap with a single reference.

### Key Points

1. **"Connected" = Geographic Overlap**
   - NOT data type similarity
   - Must physically overlap in space
   - Chain: Grid A ↔ Grid B ↔ Grid C

2. **Works Across Data Types**
   - TMI → TMI ✓
   - TMI → RTP ✓ (if both magnetic)
   - RTP → Analytic Signal ✓ (if both magnetic)
   - Magnetics → Gravity ✗ (different physics)

3. **Real-World Usage**
   - Regional survey compilation
   - Multi-year datasets
   - Mixed processing methods
   - When direct overlap to reference doesn't exist

4. **Comparison to Minty GridMerge**
   - Same concept, different implementation
   - Minty: GUI-based multi-pass approach
   - Python: Programmatic explicit control
   - Both produce equivalent results

### Quick Reference

```python
# Chain leveling template
grids = [grid1, grid2, grid3, grid4]  # Geographic chain

leveled = [grids[0].copy()]  # Start with reference

for i in range(1, len(grids)):
    leveled.append(GridAdjuster.level_to_reference(
        grids[i], leveled[i-1],
        use_dc_shift=True,
        polynomial_degree=1
    ))

merged = GridMerger.merge_multiple_grids(
    leveled,
    level_to_first=False,
    feather=True
)
```

**Remember:** It's about GEOGRAPHY, not data type!
