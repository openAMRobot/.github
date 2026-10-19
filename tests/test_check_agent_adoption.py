"""Tests for rollout/repositories.yaml agent-rules adoption metadata."""

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_agent_adoption as aa  # noqa: E402


class Adoption(unittest.TestCase):
    def write(self, data):
        path = Path(self.tmp.name, "repositories.yaml")
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return path

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_required_missing_agents_is_a_finding(self):
        data = {"organization": "openAMRobot", "repositories": [
            {"name": "demo", "default_branch": "main", "agent_rules": "required"},
        ]}
        policy = aa.entry_for(self.write(data), "demo")
        root = Path(self.tmp.name, "repo")
        root.mkdir()
        findings = aa.missing_findings(root, policy)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["group"], "agent-rules")
        self.assertEqual(findings[0]["found"], "file is missing")

    def test_exempt_missing_agents_is_not_a_finding(self):
        data = {"organization": "openAMRobot", "repositories": [
            {"name": "release", "default_branch": "main", "agent_rules": "exempt",
             "agent_rules_reason": "release process owns this boundary"},
        ]}
        policy = aa.entry_for(self.write(data), "release")
        root = Path(self.tmp.name, "repo")
        root.mkdir()
        self.assertEqual(aa.missing_findings(root, policy), [])
        self.assertEqual(aa.policy_status(root, policy), {
            "status": "exempt", "reason": "release process owns this boundary",
        })

    def test_exempt_requires_reason(self):
        data = {"organization": "openAMRobot", "repositories": [
            {"name": "release", "default_branch": "main", "agent_rules": "exempt"},
        ]}
        with self.assertRaisesRegex(ValueError, "agent_rules_reason"):
            aa.validate_document(data)

    def test_unknown_status_is_rejected(self):
        data = {"organization": "openAMRobot", "repositories": [
            {"name": "demo", "default_branch": "main", "agent_rules": "optional"},
        ]}
        with self.assertRaisesRegex(ValueError, "required or exempt"):
            aa.validate_document(data)

    def test_missing_status_is_rejected(self):
        data = {"organization": "openAMRobot", "repositories": [
            {"name": "demo", "default_branch": "main"},
        ]}
        with self.assertRaisesRegex(ValueError, "required or exempt"):
            aa.validate_document(data)


if __name__ == "__main__":
    unittest.main()
