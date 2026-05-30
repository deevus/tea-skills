from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ACTION_SKILLS = [
    "issue-comments",
    "issue-dependencies",
    "issue-moderation",
    "create-pull",
    "review-pull",
    "merge-pull",
    "milestones",
    "label-schemes",
]

FORK_REFERENCE_SKILLS = ["list-pulls", "review-pull"]


def test_repository_root_is_not_a_skill_that_shadows_nested_skills():
    assert not (ROOT / "SKILL.md").exists()


def test_action_using_skills_bundle_actions_as_symlinked_skill_resources():
    for skill_name in ACTION_SKILLS:
        actions_link = ROOT / "skills" / skill_name / "actions"
        assert actions_link.is_symlink(), f"skills/{skill_name}/actions should symlink to ../../actions"
        assert actions_link.resolve() == (ROOT / "actions").resolve()

        skill_text = (ROOT / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "relative to this skill directory" in skill_text
        assert "tea-skills package root" not in skill_text


def test_pull_request_fork_reference_is_bundled_with_skills_that_link_to_it():
    for skill_name in FORK_REFERENCE_SKILLS:
        reference_link = ROOT / "skills" / skill_name / "pull-request-forks.md"
        assert reference_link.is_symlink(), f"skills/{skill_name}/pull-request-forks.md should be bundled"
        assert reference_link.resolve() == (ROOT / "skills" / "pull-request-forks.md").resolve()

        skill_text = (ROOT / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "[pull-request-forks](pull-request-forks.md)" in skill_text


def test_readme_recommends_normal_all_skill_npx_install():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "npx skills add deevus/tea-skills --skill '*'" in readme
    assert "--agent universal" in readme
    assert "~/.agents/skills/tea-skills" not in readme
    assert "tea-skills/skills/<name>/SKILL.md" not in readme
