# Non-Intersecting Grids and Quality Classification Guide

## Overview

This guide explains how GridMerge handles scenarios where:
1. **Some grids don't intersect with each other** (non-overlapping grids)
2. **Quality classification** (priorities) affects the merge process

These are common real-world situations when merging survey data from different locations or time periods.

---

## Part 1: Non-Intersecting Grids

### The Scenario

When merging 47 grids, it's common that:
- Some grids overlap with each other
- Some grids are completely separate (non-intersecting)
- Some grids overlap with Grid A but not Grid B

**Example layout:**
```
┌─────────┐                    ┌─────────┐
│ Grid 1  │     ┌─────────┐    │ Grid 4  │
│(0,0)    │     │ Grid 2  │    │(3000,0) │
└─────────┘     │(1000,0) │    └─────────┘
                └─────────┘
      ┌─────────┐
      │ Grid 3  │
      │(500,1000)│
      └─────────┘
```

Grid 1 and Grid 4 don't intersect at all!

### How DC Shift and Leveling Work Without Overlap

#### When Grids DO Intersect

```python
# Grid A and Grid B overlap
dc_shift = GridAdjuster.calculate_dc_shift(grid_a, grid_b)
# Returns: e.g., 15.5 (Grid B is 15.5 units higher than Grid A)

# Apply correction
leveled = GridAdjuster.apply_dc_shift(grid_b, dc_shift)
# Grid B is now leveled to match Grid A's baseline
```

#### When Grids DON'T Intersect

```python
# Grid A and Grid C don't overlap at all
dc_shift = GridAdjuster.calculate_dc_shift(grid_a, grid_c)
# Returns: None (no overlap detected)

# What happens during leveling?
leveled = GridAdjuster.level_to_reference(
    grid_c, grid_a,
    use_dc_shift=True,
    polynomial_degree=1
)
# Result: Grid C is returned UNCHANGED (no corrections applied)
```

**Key Point:** When grids don't intersect:
- DC shift calculation returns `None`
- Scale calculation returns `None`
- Polynomial fitting returns `None`
- Grid is copied but **not modified**
- Grid is still included in the final merge at its original position

### The Leveling Process with Non-Intersecting Grids

```python
from gridmerge import GridMerger, Grid

# 5 grids: some intersect, some don't
grids = [
    Grid.read("grid1.tif"),  # Reference at (0, 0)
    Grid.read("grid2.tif"),  # Overlaps with Grid 1
    Grid.read("grid3.tif"),  # Overlaps with Grid 1
    Grid.read("grid4.tif"),  # NO overlap with Grid 1!
    Grid.read("grid5.tif"),  # NO overlap with Grid 1!
]

# Merge with leveling enabled
merged = GridMerger.merge_with_auto_leveling(grids)
```

**What happens internally:**

```
Step 1: Grid 1 is the reference (unchanged)

Step 2: Level Grid 2 to Grid 1
  - Calculate overlap: Found! (500x500 cells overlap)
  - DC shift: -12.3 (Grid 2 is 12.3 units lower)
  - Apply correction: Grid 2 adjusted by +12.3
  - Result: Leveled Grid 2 ✓

Step 3: Level Grid 3 to Grid 1
  - Calculate overlap: Found! (300x400 cells overlap)
  - DC shift: +5.7 (Grid 3 is 5.7 units higher)
  - Apply correction: Grid 3 adjusted by -5.7
  - Result: Leveled Grid 3 ✓

Step 4: Level Grid 4 to Grid 1
  - Calculate overlap: None! (grids don't intersect)
  - DC shift: None
  - No correction applied
  - Result: Grid 4 UNCHANGED (but still included) ⚠

Step 5: Level Grid 5 to Grid 1
  - Calculate overlap: None! (grids don't intersect)
  - DC shift: None
  - No correction applied
  - Result: Grid 5 UNCHANGED (but still included) ⚠

Step 6: Merge all grids
  - Grid 1, 2, 3 are properly leveled
  - Grid 4, 5 are at their original baselines
  - All grids positioned correctly in space
  - Result: Mosaic with leveled and non-leveled regions
```

### Impact of Non-Intersecting Grids

**What's Good:**
- ✅ Grids are positioned correctly in geographic space
- ✅ No errors or crashes
- ✅ All data is preserved
- ✅ Overlapping grids ARE properly leveled

