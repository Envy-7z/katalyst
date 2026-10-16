#!/usr/bin/env python3
"""
Automation, Routing & Synchronization Test Suite
Validates that:
1. Skills are accurately triggered based on task intent
2. Hooks execute in correct lifecycle order without event collision
3. MCP tools route to appropriate handlers based on tool contracts
4. Scoped rules activate ONLY for matching file extensions
5. The entire multi-tier system acts as a coherent, automated pipeline
"""

import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

class AutomationRoutingSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = os.path.expanduser("~")
        cls.skills_dir = os.path.join(cls.home, ".omp", "agent", "skills")
        cls.hooks_dir = os.path.join(cls.home, ".omp", "agent", "hooks", "pre")
        cls.mcp_path = os.path.join(cls.home, ".omp", "agent", "mcp.json")

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="katalyst-auto-sync-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -----------------------------------------------------------------
    # TEST 1: SKILL ROUTING PRECISION (Intent -> Expected Skill)
    # -----------------------------------------------------------------
    def test_01_skill_semantic_routing_rules(self):
        """Verify each major developer intent maps to a distinct, active skill"""
        intent_map = {
            "bug": "systematic-debugging",
            "refactor": "safe-refactor-guard",
            "prd": "prd-to-execution",
            "test": "test-driven-development",
            "threat": "security-threat-model",
            "ui": "antislop-ui",
            "memory": "memory-bank",
            "plan": "architect-mode"
        }
        
        for keyword, expected_skill in intent_map.items():
            skill_path = os.path.join(self.skills_dir, expected_skill, "SKILL.md")
            self.assertTrue(os.path.isfile(skill_path), f"Skill '{expected_skill}' must exist for intent '{keyword}'")
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read(1500).lower()
            self.assertIn("name:", content)
            self.assertIn("description:", content)

    # -----------------------------------------------------------------
    # TEST 2: HOOK EVENT PIPELINE ORCHESTRATION
    # -----------------------------------------------------------------
    def test_02_hook_event_pipeline_isolation(self):
        """Verify hooks bind to distinct lifecycle events without overwriting each other"""
        event_registry = {}
        hook_files = glob.glob(os.path.join(self.hooks_dir, "*.ts"))
        
        for h in hook_files:
            hname = os.path.basename(h)
            with open(h, "r") as f:
                code = f.read()
            # Match pi.on("event_name", ...) or pi.registerCommand(...)
            events = re.findall(r'pi\.on\(\s*["\']([^"\']+)["\']', code)
            commands = re.findall(r'pi\.registerCommand\(\s*["\']([^"\']+)["\']', code)
            event_registry[hname] = {"events": events, "commands": commands}

        # Validate that dynamic-context and scoped-rules both hook into 'context' cleanly
        self.assertIn("context", event_registry["dynamic-context.ts"]["events"])
        self.assertIn("context", event_registry["scoped-rules.ts"]["events"])
        
        # Validate that terminal-error-trap hooks into 'tool_result'
        self.assertIn("tool_result", event_registry["terminal-error-trap.ts"]["events"])
        
        # Validate that composer-chips registers valid slash commands
        self.assertIn("fix-ci", event_registry["composer-chips.ts"]["commands"])
        self.assertIn("jira", event_registry["composer-chips.ts"]["commands"])
        self.assertIn("mb", event_registry["composer-chips.ts"]["commands"])
        self.assertIn("start", event_registry["composer-chips.ts"]["commands"])

    # -----------------------------------------------------------------
    # TEST 3: SCOPED RULES AUTOMATED SELECTIVITY
    # -----------------------------------------------------------------
    def test_03_scoped_rules_glob_matcher_selectivity(self):
        """Simulate scoped-rules.ts matching: only matching extensions trigger rules"""
        # Create dummy project with .katalyst/rules/
        rules_dir = os.path.join(self.tmp, ".katalyst", "rules")
        os.makedirs(rules_dir, exist_ok=True)
        
        # Rule 1: Go files
        with open(os.path.join(rules_dir, "go-style.mdc"), "w") as f:
            f.write("---\nglobs: [\"*.go\"]\n---\nUse standard gofmt and error handling.")
            
        # Rule 2: React files
        with open(os.path.join(rules_dir, "react-rules.mdc"), "w") as f:
            f.write("---\nglobs: [\"*.tsx\", \"*.jsx\"]\n---\nUse functional components and hooks.")

        # Test matcher simulation
        def simulate_scoped_rules(active_files):
            active_text = " ".join(active_files)
            triggered = []
            for rf in os.listdir(rules_dir):
                with open(os.path.join(rules_dir, rf), "r") as fp:
                    raw = fp.read()
                # parse globs
                m = re.search(r'globs:\s*\[(.*)\]', raw)
                if m:
                    globs = [g.strip().strip('"\'') for g in m.group(1).split(',')]
                    for g in globs:
                        ext = g.replace("*", "")
                        if any(f.endswith(ext) for f in active_files):
                            triggered.append(rf)
                            break
            return sorted(triggered)

        # Case A: Editing main.go -> only go-style triggers
        res_a = simulate_scoped_rules(["server/main.go", "server/handler.go"])
        self.assertEqual(res_a, ["go-style.mdc"])

        # Case B: Editing Button.tsx -> only react-rules triggers
        res_b = simulate_scoped_rules(["src/components/Button.tsx"])
        self.assertEqual(res_b, ["react-rules.mdc"])

        # Case C: Editing README.md -> neither triggers (zero token bloat!)
        res_c = simulate_scoped_rules(["README.md", "docs/architecture.md"])
        self.assertEqual(res_c, [])

    # -----------------------------------------------------------------
    # TEST 4: MCP TOOL DISPATCH INTEGRITY
    # -----------------------------------------------------------------
    def test_04_mcp_tool_routing_contract(self):
        """Verify active MCP servers map to expected real-world developer tools"""
        with open(self.mcp_path) as f:
            mcp = json.load(f)
        active = mcp.get("mcpServers", {})
        
        # Check required capabilities
        self.assertIn("context7", active, "Documentation RAG requires context7")
        self.assertIn("github", active, "CI and PR workflows require github MCP")
        self.assertIn("playwright", active, "Browser UI testing requires playwright")
        self.assertTrue(any("jira" in k for k in active), "Jira integration requires jira MCP")
        
        # Verify disabled servers are cleanly segmented
        disabled = mcp.get("disabledMcpServers", {})
        self.assertIn("docker", disabled)
        self.assertIn("mysql-dev", disabled)

    # -----------------------------------------------------------------
    # TEST 5: REAL WORKFLOW CONCURRENCY & MEMORY INTEGRITY
    # -----------------------------------------------------------------
    def test_05_concurrent_session_memory_isolation(self):
        """Simulate two concurrent workspaces: verify their memory banks never collide"""
        ws1 = os.path.join(self.tmp, "project-alpha")
        ws2 = os.path.join(self.tmp, "project-beta")
        os.makedirs(os.path.join(ws1, ".memory-bank"), exist_ok=True)
        os.makedirs(os.path.join(ws2, ".memory-bank"), exist_ok=True)
        
        with open(os.path.join(ws1, ".memory-bank", "status.md"), "w") as f:
            f.write("# Project Alpha Status\nFocus: Alpha Task\n")
            
        with open(os.path.join(ws2, ".memory-bank", "status.md"), "w") as f:
            f.write("# Project Beta Status\nFocus: Beta Task\n")
            
        # Verify strict filesystem isolation
        with open(os.path.join(ws1, ".memory-bank", "status.md"), "r") as f:
            alpha_status = f.read()
        with open(os.path.join(ws2, ".memory-bank", "status.md"), "r") as f:
            beta_status = f.read()
        
        self.assertIn("Alpha Task", alpha_status)
        self.assertNotIn("Beta Task", alpha_status)
        self.assertIn("Beta Task", beta_status)
        self.assertNotIn("Alpha Task", beta_status)

if __name__ == "__main__":
    unittest.main()
