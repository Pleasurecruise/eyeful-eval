from __future__ import annotations

import unittest

from core.layout import official, pull


class Layout(unittest.TestCase):
    def test_official_image(self) -> None:
        self.assertEqual(official("psf__requests-1142", "x86_64"), "swebench/sweb.eval.x86_64.psf_1776_requests-1142:latest")

    def test_pull(self) -> None:
        self.assertEqual(pull("https://github.com/keycloak/keycloak/pull/32918"), ("keycloak__keycloak-32918", "keycloak", "keycloak", "32918"))
        self.assertIsNone(pull("https://github.com/keycloak/keycloak/issues/1"))


if __name__ == "__main__":
    unittest.main()
