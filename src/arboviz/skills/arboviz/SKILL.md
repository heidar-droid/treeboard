---
name: arboviz
vendor: io.arboviz
description: Visual cockpit for Claude Code. Shows a spatial canvas of which files you are touching during a task — where they live in the project, which phase (reading, editing, creating, deleting). Call the CLI commands below during every task that touches files. If arboviz is not running, commands exit silently — never let arboviz block your work.
---

## arboviz Integration

Call these Bash commands at the exact moments described. Use the Bash tool for each call. Do not batch them into scripts.

### Before starting any task that modifies or reads project files

```bash
arboviz snapshot
```

### Each time you use the Read tool on a file

```bash
arboviz read <relative_path_from_project_root>
```

### Each time you use the Write or Edit tool

```bash
arboviz edit <relative_path_from_project_root>
```

### When you create a file that did not exist before

```bash
arboviz create <relative_path_from_project_root>
```

### When you delete a file

```bash
arboviz delete <relative_path_from_project_root>
```

### When the task is complete

```bash
arboviz task-end "<short description, e.g. auth refactor>"
```

## Rules

- If any arboviz command fails, ignore the error and continue
- Never wait for arboviz output before proceeding
- Paths MUST be relative to the project root. Never use absolute paths (paths starting with `/`). Example: `src/auth.py`, never `/Users/smb/myapp/src/auth.py`.
- The display name for these calls in the tool log is: **arboviz**
