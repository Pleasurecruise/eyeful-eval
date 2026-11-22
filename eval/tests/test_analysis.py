from __future__ import annotations

import unittest

from analysis.analyze import Score, bootstrap, detected, difference, mcnemar
from tests.fixtures import review


class Statistics(unittest.TestCase):
    def test_mcnemar(self) -> None:
        self.assertEqual(mcnemar(0, 0), 1.0)
        self.assertAlmostEqual(mcnemar(5, 0), 0.0625)
        self.assertAlmostEqual(mcnemar(0, 5), 0.0625)
        self.assertEqual(mcnemar(3, 3), 1.0)

    def test_bootstrap(self) -> None:
        estimate = bootstrap({str(i): (float(i % 2), 1.0) for i in range(40)})
        self.assertAlmostEqual(estimate.value, 0.5)
        self.assertLess(estimate.low, 0.5)
        self.assertGreater(estimate.high, 0.5)
        self.assertEqual(str(bootstrap({})), "n/a")

    def test_bootstrap_ignores_order(self) -> None:
        rows = {str(i): (float(i % 3 == 0), 1.0) for i in range(30)}
        self.assertEqual(bootstrap(rows), bootstrap(dict(reversed(list(rows.items())))))

    def test_difference(self) -> None:
        arm = {str(i): (float(i % 3 == 0), 1.0) for i in range(30)}
        estimate = difference(arm, arm)
        self.assertEqual((estimate.value, estimate.low, estimate.high), (0.0, 0.0, 0.0))

    def test_detected(self) -> None:
        reviews = [review("s", rep) for rep in (1, 2, 3)]
        scores = {r.key: Score({"a": "bug", "b": "bug"}, frozenset({"a"} if r.rep < 3 else {"b"}), frozenset()) for r in reviews}
        self.assertEqual(detected(reviews, scores, 2), {("s", "a"): True, ("s", "b"): False})
        self.assertEqual(detected(reviews, scores, 1), {("s", "a"): True, ("s", "b"): True})


if __name__ == "__main__":
    unittest.main()
