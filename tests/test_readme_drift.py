import json
import tempfile
import unittest
from pathlib import Path

from tools import check_readme_drift


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ReadmeDriftTests(unittest.TestCase):
    def test_current_readme_references_every_skill_directory(self):
        errors = check_readme_drift.check_readme_references_every_skill(check_readme_drift.ROOT)

        self.assertEqual([], errors)

    def test_current_readme_action_domain_references_match_public_action_docs(self):
        errors = check_readme_drift.check_readme_references_public_action_domains(check_readme_drift.ROOT)

        self.assertEqual([], errors)

    def test_current_readme_matches_plugin_metadata(self):
        errors = check_readme_drift.check_readme_matches_plugin_metadata(check_readme_drift.ROOT)

        self.assertEqual([], errors)

    def test_missing_skill_reference_is_reported(self):
        with minimal_repo() as root:
            write(root / "skills" / "missing-skill" / "SKILL.md", "---\nname: missing-skill\n---\n")

            errors = check_readme_drift.check_readme_references_every_skill(root)

        self.assertIn("README.md does not reference skill `missing-skill`", errors)

    def test_missing_action_domain_reference_is_reported(self):
        with minimal_repo() as root:
            write(root / "actions" / "milestones" / "README.md", "# Milestone actions\n")

            errors = check_readme_drift.check_readme_references_public_action_domains(root)

        self.assertIn("README.md does not link to actions/milestones/README.md", errors)

    def test_stale_action_domain_reference_is_reported(self):
        with minimal_repo(extra_readme="\n[Old domain](actions/old-domain/README.md)\n") as root:
            errors = check_readme_drift.check_readme_references_public_action_domains(root)

        self.assertIn("README.md links to unknown public action domain actions/old-domain/README.md", errors)

    def test_missing_plugin_install_target_is_reported(self):
        with minimal_repo(readme_install_target="wrong@tea-skills") as root:
            errors = check_readme_drift.check_readme_matches_plugin_metadata(root)

        self.assertIn("README.md should include Claude plugin install target `tea@tea-skills`", errors)


def minimal_repo(readme_install_target: str = "tea@tea-skills", extra_readme: str = ""):
    temp_dir = tempfile.TemporaryDirectory()
    root = Path(temp_dir.name)

    write(
        root / "README.md",
        f"""# tea-skills

`{readme_install_target}`

`example-skill`

[Issues](actions/issues/README.md)
{extra_readme}
""",
    )
    write(root / "skills" / "example-skill" / "SKILL.md", "---\nname: example-skill\n---\n")
    write(root / "actions" / "issues" / "README.md", "# Issue actions\n")
    write(root / ".claude-plugin" / "plugin.json", json.dumps({"name": "tea", "description": "desc"}))
    write(
        root / ".claude-plugin" / "marketplace.json",
        json.dumps({"name": "tea-skills", "description": "desc", "plugins": [{"name": "tea"}]}),
    )

    class RepoContext:
        def __enter__(self) -> Path:
            return root

        def __exit__(self, *args):
            temp_dir.cleanup()

    return RepoContext()


if __name__ == "__main__":
    unittest.main()
