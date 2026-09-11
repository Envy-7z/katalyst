import json
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "bin" / "katalyst-migrate-profile"


class ProfileMigrationTests(unittest.TestCase):
    def test_keeps_private_sources_local_and_merges_compatible_mcp_servers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            state = home / ".katalyst"
            (home / ".agents" / "skills" / "private-review").mkdir(parents=True)
            (home / ".agents" / "skills" / "private-review" / "SKILL.md").write_text("private workflow")
            (home / ".cursor").mkdir(parents=True)
            (home / ".cursor" / "mcp.json").write_text(json.dumps({"mcpServers": {
                "browser": {"command": "npx", "args": ["browser-mcp"]}
            }}))
            (home / ".cursor" / "rules").mkdir()
            (home / ".cursor" / "rules" / "private.mdc").write_text("private rule")
            (home / ".codex").mkdir(parents=True)
            (home / ".codex" / "config.toml").write_text(textwrap.dedent("""
                [mcp_servers.docs]
                url = "https://example.test/mcp"
                [mcp_servers.computer_use]
                command = "./Codex Computer Use.app/Contents/MacOS/client"
            """))
            (home / ".codex" / "hooks.json").write_text('{"hooks": []}')
            client = home / ".codex" / "computer-use" / "Codex Computer Use.app" / "Contents" / "MacOS" / "client"
            client.parent.mkdir(parents=True)
            client.write_text("client")
            (home / ".omp" / "agent").mkdir(parents=True)
            (home / ".omp" / "agent" / "mcp.json").write_text(json.dumps({"mcpServers": {
                "existing": {"command": "existing-mcp"}
            }}))

            result = subprocess.run(
                [str(SCRIPT), "--home", str(home), "--state-home", str(state), "--json"],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["skillsImported"], 1)
            self.assertEqual(set(summary["mcpImported"]), {"browser", "computer_use", "docs"})
            self.assertTrue((state / "skills" / "cursor-private-review" / "SKILL.md").is_file())
            self.assertTrue((state / "private-profile" / "codex" / "hooks.json").is_file())
            self.assertTrue((state / "private-profile" / "cursor" / "rules" / "private.mdc").is_file())
            merged = json.loads((home / ".omp" / "agent" / "mcp.json").read_text())
            self.assertEqual(set(merged["mcpServers"]), {"existing", "browser", "computer_use", "docs"})
            self.assertEqual(merged["mcpServers"]["computer_use"]["command"], str(client))

    def test_existing_omp_server_wins_name_collision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            state = home / ".katalyst"
            (home / ".cursor").mkdir(parents=True)
            (home / ".cursor" / "mcp.json").write_text(json.dumps({"mcpServers": {
                "same": {"command": "cursor-server"}
            }}))
            (home / ".omp" / "agent").mkdir(parents=True)
            output = home / ".omp" / "agent" / "mcp.json"
            output.write_text(json.dumps({"mcpServers": {"same": {"command": "omp-server"}}}))

            result = subprocess.run([str(SCRIPT), "--home", str(home), "--state-home", str(state), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["mcpSkipped"], ["same"])
            self.assertEqual(json.loads(output.read_text())["mcpServers"]["same"]["command"], "omp-server")


if __name__ == "__main__":
    unittest.main()
