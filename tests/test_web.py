from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.assets: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(str(attributes["id"]))
        if tag == "script" and attributes.get("src"):
            self.scripts.append(str(attributes["src"]))
            self.assets.append(str(attributes["src"]))
        if tag == "link" and attributes.get("href"):
            self.assets.append(str(attributes["href"]))
        if tag == "a" and attributes.get("href") and not str(attributes["href"]).startswith("#"):
            self.assets.append(str(attributes["href"]))


class WebContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        cls.javascript = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        cls.parser = PageParser()
        cls.parser.feed(cls.html)

    def test_local_assets_resolve_and_generated_data_loads_first(self) -> None:
        self.assertEqual(self.parser.scripts, ["data.generated.js", "app.js"])
        for asset in self.parser.assets:
            path = (ROOT / "web" / asset).resolve()
            self.assertTrue(path.is_file(), f"missing local asset: {asset}")

    def test_dom_ids_are_unique(self) -> None:
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))
        for required in {"main-content", "basisChart", "gpuTabs", "pairDetail", "eventLedger"}:
            self.assertIn(required, self.parser.ids)

    def test_accessible_interaction_and_responsive_contracts_are_present(self) -> None:
        self.assertIn('role="tablist"', self.html)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("prefers-reduced-motion", self.css)
        self.assertIn("@media (max-width: 47.99rem)", self.css)
        self.assertIn('event.key === "ArrowRight"', self.javascript)
        self.assertIn('setAttribute("aria-selected"', self.javascript)
        self.assertIsNone(re.search(r"outline\s*:\s*none", self.css))


if __name__ == "__main__":
    unittest.main()
