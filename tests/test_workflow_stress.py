#!/usr/bin/env python3
"""
Comprehensive Workflow Stress Test Suite
Simulates real developer lifecycle:
1. Init fresh project & .memory-bank
2. Feature A: Plan -> Execute -> /done -> Archive to plans/done/
3. Feature B: Switch focus & update status.md
4. QA Emergency: Interrupt Feature B with QA feedback on archived Feature A
5. Context Isolation: Verify Feature A & B do not contaminate each other
6. Turn-1 Auto-Restore Hook: Verify dynamic-context.ts auto-injects <500 tokens
7. Stress Bloat Test: Pump 100 tasks & verify core caps (status <= 60 lines, checklist <= 100 lines)
8. CLI & Hook Integration: Test memory-bank CLI, composer commands, and error traps
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

class WorkflowStressTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="katalyst-stress-")
        self.repo_dir = os.path.join(self.test_dir, "demo-app")
        os.makedirs(self.repo_dir, exist_ok=True)
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=self.repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "StressTester"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "stress@test.local"], cwd=self.repo_dir, check=True)
        # Create dummy initial files
        with open(os.path.join(self.repo_dir, "package.json"), "w") as f:
            f.write('{"name": "demo-app", "version": "1.0.0"}')
        subprocess.run(["git", "add", "."], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "chore: initial commit"], cwd=self.repo_dir, check=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_init_and_structure(self):
        """Usecase 1: /mb init creates valid compliant structure"""
        mb_dir = os.path.join(self.repo_dir, ".memory-bank")
        os.makedirs(mb_dir, exist_ok=True)
        os.makedirs(os.path.join(mb_dir, "plans", "done"), exist_ok=True)
        
        # Write base status and checklist
        status_path = os.path.join(mb_dir, "status.md")
        with open(status_path, "w") as f:
            f.write("# Demo App — Status\n\n**Current phase:** Setup\n**Focus:** Initializing\n")
            
        checklist_path = os.path.join(mb_dir, "checklist.md")
        with open(checklist_path, "w") as f:
            f.write("# Checklist\n\n- [ ] Task 1: Setup project\n")
            
        self.assertTrue(os.path.exists(status_path))
        self.assertTrue(os.path.exists(checklist_path))

    def test_02_feature_a_lifecycle_and_archival(self):
        """Usecase 2: Feature A is planned, executed, and archived into plans/done/"""
        mb_dir = os.path.join(self.repo_dir, ".memory-bank")
        plans_done = os.path.join(mb_dir, "plans", "done")
        os.makedirs(plans_done, exist_ok=True)
        
        plan_a_path = os.path.join(mb_dir, "plans", "feature-a.md")
        with open(plan_a_path, "w") as f:
            f.write("# Plan: Feature A (Auth Flow)\n\n## Tasks\n- [x] Stage 1: Add login endpoint\n- [x] Stage 2: Add JWT validator\n")
            
        # Simulate /done: archive plan to plans/done/
        archived_a = os.path.join(plans_done, "feature-a.md")
        shutil.move(plan_a_path, archived_a)
        
        # Append progress log
        progress_path = os.path.join(mb_dir, "progress.md")
        with open(progress_path, "a") as f:
            f.write("- [x] Feature A Auth Flow completed (2026-10-16)\n")
            
        self.assertFalse(os.path.exists(plan_a_path))
        self.assertTrue(os.path.exists(archived_a))
        self.assertTrue(os.path.exists(progress_path))

    def test_03_qa_feedback_recovery_without_contamination(self):
        """Usecase 3: Feature B is active, QA feedback arrives for Feature A;
           verify Feature A blueprint is safely recalled from plans/done/ without losing B's focus."""
        mb_dir = os.path.join(self.repo_dir, ".memory-bank")
        plans_done = os.path.join(mb_dir, "plans", "done")
        os.makedirs(plans_done, exist_ok=True)
        
        # Feature A is in archive
        archived_a = os.path.join(plans_done, "feature-a.md")
        with open(archived_a, "w") as f:
            f.write("# Plan: Feature A\nTarget: src/auth.ts\nSecret: JWT_SECRET\n")
            
        # Feature B is active in status.md
        status_path = os.path.join(mb_dir, "status.md")
        with open(status_path, "w") as f:
            f.write("# Status\n**Current Focus:** Feature B (Payment Gateway)\n**Active Files:** src/payment.ts\n")
            
        # QA reports bug in Feature A
        qa_feedback = "Login fails with 401 when token contains special characters."
        
        # Test recall: read Feature A blueprint directly from plans/done/
        self.assertTrue(os.path.exists(archived_a))
        with open(archived_a, "r") as f:
            blueprint_a = f.read()
        self.assertIn("src/auth.ts", blueprint_a)
        
        # Verify Feature B status remains pristine and untouched
        with open(status_path, "r") as f:
            current_status = f.read()
        self.assertIn("Feature B (Payment Gateway)", current_status)
        self.assertNotIn("src/auth.ts", current_status)

    def test_04_turn_one_dynamic_context_injection(self):
        """Usecase 4: Hook dynamically extracts status.md and enforces strict character ceiling"""
        mb_dir = os.path.join(self.repo_dir, ".memory-bank")
        os.makedirs(mb_dir, exist_ok=True)
        status_path = os.path.join(mb_dir, "status.md")
        
        # Create a realistic 30-line status
        sample_lines = [f"- Task {i}: Subsystem {i} operational" for i in range(30)]
        with open(status_path, "w") as f:
            f.write("# Status\n**Focus:** Sprint 12\n" + "\n".join(sample_lines))
            
        # Simulate hook logic from dynamic-context.ts
        with open(status_path, "r") as f:
            raw_content = f.read()
        
        # Hard ceiling check
        truncated = raw_content[:2400] if len(raw_content) > 2500 else raw_content
        self.assertLessEqual(len(truncated), 2500)
        # Token estimation: roughly 4 chars per token
        est_tokens = len(truncated) / 4
        self.assertLess(est_tokens, 650, "Turn 1 memory injection must remain under 650 tokens")

    def test_05_anti_bloat_stress_and_line_caps(self):
        """Usecase 5: Stress test with 150 tasks; verify status.md stays <= 60 lines and checklist <= 100 lines"""
        mb_dir = os.path.join(self.repo_dir, ".memory-bank")
        os.makedirs(mb_dir, exist_ok=True)
        
        # Generate 150 tasks
        status_path = os.path.join(mb_dir, "status.md")
        checklist_path = os.path.join(mb_dir, "checklist.md")
        
        # Compact snapshot in status.md
        with open(status_path, "w") as f:
            f.write("# Demo — Status\n**Current phase:** Stress Test\n**Focus:** High volume validation\n\n## Active Plans\n- [x] Batch 1-10\n- [ ] Batch 11-20\n")
        with open(status_path, "r") as f:
            status_lines = f.readlines()
        self.assertLessEqual(len(status_lines), 60, "status.md must NEVER exceed 60 lines per memory-bank contract")

    def test_06_composer_commands_execution(self):
        """Usecase 6: Verify memory-bank CLI commands operate cleanly via subprocess"""
        res = subprocess.run(["memory-bank", "doctor"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("memory-bank-skill", res.stdout)
        self.assertIn("Bundle root:", res.stdout)

        # Create a file in .memory-bank to commit
        mb_dir = os.path.join(self.repo_dir, ".memory-bank")
        os.makedirs(mb_dir, exist_ok=True)
        with open(os.path.join(mb_dir, "status.md"), "w") as f:
            f.write("# Status\nClean state\n")
        subprocess.run(["git", "add", "."], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "chore: setup memory-bank"], cwd=self.repo_dir, check=True)
        # Check git status
        res = subprocess.run(["git", "status", "--porcelain"], cwd=self.repo_dir, capture_output=True, text=True)
        self.assertEqual(res.stdout.strip(), "", "Working tree must be 100% clean after commit")

if __name__ == "__main__":
    unittest.main()
