import os
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).parents[1]


class ProductPrinciplesTests(unittest.TestCase):
    def test_principles_file_exists_and_contains_all_25_rules(self) -> None:
        principles_file = ROOT / "PRINCIPLES.md"
        self.assertTrue(principles_file.exists(), "PRINCIPLES.md must exist at root")
        content = principles_file.read_text(encoding="utf-8")

        for i in range(1, 26):
            self.assertRegex(
                content,
                rf"## {i}\. ",
                f"Missing Principle {i} in PRINCIPLES.md",
            )

        self.assertIn("STABILITY > FEATURES", content)
        self.assertIn("NATIVE APP FEEL", content)
        self.assertIn("CODEX-LIKE CALMNESS", content)
        self.assertIn("RESPONSIVENESS IS A FEATURE", content)
        self.assertIn("OPTIMIZE FOR PERCEIVED PERFORMANCE", content)
        self.assertIn("AVOID \"FEATURE BLOAT\"", content)
        self.assertIn("PROGRESSIVE DISCLOSURE", content)
        self.assertIn("NO REDUNDANT STATE", content)
        self.assertIn("MINIMIZE BACKGROUND WORK", content)
        self.assertIn("MEMORY IS A FIRST-CLASS CONSTRAINT", content)
        self.assertIn("RENDER ONLY WHAT MATTERS", content)
        self.assertIn("ANIMATION MUST SERVE INFORMATION", content)
        self.assertIn("KEYBOARD-FIRST", content)
        self.assertIn("INFORMATION HIERARCHY", content)
        self.assertIn("ERROR UX", content)
        self.assertIn("FAILURE MUST BE GRACEFUL", content)
        self.assertIn("LONG-RUNNING AGENTS", content)
        self.assertIn("DO NOT OVER-ENGINEER", content)
        self.assertIn("MEASURE BEFORE CLAIMING", content)
        self.assertIn("EVERY FEATURE HAS A PERFORMANCE BUDGET", content)
        self.assertIn("FEATURE PRIORITY", content)
        self.assertIn("THE \"WOULD I WANT THIS OPEN ALL DAY?\" TEST", content)
        self.assertIn("THE \"CODEX FEEL\" TEST", content)
        self.assertIn("THE \"NATIVE ZED\" TEST", content)
        self.assertIn("FINAL RULE", content)

    def test_readme_references_principles(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("PRINCIPLES.md", readme)
        self.assertIn("Architecture & Product Principles", readme)
        self.assertIn("STABILITY > PERFORMANCE > UX POLISH > FEATURES", readme)

    def test_default_exclusions_in_installer_and_patches(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("Katalyst.app", installer)

        patch_0026 = (ROOT / "patches/0026-fix-katalyst-decouple-git-checkpoint-from-prompt-sen.patch").read_text(encoding="utf-8")
        for excluded in ["node_modules", "target", "dist", "build", ".next", ".cache", "DerivedData", "coverage", "tmp", "logs"]:
            self.assertIn(excluded, patch_0026, f"Exclusion {excluded} missing from patch 0026")

    def test_patches_clean_and_monotonic(self) -> None:
        patches = sorted((ROOT / "patches").glob("*.patch"))
        self.assertGreaterEqual(len(patches), 26)
        for idx, patch in enumerate(patches, start=1):
            self.assertTrue(patch.name.startswith(f"{idx:04d}-"), f"Patch sequence broken: {patch.name}")
            content = patch.read_text(encoding="utf-8")
            self.assertNotIn("<<<<<<<", content)
            self.assertNotIn(">>>>>>>", content)
            self.assertTrue("From: Katalyst" in content and "@katalyst.dev" in content, f"Non-generic author in patch {patch.name}")


if __name__ == "__main__":
    unittest.main()