**What's Problematic:**
- ⚠️ Non-intersecting grids keep their original baseline
- ⚠️ May have visible "steps" or mismatches between regions
- ⚠️ If Grid 4 has a different datum/baseline, it won't be corrected

**Example Issue:**
```
Grid 1 baseline: 100 nT (corrected)
Grid 2 baseline: 112 nT → corrected to 100 nT ✓
Grid 3 baseline: 95 nT → corrected to 100 nT ✓
Grid 4 baseline: 150 nT → stays at 150 nT ⚠ (no overlap to correct)
```

### Solutions for Non-Intersecting Grids

#### Solution 1: Chain Leveling (Recommended)

**What is Chain Leveling?** Leveling grids through a sequence of geographic overlaps when they don't all directly overlap with a single reference.

**Key Point:** "Connected" means GEOGRAPHIC proximity (physical overlap in space), NOT data type similarity (TMI, RTP, etc.).

If you have grids that form a geographic chain (Grid 1↔2↔3↔4):

```python
from gridmerge import GridAdjuster

# Method: Level in sequence through GEOGRAPHIC neighbors
# Grid 2 to Grid 1 (they overlap geographically)
grid2_leveled = GridAdjuster.level_to_reference(grid2, grid1)

# Grid 3 to Grid 2 (they overlap geographically, even if Grid 3 doesn't touch Grid 1)
grid3_leveled = GridAdjuster.level_to_reference(grid3, grid2_leveled)

# Grid 4 to Grid 3 (they overlap geographically, even if Grid 4 doesn't touch Grid 1 or 2)
grid4_leveled = GridAdjuster.level_to_reference(grid4, grid3_leveled)

# Now merge all leveled grids
leveled_grids = [grid1, grid2_leveled, grid3_leveled, grid4_leveled]
merged = GridMerger.merge_multiple_grids(leveled_grids, level_to_first=False)
```

**How this works:**
```
Grid 1 (baseline 100) ← reference
   ↓ geographic overlap
Grid 2 (baseline 112) → leveled to 100
   ↓ geographic overlap
Grid 3 (baseline 95) → leveled to 100 (via Grid 2)
   ↓ geographic overlap
Grid 4 (baseline 150) → leveled to 100 (via Grid 3)
```

**Real-World Example:**
```
Central Survey (TMI, 52,000 nT) ← reference
   ↓ 5km geographic overlap
East Survey (TMI, 52,150 nT) → leveled to 52,000 nT
   ↓ 5km geographic overlap  
FarEast Survey (RTP, 320 nT) → leveled to 52,000 nT (via East, even though data type changed!)
   ↓ 5km geographic overlap
FarFarEast Survey (RTP, 310 nT) → leveled to 52,000 nT (via FarEast)
```

Note: TMI→RTP transition works because they overlap GEOGRAPHICALLY, not because they're the same data type!

**For complete details, see [CHAIN_LEVELING.md](CHAIN_LEVELING.md)**

#### Solution 2: Regional References

Use different reference grids for different regions:

```python
# North region grids
north_grids = [grid1, grid2, grid3]
north_merged = GridMerger.merge_with_auto_leveling(north_grids)

# South region grids
south_grids = [grid4, grid5, grid6]
south_merged = GridMerger.merge_with_auto_leveling(south_grids)

# Then merge regions (may still have baseline difference)
final = GridMerger.merge_two_grids(north_merged, south_merged)
```

#### Solution 3: Use Metadata/Known Offsets

If you know the baseline offsets:

```python
from gridmerge import GridAdjuster

# Apply known corrections before merging
grid4_corrected = GridAdjuster.apply_dc_shift(grid4, -50)  # Reduce by 50
grid5_corrected = GridAdjuster.apply_dc_shift(grid5, -50)

# Then merge all grids
all_grids = [grid1, grid2, grid3, grid4_corrected, grid5_corrected]
merged = GridMerger.merge_with_auto_leveling(all_grids)
```

#### Solution 4: Accept the Limitation

For truly separate surveys with no chain:

```python
# Merge as-is and document the limitation
merged = GridMerger.merge_multiple_grids(
    grids,
    level_to_first=True  # Will level what it can
)

# Add metadata noting the issue
merged.metadata['leveling_note'] = (
    "Grids 1-3 leveled to common baseline. "
    "Grids 4-5 from separate survey, original baseline retained."
)
```

---

## Part 2: Quality Classification (Priorities)

### What Are Priorities?

