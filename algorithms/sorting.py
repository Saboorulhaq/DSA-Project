"""
sorting.py - the 5 class algorithms (Bubble, Selection, Insertion, Merge, Quick)
             + 2 extra algorithms (Heap Sort, Shell Sort).

HOW IT WORKS
  Every algorithm sorts a list of PAIRS  (key, row)  IN PLACE and returns (comparisons, swaps).
  Only the key is compared, never the whole row.

COUNTING CONVENTIONS (explain these to your teacher)
  comparison = one time two KEYS are compared (a[i][0] > a[j][0]).
  swap       = one exchange of two elements (Bubble, Selection, Quick, Heap).
  Insertion and Shell sort do not swap; they SHIFT elements. Each shift is counted as one swap.
  Merge sort does not swap either; each element COPIED into the merged output is counted as one swap.
  Runtime is measured with time.perf_counter() around the sorting call only
  (building the keys is not included).
"""
import random
import time

# ------------------------------------------------------------------ keys
NUMERIC = ("int", "float")


def make_key(row, specs):
    """
    specs = list of (column, type, ascending). One spec = single sort, several = multi-level.
    Descending numbers use -value; descending text uses negative letter codes + a sentinel
    (so that "ab" and "abc" still sort in the correct reverse order).
    """
    parts = []
    for column, kind, ascending in specs:
        value = row[column]
        if kind in NUMERIC:
            parts.append(value if ascending else -value)
        else:
            text = str(value).lower()
            parts.append(text if ascending else tuple(-ord(c) for c in text) + (1,))
    return parts[0] if len(parts) == 1 else tuple(parts)


# ------------------------------------------------------------------ algorithms
def bubble_sort(a):
    comps = swaps = 0
    n = len(a)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            comps += 1
            if a[j][0] > a[j + 1][0]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swaps += 1
                swapped = True
        if not swapped:          # already sorted -> stop early (best case O(n))
            break
    return comps, swaps


def selection_sort(a):
    comps = swaps = 0
    n = len(a)
    for i in range(n - 1):
        smallest = i
        for j in range(i + 1, n):
            comps += 1
            if a[j][0] < a[smallest][0]:
                smallest = j
        if smallest != i:
            a[i], a[smallest] = a[smallest], a[i]
            swaps += 1
    return comps, swaps


def insertion_sort(a):
    comps = shifts = 0
    for i in range(1, len(a)):
        current = a[i]
        j = i - 1
        while j >= 0:
            comps += 1
            if a[j][0] > current[0]:
                a[j + 1] = a[j]       # shift right
                shifts += 1
                j -= 1
            else:
                break
        a[j + 1] = current
    return comps, shifts


def merge_sort(a):
    counts = [0, 0]                   # [comparisons, element copies]
    temp = a[:]

    def sort_range(lo, hi):           # sorts a[lo:hi]
        if hi - lo < 2:
            return
        mid = (lo + hi) // 2
        sort_range(lo, mid)
        sort_range(mid, hi)
        i, j, k = lo, mid, lo
        while i < mid and j < hi:
            counts[0] += 1
            if a[j][0] < a[i][0]:     # take from right only if STRICTLY smaller -> stable
                temp[k] = a[j]
                j += 1
            else:
                temp[k] = a[i]
                i += 1
            k += 1
            counts[1] += 1
        while i < mid:
            temp[k] = a[i]; i += 1; k += 1; counts[1] += 1
        while j < hi:
            temp[k] = a[j]; j += 1; k += 1; counts[1] += 1
        a[lo:hi] = temp[lo:hi]

    sort_range(0, len(a))
    return counts[0], counts[1]


def quick_sort(a):
    """Hoare partition + random pivot (handles many equal keys well). No deep recursion."""
    comps = swaps = 0
    stack = [(0, len(a) - 1)]
    while stack:
        lo, hi = stack.pop()
        while lo < hi:
            pivot = a[random.randint(lo, hi - 1)][0]
            i, j = lo - 1, hi + 1
            while True:
                i += 1
                comps += 1
                while a[i][0] < pivot:
                    i += 1
                    comps += 1
                j -= 1
                comps += 1
                while a[j][0] > pivot:
                    j -= 1
                    comps += 1
                if i >= j:
                    break
                a[i], a[j] = a[j], a[i]
                swaps += 1
            # sort the smaller part now, push the bigger part for later (keeps stack small)
            if j - lo < hi - j - 1:
                stack.append((j + 1, hi))
                hi = j
            else:
                stack.append((lo, j))
                lo = j + 1
    return comps, swaps


