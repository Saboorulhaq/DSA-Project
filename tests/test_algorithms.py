"""Run from the project root:   python -m unittest tests.test_algorithms -v"""
import random
import unittest

from algorithms.filters import filter_rows, make_condition
from algorithms.searching import binary_search_exact, linear_search_exact
from algorithms.sorting import ALGORITHMS, benchmark, make_key, sort_rows

TYPES = {"cat": "text", "price": "float", "year": "int", "title": "text"}


def sample_rows(n, seed=1):
    r = random.Random(seed)
    return [{"cat": r.choice(["Art", "Fiction", "Science", "art"]), "price": round(r.uniform(1, 50), 2),
             "year": r.randint(1990, 2020), "title": f"T{i}"} for i in range(n)]


class SortingTests(unittest.TestCase):
    def test_all_algorithms_match_python_sorted(self):
        for name, info in ALGORITHMS.items():
            for data in ([], [5], [1, 2, 3, 4], [4, 3, 2, 1], [7] * 20,
                         [random.Random(s).randint(0, 30) for s in range(200)]):
                pairs = [(v, i) for i, v in enumerate(data)]
                info["func"](pairs)
                self.assertEqual([p[0] for p in pairs], sorted(data), name)

    def test_stability_claims(self):
        r = random.Random(3)
        data = [(r.randint(0, 5), i) for i in range(300)]
        expected = sorted(data, key=lambda p: p[0])          # Python's sort is stable
        for name, info in ALGORITHMS.items():
            if info["stable"]:
                pairs = data[:]
                info["func"](pairs)
                self.assertEqual(pairs, expected, f"{name} should be stable")

    def test_counting_convention(self):
        expect = {"Bubble Sort": (3, 3), "Selection Sort": (3, 1), "Insertion Sort": (3, 3)}
        for name, (c, s) in expect.items():
            self.assertEqual(ALGORITHMS[name]["func"]([(3, 0), (2, 1), (1, 2)]), (c, s), name)
        self.assertEqual(ALGORITHMS["Merge Sort"]["func"]([(2, 0), (1, 1)]), (1, 2))
        self.assertEqual(ALGORITHMS["Bubble Sort"]["func"]([(1, 0), (2, 1), (3, 2)]), (2, 0))

    def test_multilevel_and_descending(self):
        rows = sample_rows(500)
        specs = [("cat", "text", True), ("price", "float", False)]
        expected = sorted(rows, key=lambda r: (r["cat"].lower(), -r["price"]))
        for name in ALGORITHMS:
            result, stats = sort_rows(rows, specs, name)
            self.assertEqual([(r["cat"].lower(), r["price"]) for r in result],
                             [(r["cat"].lower(), r["price"]) for r in expected], name)
            self.assertGreaterEqual(stats["ms"], 0)

    def test_descending_text_prefix(self):
        rows = [{"t": "ab"}, {"t": "abc"}, {"t": "b"}, {"t": "a"}]
        result, _ = sort_rows(rows, [("t", "text", False)], "Merge Sort")
        self.assertEqual([r["t"] for r in result], ["b", "abc", "ab", "a"])

    def test_benchmark_all_correct(self):
        results = benchmark(sample_rows(400), [("price", "float", True)])
        self.assertEqual(len(results), 7)
        self.assertTrue(all(r["correct"] for r in results))


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"cat": "Fiction", "price": 10.0, "year": 1999, "title": "Alpha Book"},
            {"cat": "Science", "price": 20.0, "year": 2005, "title": "Beta Atlas"},
            {"cat": "Fiction", "price": 30.0, "year": 2015, "title": "Gamma Book"},
            {"cat": "Art", "price": 40.0, "year": 2020, "title": "Delta"},
        ]

    def titles(self, conds):
        return [r["title"] for r in filter_rows(self.rows, conds, TYPES)]

    def test_string_ops(self):
        c = make_condition
        self.assertEqual(self.titles([c("title", "contains", "book")]), ["Alpha Book", "Gamma Book"])
        self.assertEqual(self.titles([c("title", "starts with", "be")]), ["Beta Atlas"])
        self.assertEqual(self.titles([c("title", "ends with", "book")]), ["Alpha Book", "Gamma Book"])
        self.assertEqual(self.titles([c("cat", "equals", "art")]), ["Delta"])
        self.assertEqual(len(self.titles([c("cat", "not contains", "fiction")])), 2)

    def test_numeric_ops(self):
        c = make_condition
        self.assertEqual(self.titles([c("price", ">", "20")]), ["Gamma Book", "Delta"])
        self.assertEqual(self.titles([c("year", "<=", "2005")]), ["Alpha Book", "Beta Atlas"])
        with self.assertRaises(ValueError):
            self.titles([c("price", ">", "abc")])

    def test_and_or_not(self):
        c = make_condition
        and_ = [c("cat", "equals", "Fiction"), c("price", ">", "15", connector="AND")]
        self.assertEqual(self.titles(and_), ["Gamma Book"])
        or_ = [c("cat", "equals", "Art"), c("cat", "equals", "Science", connector="OR")]
        self.assertEqual(self.titles(or_), ["Beta Atlas", "Delta"])
        not_ = [c("cat", "equals", "Fiction"), c("year", "<", "2000", negate=True, connector="AND")]
        self.assertEqual(self.titles(not_), ["Gamma Book"])
        mix = [c("cat", "equals", "Art"), c("cat", "equals", "Fiction", connector="OR"),
               c("price", ">", "15", connector="AND")]          # Art OR (Fiction AND price>15)
        self.assertEqual(self.titles(mix), ["Gamma Book", "Delta"])

    def test_search_algorithms_agree(self):
        rows = sample_rows(1000)
        for col, val in [("cat", "art"), ("year", "2000"), ("price", "999")]:
            a, _ = linear_search_exact(rows, col, val, TYPES[col])
            b, _ = binary_search_exact(rows, col, val, TYPES[col])
            self.assertEqual(sorted(r["title"] for r in a), sorted(r["title"] for r in b))


if __name__ == "__main__":
    unittest.main()