Priorities (or quality classification) let you specify which grids are more reliable in overlapping regions.

**Common scenarios:**
- Newer surveys vs older surveys
- High-resolution vs low-resolution data
- Ground-truthed vs uncalibrated data
- Different acquisition methods with known quality differences

### How Priorities Work

#### Priority Assignment

```python
from gridmerge import GridMerger

# Assign priority values (higher = better quality)
grids = [grid1, grid2, grid3, grid4, grid5]
priorities = [
    100,  # Grid 1: Excellent (recent, high-res)
    100,  # Grid 2: Excellent
    80,   # Grid 3: Good (older survey)
    60,   # Grid 4: Fair (legacy data)
    60,   # Grid 5: Fair
]

# Merge with priorities
merged = GridMerger.merge_multiple_grids(
    grids,
    priorities=priorities,
    level_to_first=True,
    feather=True
)
```

#### What Priorities Do

**Step 1: Reorder Grids**

Grids are sorted by priority (highest first):
```
Before:  [Grid1(100), Grid2(100), Grid3(80), Grid4(60), Grid5(60)]
After:   [Grid1(100), Grid2(100), Grid3(80), Grid4(60), Grid5(60)]
                                    ↑ sorted in descending order
```

**Step 2: Merge Order**

Grids are merged in priority order:
```python
result = Grid1.copy()  # Start with highest priority

# Grid 2 (priority 100) merged into result
result = merge(result, Grid2, priority='blend')

# Grid 3 (priority 80) merged into result
result = merge(result, Grid3, priority='blend')

# ... and so on
```

**Step 3: Overlap Behavior**

In overlapping regions, all grids are blended using feathering:
```
Overlap between Grid1(100) and Grid3(80):
  - NOT: "Grid1 completely overwrites Grid3"
  - BUT: "Blended using distance-based weights"
  
The priority affects ORDER, not absolute dominance in the current implementation.
```

### Current Priority Behavior

**Important:** In the current implementation:
- Priorities affect the **merge order**
- Higher priority grids are merged first
- Overlaps use **feathering/blending** regardless of priority
- No grid completely overwrites another based on priority alone

**Example:**
```python
# Grid A (priority 100) and Grid B (priority 50) overlap
# In the overlap region:
#   - Values are BLENDED using distance weights
#   - NOT: Grid A values used exclusively
```

### Enhanced Priority System (Future)

If you need priority to control overlap:

```python
# Current workaround: Merge in reverse order without blending
result = low_priority_grid.copy()
result = GridMerger.merge_two_grids(
    result, high_priority_grid,
    priority='second',  # High priority overwrites
    feather=False       # No blending
)
```

### Practical Priority Assignment

#### Scenario 1: Time-Based Quality

```python
# Recent surveys are better
grids_2024 = [grid1, grid2, grid3]  # Recent
grids_2020 = [grid4, grid5]         # Older
grids_2010 = [grid6, grid7]         # Legacy

priorities = (
    [100] * len(grids_2024) +
    [80] * len(grids_2020) +
    [60] * len(grids_2010)
)
```

#### Scenario 2: Resolution-Based

```python
priorities = []
for grid in grids:
    if grid.cellsize <= 10:
        priorities.append(100)  # High resolution
    elif grid.cellsize <= 25:
        priorities.append(80)   # Medium resolution
    else:
        priorities.append(60)   # Low resolution
```

#### Scenario 3: Survey Method

```python
priorities = []
for grid in grids:
    method = grid.metadata.get('survey_method')
    if method == 'ground_based':
        priorities.append(100)
    elif method == 'airborne_high':
        priorities.append(90)
    elif method == 'airborne_standard':
        priorities.append(70)
    else:
        priorities.append(50)
```

#### Scenario 4: Coverage/Quality Metrics

```python
priorities = []
for grid in grids:
    # Higher priority for better coverage
    coverage = len(grid.get_valid_data()) / (grid.nrows * grid.ncols)
    
    if coverage > 0.95:
        priorities.append(100)
    elif coverage > 0.85:
        priorities.append(80)
    else:
        priorities.append(60)
```

---

## Part 3: Impact of Quality Classification

### Impact on Non-Intersecting Grids

**Key Point:** Priorities don't help with non-intersecting grids.

```python
# Grid 1 (priority 100) at (0, 0)
# Grid 4 (priority 60) at (5000, 5000) - NO OVERLAP

# Priority 100 vs 60 doesn't matter because:
# - No overlap = no competition for same space
# - Both grids keep their data
# - Leveling still returns None (no overlap with reference)
```