def heap_sort(a):
    """EXTRA algorithm 1."""
    comps = swaps = 0
    n = len(a)

    def sift_down(root, end):
        nonlocal comps, swaps
        while True:
            child = 2 * root + 1
            if child >= end:
                return
            if child + 1 < end:
                comps += 1
                if a[child + 1][0] > a[child][0]:
                    child += 1
            comps += 1
            if a[child][0] > a[root][0]:
                a[root], a[child] = a[child], a[root]
                swaps += 1
                root = child
            else:
                return

    for start in range(n // 2 - 1, -1, -1):      # build a max-heap
        sift_down(start, n)
    for end in range(n - 1, 0, -1):              # move the biggest to the end
        a[0], a[end] = a[end], a[0]
        swaps += 1
        sift_down(0, end)
    return comps, swaps


def shell_sort(a):
    """EXTRA algorithm 2: insertion sort on elements that are 'gap' apart."""
    comps = shifts = 0
    n = len(a)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            current = a[i]
            j = i
            while j >= gap:
                comps += 1
                if a[j - gap][0] > current[0]:
                    a[j] = a[j - gap]
                    shifts += 1
                    j -= gap
                else:
                    break
            a[j] = current
        gap //= 2
    return comps, shifts


ALGORITHMS = {
    "Bubble Sort":    {"func": bubble_sort,    "best": "O(n)",       "avg": "O(n²)",       "worst": "O(n²)",
                       "space": "O(1)",     "stable": True,  "extra": False},
    "Selection Sort": {"func": selection_sort, "best": "O(n²)",      "avg": "O(n²)",       "worst": "O(n²)",
                       "space": "O(1)",     "stable": False, "extra": False},
    "Insertion Sort": {"func": insertion_sort, "best": "O(n)",       "avg": "O(n²)",       "worst": "O(n²)",
                       "space": "O(1)",     "stable": True,  "extra": False},
    "Merge Sort":     {"func": merge_sort,     "best": "O(n log n)", "avg": "O(n log n)",  "worst": "O(n log n)",
                       "space": "O(n)",     "stable": True,  "extra": False},
    "Quick Sort":     {"func": quick_sort,     "best": "O(n log n)", "avg": "O(n log n)",  "worst": "O(n²)",
                       "space": "O(log n)", "stable": False, "extra": False},
    "Heap Sort":      {"func": heap_sort,      "best": "O(n log n)", "avg": "O(n log n)",  "worst": "O(n log n)",
                       "space": "O(1)",     "stable": False, "extra": True},
    "Shell Sort":     {"func": shell_sort,     "best": "O(n log n)", "avg": "depends on gaps", "worst": "O(n²)",
                       "space": "O(1)",     "stable": False, "extra": True},
}


def complexity_text(name):
    info = ALGORITHMS[name]
    return f"best {info['best']}, avg {info['avg']}, worst {info['worst']}"


# ------------------------------------------------------------------ helpers used by the GUI
def sort_rows(rows, specs, algorithm_name):
    """Sort `rows` with the chosen algorithm. Returns (sorted_rows, stats_dict)."""
    pairs = [(make_key(row, specs), row) for row in rows]
    func = ALGORITHMS[algorithm_name]["func"]
    start = time.perf_counter()
    comparisons, swaps = func(pairs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    stats = {"algorithm": algorithm_name, "ms": elapsed_ms, "comparisons": comparisons,
             "swaps": swaps, "rows": len(rows)}
    return [p[1] for p in pairs], stats


def benchmark(rows, specs):
    """Run every algorithm on its own COPY of the same data. Returns a list of result dicts."""
    pairs = [(make_key(row, specs), row) for row in rows]
    reference_keys = [p[0] for p in sorted(pairs, key=lambda p: p[0])]   # Python's sort = answer key
    results = []
    for name, info in ALGORITHMS.items():
        copy = pairs[:]                      # fresh, identical input for every algorithm
        start = time.perf_counter()
        comparisons, swaps = info["func"](copy)
        elapsed_ms = (time.perf_counter() - start) * 1000
        correct = [p[0] for p in copy] == reference_keys
        results.append({"algorithm": name, "ms": elapsed_ms, "comparisons": comparisons,
                        "swaps": swaps, "complexity": complexity_text(name), "space": info["space"],
                        "stable": info["stable"], "correct": correct, "rows": len(rows)})
    return results
