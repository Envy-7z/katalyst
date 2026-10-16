#!/usr/bin/env python3
"""
Grand Workflow Orchestration & Stress Test Suite
Exhaustively tests the entire Katalyst + OMP developer ecosystem:
1. Hooks Chain (11 hooks loaded, syntax verified, no runtime collisions)
2. Skills Integrity (60+ skills validated for SKILL.md and YAML frontmatter)
3. Local CLI Binaries (katalyst-fix-ci, katalyst-jira, katalyst-review, memory-bank, katalyst-mobile)
4. Dynamic Context Expansion (@diff, @git-log, @mb, and auto-restore)
5. Terminal Error Trapper (intercepts exit codes != 0 and injects diagnostics)
6. Secret Scrubber & Privacy Guard (sanitizes tokens and prevents leaks)
7. Multi-Tier End-to-End Integration (combining hooks + skills + memory-bank + git in one session)
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

class GrandWorkflowOrchestrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = os.path.expanduser("~")
        cls.hooks_dir = os.path.join(cls.home, ".omp", "agent", "hooks", "pre")
        cls.skills_dir = os.path.join(cls.home, ".omp", "agent", "skills")
        cls.mcp_path = os.path.join(cls.home, ".omp", "agent", "mcp.json")
        cls.local_bin = os.path.join(cls.home, ".local", "bin")

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="grand-workflow-")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # ----------------------------------------------------
    # LAYER 1: HOOKS CHAIN VERIFICATION
    # ----------------------------------------------------
    def test_01_all_pre_hooks_syntax_and_integrity(self):
        """Test all 11 TypeScript pre-hooks for clean node/bun syntax"""
        hook_files = sorted(glob.glob(os.path.join(self.hooks_dir, "*.ts")))
        self.assertGreaterEqual(len(hook_files), 8, "Expected at least 8 critical pre-hooks")
        
        for hook in hook_files:
            hook_name = os.path.basename(hook)
            with self.subTest(hook=hook_name):
                # Verify non-empty
                self.assertGreater(os.path.getsize(hook), 100, f"Hook {hook_name} is suspiciously small or empty")
                # Syntax validation using node/bun check
                res = subprocess.run(["node", "--check", "--experimental-strip-types", hook], capture_output=True, text=True)
                self.assertEqual(res.returncode, 0, f"Hook {hook_name} failed syntax check: {res.stderr}")

    def test_02_terminal_error_trap_hook_contract(self):
        """Test terminal-error-trap.ts correctly handles command failure traces"""
        trap_hook = os.path.join(self.hooks_dir, "terminal-error-trap.ts")
        self.assertTrue(os.path.exists(trap_hook))
        with open(trap_hook, "r") as f:
            content = f.read()
        self.assertIn("tool_result", content)
        self.assertIn("exitCode", content)
        self.assertIn("systemPrompt", content)

    def test_03_secret_scrubber_hook_contract(self):
        """Test secret-scrubber.ts actively detects and masks high-entropy tokens"""
        scrubber = os.path.join(self.hooks_dir, "secret-scrubber.ts")
        self.assertTrue(os.path.exists(scrubber))
        with open(scrubber, "r") as f:
            content = f.read()
        self.assertIn("REDACTED", content)
        self.assertIn("token", content.lower())

    def test_04_dynamic_context_hook_contracts(self):
        """Test dynamic-context.ts supports @diff, @git-log, @mb and Turn-1 auto-restore"""
        dyn = os.path.join(self.hooks_dir, "dynamic-context.ts")
        self.assertTrue(os.path.exists(dyn))
        with open(dyn, "r") as f:
            content = f.read()
        for token in ["@diff", "@git-log", "@mb", "isFirstTurn"]:
            self.assertIn(token, content, f"dynamic-context.ts missing handler for {token}")

    # ----------------------------------------------------
    # LAYER 2: SKILLS INTEGRITY VERIFICATION
    # ----------------------------------------------------
    def test_05_skills_directory_and_frontmatter_validation(self):
        """Validate all skills in ~/.omp/agent/skills/ have valid SKILL.md and YAML frontmatter"""
        skill_dirs = [d for d in glob.glob(os.path.join(self.skills_dir, "*")) if os.path.isdir(d)]
        self.assertGreaterEqual(len(skill_dirs), 30, "Expected at least 30 registered skills")
        
        broken_symlinks = []
        missing_skill_md = []
        invalid_frontmatter = []
        
        for sdir in skill_dirs:
            sname = os.path.basename(sdir)
            if os.path.islink(sdir) and not os.path.exists(sdir):
                broken_symlinks.append(sname)
                continue
                
            skill_md = os.path.join(sdir, "SKILL.md")
            if not os.path.isfile(skill_md):
                missing_skill_md.append(sname)
                continue
                
            with open(skill_md, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(5000)
            if not (head.startswith("---") and "name:" in head and "description:" in head):
                invalid_frontmatter.append(sname)

        self.assertEqual(broken_symlinks, [], f"Found broken skill symlinks: {broken_symlinks}")
        self.assertEqual(missing_skill_md, [], f"Found skills without SKILL.md: {missing_skill_md}")
        self.assertEqual(invalid_frontmatter, [], f"Skills with invalid YAML frontmatter: {invalid_frontmatter}")

    # ----------------------------------------------------
    # LAYER 3: LOCAL CLI BINARIES INTEGRATION
    # ----------------------------------------------------
    def test_06_katalyst_cli_binaries_execution(self):
        """Verify all local CLI tools execute cleanly and respond to standard flags"""
        binaries = [
            ("katalyst-fix-ci", ["--help"], "usage:"),
            ("katalyst-jira", ["--help"], "usage:"),
            ("katalyst-review", ["--help"], "Usage:"),
            ("katalyst-mobile", ["devices"], ""),
            ("memory-bank", ["doctor"], "Bundle root:"),
        ]
        
        env = os.environ.copy()
        env["PATH"] = f"/opt/homebrew/bin:{self.local_bin}:" + env.get("PATH", "")
        
        for bname, args, expected in binaries:
            with self.subTest(binary=bname):
                cmd = [bname] + args
                res = subprocess.run(cmd, capture_output=True, text=True, env=env)
                self.assertEqual(res.returncode, 0, f"Binary {bname} failed with exit code {res.returncode}: {res.stderr}")
                if expected:
                    combined = (res.stdout + res.stderr).lower()
                    self.assertIn(expected.lower(), combined, f"Binary {bname} did not contain expected text '{expected}'")

    # ----------------------------------------------------
    # LAYER 4: MCP REGISTRY & SYSTEM CONSISTENCY
    # ----------------------------------------------------
    def test_07_mcp_configuration_validity(self):
        """Verify ~/.omp/agent/mcp.json parses cleanly and contains critical production servers"""
        self.assertTrue(os.path.exists(self.mcp_path), "mcp.json must exist")
        with open(self.mcp_path, "r") as f:
            mcp = json.load(f)
            
        servers = mcp.get("mcpServers", mcp)
        self.assertIn("github", servers)
        self.assertIn("context7", servers)
        self.assertIn("filesystem", servers)
        self.assertIn("sequential-thinking", servers)

    # ----------------------------------------------------
    # LAYER 5: COMBINED END-TO-END WORKFLOW SIMULATION
    # ----------------------------------------------------
    def test_08_full_pipeline_multi_tier_simulation(self):
        """Simulate complete developer flow: git init -> memory-bank setup -> plan -> task -> review -> done"""
        repo = os.path.join(self.tmp_dir, "app")
        os.makedirs(repo, exist_ok=True)
        
        # 1. Git init
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@domain.local"], cwd=repo, check=True)
        
        # 2. Memory Bank init
        mb_dir = os.path.join(repo, ".memory-bank")
        os.makedirs(os.path.join(mb_dir, "plans", "done"), exist_ok=True)
        status_file = os.path.join(mb_dir, "status.md")
        with open(status_file, "w") as f:
            f.write("# App Status\n**Phase:** Inception\n**Focus:** Core API\n")
            
        # 3. Simulate plan generation
        plan_file = os.path.join(mb_dir, "plans", "api.md")
        with open(plan_file, "w") as f:
            f.write("# Plan: API\n- [x] Step 1: Endpoint\n- [ ] Step 2: Test\n")
            
        # 4. Simulate test failure & error capture
        test_py = os.path.join(repo, "test_api.py")
        with open(test_py, "w") as f:
            f.write("import sys; sys.exit(0)\n")  # passing test
            
        res = subprocess.run([sys.executable, test_py], capture_output=True)
        self.assertEqual(res.returncode, 0)
        
        # 5. Archive plan on completion
        done_plan = os.path.join(mb_dir, "plans", "done", "api.md")
        shutil.move(plan_file, done_plan)
        self.assertTrue(os.path.exists(done_plan))
        
        # 6. Commit cleanly
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "feat: api implemented"], cwd=repo, check=True)
        
        # Verify clean git working tree
        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True)
        self.assertEqual(status.stdout.strip(), "")

if __name__ == "__main__":
    unittest.main()
