from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_root_skill_packages_repository_for_npx_skills_install():
    root_skill = ROOT / "SKILL.md"

    assert root_skill.exists(), "root SKILL.md makes npx skills install the whole tea-skills package"
    text = root_skill.read_text(encoding="utf-8")
    assert "name: tea-skills" in text
    assert "disable-model-invocation: true" in text
    assert "~/.agents/skills/tea-skills" in text

    required_payload = [
        "skills/issue-dependencies/SKILL.md",
        "skills/issue-moderation/SKILL.md",
        "skills/pull-request-forks.md",
        "actions/issues/dependency-add.py",
        "actions/issues/lock.py",
        "actions/internal/tea_api.py",
        "actions/pull-requests/find-by-branch.py",
        "actions/milestones/edit.py",
        "actions/org-labels/list.py",
    ]
    for relative in required_payload:
        assert (ROOT / relative).exists(), f"root package payload includes {relative}"


def test_readme_recommends_namespaced_universal_npx_install():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "npx skills add deevus/tea-skills --skill '*' --agent universal" in readme
    assert "~/.agents/skills/tea-skills" in readme
    assert "--agent pi" not in readme


def test_action_skills_explain_package_root_resolution():
    action_skill_paths = [
        "skills/issue-comments/SKILL.md",
        "skills/issue-dependencies/SKILL.md",
        "skills/issue-moderation/SKILL.md",
        "skills/create-pull/SKILL.md",
        "skills/review-pull/SKILL.md",
        "skills/merge-pull/SKILL.md",
        "skills/milestones/SKILL.md",
        "skills/label-schemes/SKILL.md",
    ]

    for relative in action_skill_paths:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "tea-skills package root" in text, f"{relative} explains where bundled actions live"
