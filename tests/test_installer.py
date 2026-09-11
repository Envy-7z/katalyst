import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


class InstallerTests(unittest.TestCase):
    def test_dry_run_uses_release_asset_and_separate_runtime_directory(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            env = os.environ.copy()
            env["HOME"] = home
            env["KATALYST_ARCH"] = "arm64"
            result = subprocess.run(
                ["bash", str(ROOT / "install.sh"), "--dry-run"],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("Katalyst-v0.2.0-macOS-arm64.zip", result.stdout)
            self.assertIn(f"{home}/.local/share/katalyst", result.stdout)
            self.assertNotIn("brew install --cask zed", result.stdout)
            self.assertFalse((Path(home) / ".katalyst").exists())

    def test_installed_session_sync_wrapper_finds_sibling_module(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            install_bin = Path(home) / ".local/bin"
            install_bin.mkdir(parents=True)
            shutil.copy2(ROOT / "bin/katalyst-session-sync", install_bin)
            shutil.copy2(ROOT / "lib/katalyst_session_sync.py", install_bin)
            result = subprocess.run(
                [str(install_bin / "katalyst-session-sync"), "status", "--json"],
                env={**os.environ, "HOME": home},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn('"cursor": 0', result.stdout)

    def test_upgrade_snapshots_configs_and_verifies_runtime_before_extract(self) -> None:
        installer = (ROOT / "install.sh").read_text()
        snapshot_at = installer.index("snapshot_config \"$HOME/.config/zed/settings.json\"")
        legacy_move_at = installer.index('if [[ -d "$KATALYST_STATE_HOME/.git" ]]')
        verify_at = installer.index('Checksum mismatch for ${RUNTIME_ASSET}')
        extract_at = installer.index('tar -xzf "$TEMP_DIR/${RUNTIME_ASSET}"')
        self.assertLess(snapshot_at, legacy_move_at)
        self.assertLess(verify_at, extract_at)
        self.assertIn("if [[ \"$INSTALL_COMPLETE\" -ne 1 ]]", installer)
        self.assertIn('mv "$KATALYST_APPLICATIONS_HOME/Katalyst.app.previous" "$KATALYST_APPLICATIONS_HOME/Katalyst.app"', installer)

    @unittest.skipUnless(sys.platform == "darwin", "installer integration requires macOS ditto")
    def test_v01_late_upgrade_failure_restores_all_user_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            applications = root / "Applications"
            release = root / "release"
            legacy = home / ".katalyst"
            old_app = applications / "Katalyst.app"
            new_app = root / "payload" / "Katalyst.app"
            (legacy / ".git").mkdir(parents=True)
            (legacy / "config" / "zed").mkdir(parents=True)
            (legacy / "config" / "zed" / "settings.json").write_text('{"legacy": true}\n')
            (legacy / "skills" / "legacy-skill").mkdir(parents=True)
            (legacy / "skills" / "legacy-skill" / "SKILL.md").write_text("legacy skill")
            (home / ".config" / "zed").mkdir(parents=True)
            (home / ".config" / "zed" / "settings.json").symlink_to(legacy / "config" / "zed" / "settings.json")
            (home / ".omp" / "agent").mkdir(parents=True)
            skills_link = home / ".omp" / "agent" / "skills"
            skills_link.symlink_to(legacy / "skills")
            (home / ".local" / "bin").mkdir(parents=True)
            old_helper = home / ".local" / "bin" / "katalyst-update"
            old_helper.write_text("old helper")
            launch_dir = home / "Library" / "LaunchAgents"
            launch_dir.mkdir(parents=True)
            old_plist = launch_dir / "dev.katalyst.session-sync.plist"
            old_plist.write_text("old launch agent")
            old_app.mkdir(parents=True)
            (old_app / "marker").write_text("old")
            new_app.mkdir(parents=True)
            (new_app / "marker").write_text("new")
            release.mkdir()
            asset = release / "Katalyst-v0.2.0-macOS-arm64.zip"
            subprocess.run(["ditto", "-c", "-k", "--keepParent", str(new_app), str(asset)], check=True)
            checksum = subprocess.check_output(["shasum", "-a", "256", str(asset)], text=True).split()[0]
            (release / "SHA256SUMS").write_text(f"{checksum}  {asset.name}\n")
            env = {
                **os.environ,
                "HOME": str(home),
                "KATALYST_ARCH": "arm64",
                "KATALYST_APPLICATIONS_HOME": str(applications),
                "KATALYST_RELEASE_BASE": release.as_uri(),
                "KATALYST_TEST_FAIL_AFTER_USER_MUTATIONS": "1",
                "KATALYST_SKIP_LAUNCHCTL": "1",
            }
            result = subprocess.run(
                ["bash", str(ROOT / "install.sh")], cwd=ROOT, env=env,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            self.assertEqual(result.returncode, 98, result.stdout)
            self.assertEqual((old_app / "marker").read_text(), "old")
            self.assertTrue((legacy / ".git").is_dir())
            self.assertEqual((home / ".config" / "zed" / "settings.json").read_text(), '{"legacy": true}\n')
            self.assertTrue((home / ".config" / "zed" / "settings.json").is_symlink())
            self.assertEqual(old_helper.read_text(), "old helper")
            self.assertEqual(old_plist.read_text(), "old launch agent")
            self.assertTrue(skills_link.is_symlink())
            self.assertEqual(skills_link.readlink(), legacy / "skills")
            self.assertEqual((skills_link / "legacy-skill" / "SKILL.md").read_text(), "legacy skill")


if __name__ == "__main__":
    unittest.main()
