---
name: clean-py-header-comment
description: Safely find and remove file-level header docstrings from Python source files while preserving function and class docstrings, shebangs, encoding declarations, and ordinary comments. Use when asked to clean Python file headers, remove module descriptions or module docstrings, or batch-delete opening triple-quoted comments from .py files.
---

# Clean Python Header Comment

Remove only the module docstring: the string literal that is the first Python
statement in a module. Do not remove function, class, or other string literals.

## Workflow

1. Resolve the requested directory. If its name appears mistyped, prefer the
   current workspace when it is an obvious match and state the assumption.
2. Preview affected files:

   ```bash
   python3 <skill-dir>/scripts/clean_py_header_comment.py <target>
   ```

3. Apply the removal:

   ```bash
   python3 <skill-dir>/scripts/clean_py_header_comment.py --write <target>
   ```

4. Inspect `git diff -- '*.py'` when the target is a Git worktree.
5. Run the script again in preview mode. A clean result must report no Python
   files with module docstrings.

The script parses each file with Python's AST, preserves its detected source
encoding and newline bytes, and skips non-docstring headers. If any file cannot
be parsed or decoded, stop and report the file instead of attempting a regex
fallback.

## Scope

- Accept a Python file or directory; search directories recursively.
- Ignore common generated and environment directories.
- Use `--write` only when the user asked to change files.
- Preserve unrelated working-tree changes.
