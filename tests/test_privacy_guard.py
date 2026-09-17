import unittest
import subprocess
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestPrivacyGuard(unittest.TestCase):
    """Enforces zero-leak invariant for all git-tracked files in Katalyst."""

    SECRET_PATTERNS = {
        "google_oauth": re.compile(r"ya29\.[a-zA-Z0-9_-]{20,}"),
        "jwt_token": re.compile(r"eyJ[a-zA-Z0-9_-]{15,}\.eyJ[a-zA-Z0-9_-]{15,}\.[a-zA-Z0-9_-]{15,}"),
        "openai_key": re.compile(r"sk-(proj-)?[a-zA-Z0-9_-]{32,}"),
        "anthropic_key": re.compile(r"sk-ant-[a-zA-Z0-9_-]{32,}"),
        "google_api_key": re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"),
        "github_pat": re.compile(r"gh[pousr]_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}"),
        "gitlab_pat": re.compile(r"glpat-[a-zA-Z0-9_-]{20,}"),
        "slack_token": re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"),
        "aws_access_key": re.compile(r"(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
        "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    }

    FORBIDDEN_KEYWORDS = [
        "genie" + "book",
        "trip" + "fez",
        "ma" + "hara",
        "nex" + "tera",
        "re" + "moot",
        "mota" + "pos",
        "bub" + "bly",
        "/" + "Users/" + "wisnu",
    ]
    def test_audit_privacy_script_passes(self):
        script = os.path.join(ROOT, "scripts", "audit-privacy.sh")
        result = subprocess.run(["bash", script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"audit-privacy.sh failed:\n{result.stdout}\n{result.stderr}")

    def test_no_secrets_in_tracked_files(self):
        tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
        violations = []

        for rel_path in tracked:
            if rel_path.endswith(('.png', '.icns', '.jpg', '.wasm', '.tar', '.gz', '.zip')) or rel_path == 'scripts/pre-commit':
                continue
            full_path = os.path.join(ROOT, rel_path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    for lno, line in enumerate(f, 1):
                        for name, pat in self.SECRET_PATTERNS.items():
                            m = pat.search(line)
                            if m:
                                match_str = m.group(0)
                                if "..." in match_str or "xxx" in match_str.lower() or "example" in match_str.lower():
                                    continue
                                violations.append(f"{rel_path}:{lno} matched secret pattern {name}: {match_str[:25]}")
                        
                        for kw in self.FORBIDDEN_KEYWORDS:
                            if kw in line.lower():
                                violations.append(f"{rel_path}:{lno} contained forbidden keyword: '{kw}'")
            except Exception as e:
                violations.append(f"Could not read {rel_path}: {e}")

        self.assertEqual(violations, [], f"Privacy guard violations detected:\n" + "\n".join(violations))

if __name__ == "__main__":
    unittest.main()
