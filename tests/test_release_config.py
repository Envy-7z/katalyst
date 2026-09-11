from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


class ReleaseConfigTests(unittest.TestCase):
    def test_release_builds_both_macos_architectures_from_pinned_zed(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        revision = (ROOT / "ZED_REVISION").read_text().strip()
        self.assertRegex(revision, r"^[0-9a-f]{40}$")
        self.assertIn("macos-15-intel", workflow)
        self.assertIn("macos-15", workflow)
        self.assertIn("Katalyst-v${VERSION}-macOS-${RELEASE_ARCH}.zip", workflow)
        self.assertIn("SHA256SUMS", workflow)
        self.assertIn("MACOS_SIGNING_IDENTITY", workflow)
        self.assertIn("notarytool", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn("if: github.event_name != 'pull_request'", workflow)
        self.assertNotIn("    env:\n      MACOS_CERTIFICATE", workflow)
        self.assertIn("rm -f package/Katalyst.app/Contents/embedded.provisionprofile", workflow)

    def test_patch_series_includes_omp_first_patch(self) -> None:
        patch = ROOT / "patches/0020-feat-katalyst-make-OMP-the-first-run-agent.patch"
        self.assertTrue(patch.is_file())
        self.assertIn("katalyst_default_agent", patch.read_text())
        self.assertIn("VectorName::KatalystLogo", patch.read_text())
        self.assertIn("Auto import: On", patch.read_text())
        self.assertIn("Syncing Cursor and Codex chats", patch.read_text())

    def test_public_runtime_excludes_private_workflow_hook(self) -> None:
        self.assertFalse((ROOT / "config/omp/hooks/pre/plan-auto-open.ts").exists())
        installer = (ROOT / "install.sh").read_text()
        self.assertNotIn("plan-auto-open", installer)
        self.assertIn("katalyst-migrate-profile", installer)


if __name__ == "__main__":
    unittest.main()
