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

    def test_patch_series_sequence_and_integrity(self) -> None:
        patches = sorted((ROOT / "patches").glob("*.patch"))
        self.assertGreaterEqual(len(patches), 25)
        for i, patch in enumerate(patches, start=1):
            self.assertTrue(patch.name.startswith(f"{i:04d}-"), f"Patch out of order: {patch.name}")
            content = patch.read_text(encoding="utf-8")
            self.assertIn("diff --git", content, f"Patch missing diff: {patch.name}")
            self.assertNotIn("<<<<<<<", content)
            self.assertNotIn(">>>>>>>", content)

        patch_0024 = (ROOT / "patches/0024-feat-katalyst-add-omp-status-panel.patch").read_text()
        self.assertIn("+use crate::agent_connection_store::{AgentConnectionStatus, AgentConnectionStore};", patch_0024)
        self.assertIn("ToggleStatusPanel", patch_0024)
        self.assertIn("toggle_panel_focus::<agent_ui::KatalystStatusPanel>", patch_0024)

if __name__ == "__main__":
    unittest.main()
