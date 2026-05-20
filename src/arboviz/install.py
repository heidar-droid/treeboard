# src/arboviz/install.py
"""
Claude Code skill installer for arboviz.

Symlinks the packaged skill at src/arboviz/skills/arboviz into
~/.claude/skills/arboviz so Claude Code discovers it automatically.

Run via the entry point:
    arboviz-install

Or directly:
    python -m arboviz.install
"""
from __future__ import annotations

import pathlib
import sys


SKILLS_SRC = pathlib.Path(__file__).parent / "skills" / "arboviz"
CLAUDE_SKILLS = pathlib.Path.home() / ".claude" / "skills"
SKILL_LINK = CLAUDE_SKILLS / "arboviz"


def install_skill() -> None:
    """Create the symlink. Removes any existing link or directory first."""
    if not SKILLS_SRC.exists():
        print(
            f"arboviz: skill source not found at {SKILLS_SRC}",
            file=sys.stderr,
        )
        return

    CLAUDE_SKILLS.mkdir(parents=True, exist_ok=True)

    # Remove existing entry (broken symlink, real link, or directory)
    if SKILL_LINK.is_symlink() or SKILL_LINK.exists():
        try:
            SKILL_LINK.unlink()
        except IsADirectoryError:
            import shutil
            shutil.rmtree(SKILL_LINK)

    SKILL_LINK.symlink_to(SKILLS_SRC, target_is_directory=True)
    print(f"arboviz: Claude Code skill installed → {SKILL_LINK}")


def uninstall_skill() -> None:
    """Remove the symlink if it points at our skill."""
    if SKILL_LINK.is_symlink():
        try:
            if SKILL_LINK.resolve() == SKILLS_SRC.resolve():
                SKILL_LINK.unlink()
                print(f"arboviz: Claude Code skill removed from {SKILL_LINK}")
        except Exception:
            pass


if __name__ == "__main__":
    install_skill()
