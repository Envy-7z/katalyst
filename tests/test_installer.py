import json
import os
import plistlib
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

            version = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "0.2.0"
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(f"Katalyst-v{version}-macOS-arm64.zip", result.stdout)
            self.assertIn(f"{home}/.local/share/katalyst", result.stdout)
            self.assertNotIn("brew install --cask zed", result.stdout)
            self.assertFalse((Path(home) / ".katalyst").exists())

    def test_update_does_not_downgrade_runtime_newer_than_latest_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            (data / "VERSION").write_text("0.3.2\n")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            curl = bin_dir / "curl"
            curl.write_text('#!/bin/sh\nprintf \'{"tag_name":"v0.3.1"}\\n\'\n')
            curl.chmod(0o755)
            omp = bin_dir / "omp"
            omp.write_text(f'#!/bin/sh\nprintf "omp update invoked\\n" >> "{root / "updates"}"\n')
            omp.chmod(0o755)

            result = subprocess.run(
                ["bash", str(ROOT / "bin/katalyst-update")],
                env={**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                     "KATALYST_DATA_HOME": str(data), "KATALYST_APPLICATIONS_HOME": str(root / "Applications")},
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("newer than latest release", result.stdout)
            self.assertTrue((root / "updates").exists())

    def test_update_never_replaces_newer_app_when_runtime_version_lags(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            (data / "VERSION").write_text("0.3.0\n")
            (data / "APP_VERSION").write_text("0.3.2\n")
            app = root / "Applications/Katalyst.app/Contents"
            app.mkdir(parents=True)
            (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleShortVersionString": "0.3.2"}))
            bin_dir = root / "bin"
            bin_dir.mkdir()
            curl = bin_dir / "curl"
            curl.write_text('#!/bin/sh\nprintf \'{"tag_name":"v0.3.1"}\\n\'\n')
            curl.chmod(0o755)
            omp = bin_dir / "omp"
            omp.write_text("#!/bin/sh\nexit 0\n")
            omp.chmod(0o755)

            result = subprocess.run(
                ["bash", str(ROOT / "bin/katalyst-update")],
                env={**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                     "KATALYST_DATA_HOME": str(data), "KATALYST_APPLICATIONS_HOME": str(root / "Applications")},
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("installed app 0.3.2", result.stdout)
            self.assertIn("newer than latest release", result.stdout)
            self.assertEqual((app / "Info.plist").read_bytes(), plistlib.dumps({"CFBundleShortVersionString": "0.3.2"}))

    def test_update_does_not_guess_app_version_from_zed_bundle_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            (data / "VERSION").write_text("0.3.0\n")
            app = root / "Applications/Katalyst.app/Contents"
            app.mkdir(parents=True)
            (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleShortVersionString": "1.21.0"}))
            bin_dir = root / "bin"
            bin_dir.mkdir()
            curl = bin_dir / "curl"
            curl.write_text('#!/bin/sh\nprintf \'{"tag_name":"v0.3.1"}\\n\'\n')
            curl.chmod(0o755)
            omp = bin_dir / "omp"
            omp.write_text("#!/bin/sh\nexit 0\n")
            omp.chmod(0o755)

            result = subprocess.run(
                ["bash", str(ROOT / "bin/katalyst-update")],
                env={**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                     "KATALYST_DATA_HOME": str(data), "KATALYST_APPLICATIONS_HOME": str(root / "Applications")},
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("app release version unknown", result.stdout)
            self.assertEqual((data / "VERSION").read_text().strip(), "0.3.0")

    def test_update_defers_app_install_while_editor_is_running(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            (data / "VERSION").write_text("0.3.0\n")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            curl = bin_dir / "curl"
            curl.write_text(f'#!/bin/sh\nprintf "x\\n" >> "{root / "requests"}"\nprintf \'{{"tag_name":"v0.3.1"}}\\n\'\n')
            curl.chmod(0o755)
            pgrep = bin_dir / "pgrep"
            pgrep.write_text("#!/bin/sh\nexit 0\n")
            pgrep.chmod(0o755)
            omp = bin_dir / "omp"
            omp.write_text("#!/bin/sh\nexit 0\n")
            omp.chmod(0o755)

            result = subprocess.run(
                ["bash", str(ROOT / "bin/katalyst-update")],
                env={**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                     "KATALYST_DATA_HOME": str(data), "KATALYST_APPLICATIONS_HOME": str(root / "Applications")},
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("quit it before installing", result.stdout)
            self.assertEqual((root / "requests").read_text().splitlines(), ["x"])

    def test_installed_session_sync_wrapper_finds_sibling_module(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            install_bin = Path(home) / ".local/bin"
            install_bin.mkdir(parents=True)
            shutil.copy2(ROOT / "bin/katalyst-session-sync", install_bin)
            shutil.copy2(ROOT / "lib/katalyst_session_sync.py", install_bin)
            stale_lib = install_bin.parent / "lib"
            stale_lib.mkdir()
            (stale_lib / "katalyst_session_sync.py").write_text('raise RuntimeError("shadowed by stale importer")\n')
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

    def test_skills_update_merges_without_wiping_custom_user_skills(self) -> None:
        installer = (ROOT / "install.sh").read_text()
        self.assertNotIn('rm -rf "$KATALYST_STATE_HOME/skills"\n', installer)
        self.assertIn('ditto "$KATALYST_DATA_HOME/skills" "$KATALYST_STATE_HOME/skills"', installer)

    @unittest.skipUnless(sys.platform == "darwin", "installer integration requires macOS ditto")
    def test_successful_install_records_app_release_separately_from_zed_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            existing_omp = {
                "type": "custom",
                "command": "/tmp/custom-omp",
                "args": ["acp"],
                "default_config_options": {"model": "anthropic/example"},
                "env": {"EXAMPLE_API_KEY": "existing-value"},
            }
            settings = home / ".config/zed/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"agent_servers": {"omp": existing_omp}, "theme": "custom"}))
            payload = root / "payload/Katalyst.app"
            payload.mkdir(parents=True)
            (payload / "Info.plist").write_bytes(plistlib.dumps({"CFBundleShortVersionString": "1.21.0"}))
            release = root / "release"
            release.mkdir()
            version = (ROOT / "VERSION").read_text().strip()
            asset = release / f"Katalyst-v{version}-macOS-arm64.zip"
            subprocess.run(["ditto", "-c", "-k", "--keepParent", str(payload), str(asset)], check=True)
            checksum = subprocess.check_output(["shasum", "-a", "256", str(asset)], text=True).split()[0]
            (release / "SHA256SUMS").write_text(f"{checksum}  {asset.name}\n")

            result = subprocess.run(
                ["bash", str(ROOT / "install.sh")], cwd=ROOT,
                env={**os.environ, "HOME": str(home), "KATALYST_ARCH": "arm64",
                     "KATALYST_APPLICATIONS_HOME": str(root / "Applications"),
                     "KATALYST_RELEASE_BASE": release.as_uri(), "KATALYST_SKIP_LAUNCHCTL": "1"},
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            installed_data = home / ".local/share/katalyst"
            self.assertEqual((installed_data / "VERSION").read_text().strip(), version)
            self.assertEqual((installed_data / "APP_VERSION").read_text().strip(), version)
            self.assertEqual(
                plistlib.loads((root / "Applications/Katalyst.app/Info.plist").read_bytes())["CFBundleShortVersionString"],
                "1.21.0",
            )
            installed_settings = json.loads(settings.read_text())
            self.assertEqual(installed_settings["agent_servers"]["omp"], existing_omp)
            self.assertEqual(installed_settings["theme"], "custom")
            self.assertTrue((home / ".local/bin/katalyst-mobile").is_file())
            self.assertTrue((home / ".local/bin/katalyst-search").is_file())

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
            version = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "0.2.0"
            release.mkdir()
            asset = release / f"Katalyst-v{version}-macOS-arm64.zip"
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
