"""Structural tests for issue forms, agent prompts and harness text files."""
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FORMS = ROOT / ".github" / "ISSUE_TEMPLATE"
PROMPTS = ROOT / "agent-prompts"
# Files written for the harness; plain typography is a rule for them.
HARNESS_FILES = [
    "AGENTS.md", "agent-rules/SHARED_RULES.md", "CONTRIBUTING.md", "decisions.yaml",
    "maintainers.yaml", "public-extract-allowlist.yaml", "agent-runs.md",
    ".github/PULL_REQUEST_TEMPLATE.md", *[f"agent-prompts/{p.name}" for p in PROMPTS.glob("*.md")],
    *[str(p.relative_to(ROOT)) for p in (ROOT / "rollout").rglob("*") if p.is_file()],
    *[str(p.relative_to(ROOT)) for p in (ROOT / "tools").glob("*.py")],
]


class IssueForms(unittest.TestCase):
    def load(self, name):
        return yaml.safe_load((FORMS / name).read_text(encoding="utf-8"))

    def test_every_form_is_valid(self):
        for path in FORMS.glob("*.yml"):
            if path.name == "config.yml":
                continue
            with self.subTest(form=path.name):
                form = self.load(path.name)
                self.assertTrue(form["name"] and form["description"] and form["body"])
                ids = [item["id"] for item in form["body"] if "id" in item]
                self.assertEqual(len(ids), len(set(ids)))

    def test_labels_used_by_automation(self):
        self.assertIn("harness", self.load("harness_mistake.yml")["labels"])
        self.assertIn("good first issue", self.load("good_first_issue.yml")["labels"])
        self.assertIn("contract-change", self.load("contract_change_request.yml")["labels"])

    def test_bug_report_asks_for_sha_and_commands(self):
        ids = {item.get("id") for item in self.load("bug_report.yml")["body"]}
        self.assertTrue({"repository", "commit", "reproduce", "not_verified"} <= ids)


class AgentPrompts(unittest.TestCase):
    def test_each_prompt_has_the_three_fixed_parts(self):
        prompts = [p for p in PROMPTS.glob("*.md") if p.name != "README.md"]
        self.assertEqual(sorted(p.name for p in prompts),
                         ["docs-fix.md", "evaluator-pass.md", "push-from-bundle.md", "read-only-audit.md"])
        for path in prompts:
            text = path.read_text(encoding="utf-8")
            with self.subTest(prompt=path.name):
                for heading in ("## Precondition block", "## Expected outcome", "## Failure rule"):
                    self.assertIn(heading, text)
                block = text.split("## Precondition block", 1)[1].split("```")[1]
                self.assertIn("repository:", block)
                self.assertRegex(block, r"(parent|head) SHA:")
                self.assertIn("expected outcome:", block)
                self.assertIn("A failed precondition stops the task", text)

    def test_docs_fix_separates_verified_from_planned_content(self):
        text = (PROMPTS / "docs-fix.md").read_text(encoding="utf-8")
        self.assertIn("## Verified and planned content", text)
        self.assertIn("<repository>@<SHA>:<file>:<line>", text.split("## Verified and planned content", 1)[1])
        self.assertIn("**Planned** or **Experimental**", text)
        self.assertIn("Never invent a technical claim the owning repository does not support", text)


class Typography(unittest.TestCase):
    def test_no_em_or_en_dashes_in_harness_files(self):
        for rel in HARNESS_FILES:
            path = ROOT / rel
            if path.exists():
                with self.subTest(file=rel):
                    self.assertNotRegex(path.read_text(encoding="utf-8"), "[–—]")


if __name__ == "__main__":
    unittest.main()
