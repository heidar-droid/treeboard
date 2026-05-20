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

    # Remove existing entry — but only after confirming it's safe.
    if SKILL_LINK.is_symlink():
        # Symlinks are cheap to replace; just unlink and re-create below.
        try:
            SKILL_LINK.unlink()
        except OSError:
            pass
    elif SKILL_LINK.exists() and SKILL_LINK.is_dir():
        # Real directory at the destination — could be a user-authored skill.
        # Read its SKILL.md frontmatter to verify it's actually ours before
        # rmtree'ing anything.
        existing_skill_md = SKILL_LINK / "SKILL.md"
        has_name = False
        has_vendor = False
        if existing_skill_md.is_file():
            try:
                text = existing_skill_md.read_text(encoding="utf-8")
                # Tiny inline frontmatter parse — avoid pulling in PyYAML for two fields.
                if text.startswith("---"):
                    end = text.find("---", 3)
                    if end != -1:
                        for line in text[3:end].splitlines():
                            line = line.strip()
                            if line.startswith("name:"):
                                if line.split(":", 1)[1].strip().strip("'\"") == "arboviz":
                                    has_name = True
                            elif line.startswith("vendor:"):
                                if line.split(":", 1)[1].strip().strip("'\"") == "io.arboviz":
                                    has_vendor = True
            except OSError:
                pass
        is_arboviz = has_name and has_vendor

        if not is_arboviz:
            print(
                f"arboviz: {SKILL_LINK}/ exists as a directory with non-arboviz "
                "content. Refusing to overwrite. Please remove it manually if "
                "you want to install the bundled skill.",
                file=sys.stderr,
            )
            return

        import shutil
        shutil.rmtree(SKILL_LINK)
    elif SKILL_LINK.exists():
        # Regular file at the destination — also unsafe to silently delete.
        print(
            f"arboviz: {SKILL_LINK} exists and is not a directory. "
            "Refusing to overwrite. Remove it manually to install the skill.",
            file=sys.stderr,
        )
        return

    SKILL_LINK.symlink_to(SKILLS_SRC, target_is_directory=True)
    print(f"arboviz: Claude Code skill installed → {SKILL_LINK}")


def refresh_skill_if_stale() -> None:
    """Repair the symlink if it points to a path that no longer exists.

    After `pip install -U arboviz` the site-packages directory may move and
    the previously-installed symlink becomes dangling. Silent best-effort —
    never raise; never log; arboviz must not break Claude Code's startup.
    """
    try:
        if not SKILL_LINK.is_symlink():
            return
        target = SKILL_LINK.resolve(strict=False)
        if target.exists():
            return
        SKILL_LINK.unlink()
        if SKILLS_SRC.exists():
            CLAUDE_SKILLS.mkdir(parents=True, exist_ok=True)
            SKILL_LINK.symlink_to(SKILLS_SRC, target_is_directory=True)
    except Exception:
        pass


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
