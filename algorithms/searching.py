"""
searching.py - two search algorithms for EXACT match on one column.
  Linear search : check every row, one by one.            O(n)
  Binary search : needs sorted data; halves the range.    O(log n) (after sorting once)
Both return (matching_rows, comparisons).
"""
from algorithms.sorting import make_key, sort_rows


def _target_key(value, kind):
    if kind in ("int", "float"):
        return float(value)
    return str(value).lower()


def linear_search_exact(rows, column, value, kind):
    target = _target_key(value, kind)
    matches, comparisons = [], 0
    for row in rows:
        comparisons += 1
        if make_key(row, [(column, kind, True)]) == target:
            matches.append(row)
    return matches, comparisons


def binary_search_exact(rows, column, value, kind):
    """Sorts a COPY with Merge Sort first (not counted), then binary searches."""
    specs = [(column, kind, True)]
    target = _target_key(value, kind)
    ordered, _ = sort_rows(rows, specs, "Merge Sort")
    keys = [make_key(r, specs) for r in ordered]
    comparisons = 0
    low, high = 0, len(keys) - 1
    first = -1
    while low <= high:                      # find the FIRST position equal to target
        mid = (low + high) // 2
        comparisons += 1
        if keys[mid] < target:
            low = mid + 1
        elif keys[mid] > target:
            high = mid - 1
        else:
            first = mid
            high = mid - 1
    if first == -1:
        return [], comparisons
    matches = []
    i = first
    while i < len(keys) and keys[i] == target:
        matches.append(ordered[i])
        i += 1
    return matches, comparisons