**Priorities only matter in overlapping regions!**

### Impact on Leveling

**Current behavior:**
```python
# All grids leveled to first grid (regardless of priority)
merged = GridMerger.merge_multiple_grids(
    grids,
    priorities=[60, 100, 80],  # Grid 2 has highest priority
    level_to_first=True         # But Grid 1 is still reference!
)
```

Grid 1 (priority 60) becomes the reference, even though Grid 2 has higher priority!

**Better approach:** Make highest priority grid the reference:

```python
# Sort by priority first, then level
if priorities:
    sorted_pairs = sorted(zip(priorities, grids), 
                         key=lambda x: x[0], reverse=True)
    sorted_grids = [g for _, g in sorted_pairs]
    
    # Now highest priority is first (reference)
    merged = GridMerger.merge_with_auto_leveling(sorted_grids)
```

### Impact on Merge Quality

**With priorities:**
- ✅ Control merge order
- ✅ Ensure high-quality data processed first
- ✅ Better organization of heterogeneous datasets

**Without priorities:**
- ⚠️ Order-dependent results
- ⚠️ Low-quality data might influence result more
- ⚠️ No systematic quality control

### Visual Example

```
Scenario: 3 overlapping grids with different priorities

Grid A (priority 100): ████████████
Grid B (priority 80):      ████████████
Grid C (priority 60):          ████████████

Merge order: A → B → C

Result in overlaps:
  A-B overlap: Blended (but A processed first)
  B-C overlap: Blended (but B processed first)
  A-B-C triple overlap: All three blended
```

---

## Part 4: Complete Example

### Scenario: 47 Grids with Various Overlaps

```python
from gridmerge import Grid, GridMerger, GridAdjuster
import numpy as np

# Load 47 grids
grids = [Grid.read(f"survey_{i:03d}.tif") for i in range(47)]

# Assign priorities based on metadata
priorities = []
for i, grid in enumerate(grids):
    year = grid.metadata.get('year', 2000)
    
    if year >= 2020:
        priority = 100  # Recent, high quality
    elif year >= 2010:
        priority = 80   # Moderate age
    else:
        priority = 60   # Legacy data
    
    priorities.append(priority)
    print(f"Grid {i}: year={year}, priority={priority}")

# Check for overlaps
print("\nAnalyzing overlaps with reference (Grid 0):")
reference = grids[0]
for i, grid in enumerate(grids[1:], 1):
    overlap = reference.get_overlap(grid)
    if overlap:
        print(f"  Grid {i}: HAS overlap")
    else:
        print(f"  Grid {i}: NO overlap - will not be leveled!")

# Merge with priorities
print("\nMerging...")
merged = GridMerger.merge_multiple_grids(
    grids,
    priorities=priorities,
    level_to_first=True,
    use_dc_shift=True,
    polynomial_degree=1,
    feather=True
)

print(f"Merge complete: {merged.nrows}x{merged.ncols}")
print(f"Coverage: {100*len(merged.get_valid_data())/(merged.nrows*merged.ncols):.1f}%")

# Save with metadata
merged.metadata['merge_info'] = (
    f"Merged {len(grids)} grids with priority-based ordering. "
    f"Grids leveled where overlaps exist with reference grid."
)
merged.write("merged_47_with_priorities.tif")
```

---

## Summary

### Non-Intersecting Grids

✅ **DO:**
- Check for overlaps before expecting leveling
- Use chain leveling for connected but non-overlapping grids
- Document which grids were/weren't leveled
- Consider regional references for distant grids

❌ **DON'T:**
- Assume all grids will be leveled
- Expect corrections when grids don't overlap
- Ignore baseline differences in separate regions

### Quality Classification

✅ **DO:**
- Assign priorities based on objective criteria
- Use consistent priority ranges (e.g., 0-100)
- Document priority assignment logic
- Consider making highest priority the reference

❌ **DON'T:**
- Expect priorities to override blending in overlaps
- Assign random priorities without criteria
- Assume priority solves non-intersection issues

### Key Takeaways

1. **Overlaps are required** for DC shift/leveling to work
2. **Non-intersecting grids** are included but not leveled
3. **Priorities control order**, not absolute dominance
4. **Chain leveling** solves many non-intersection issues
5. **Document limitations** when merging diverse datasets
