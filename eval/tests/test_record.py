from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from record import registry
from tests.fixtures import review


class Registry(unittest.TestCase):
    def test_one_setup_per_run(self) -> None:
        with tempfile.TemporaryDirectory() as root, mock.patch.object(registry, "ROOT", Path(root)), mock.patch.object(registry, "sh", return_value="c0ffee\n"):
            out = Path(root) / "runs" / "abc"
            out.mkdir(parents=True)
            fixed = {"dataset": ["crb"], "eyeful": {"sha256": "1"}}
            registry.begin(out, fixed, {"configs": "panel"})
            registry.finish(out, [review("s", 1)])
            registry.begin(out, fixed, {"configs": "fixed"})
            manifest = json.loads((Path(root) / "registry" / "crb" / "abc.json").read_text())
            self.assertEqual([i["configs"] for i in manifest["invocations"]], ["panel", "fixed"])
            self.assertEqual(manifest["outcomes"], {"complete": 1})
            self.assertIsNone(manifest["invocations"][-1]["finished"])
            self.assertEqual(manifest["invocations"][0]["commit"], "c0ffee")
            self.assertNotIn("scripts", manifest["setup"])
            with self.assertRaises(SystemExit):
                registry.begin(out, fixed | {"eyeful": {"sha256": "2"}}, {"configs": "panel"})


if __name__ == "__main__":
    unittest.main()
