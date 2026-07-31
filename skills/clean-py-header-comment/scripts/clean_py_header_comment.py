#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import io
import sys
import tokenize
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


def python_files(targets: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for target in targets:
        if target.is_file():
            if target.suffix == ".py":
                found.add(target)
            continue
        if not target.exists():
            raise FileNotFoundError(target)
        for path in target.rglob("*.py"):
            if not any(part in IGNORED_DIRS for part in path.parts):
                found.add(path)
    return sorted(found)


def remove_module_docstring(data: bytes, filename: str) -> tuple[bytes, bool]:
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    source = data.decode(encoding)
    tree = ast.parse(source, filename=filename)
    if not tree.body:
        return data, False

    node = tree.body[0]
    if not (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ):
        return data, False

    lines = source.splitlines(keepends=True)
    start_line = node.lineno - 1
    end_line = node.end_lineno - 1
    before = lines[start_line][: node.col_offset]
    after = lines[end_line][node.end_col_offset :]

    replacement = "" if not before.strip() and not after.strip() else before + after
    updated = "".join(lines[:start_line] + [replacement] + lines[end_line + 1 :])
    return updated.encode(encoding), True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find or remove the module docstring from Python files."
    )
    parser.add_argument("targets", nargs="+", type=Path, help="Python files or directories")
    parser.add_argument(
        "--write",
        action="store_true",
        help="write changes; without this flag, only list affected files",
    )
    args = parser.parse_args()

    try:
        files = python_files(args.targets)
    except FileNotFoundError as exc:
        parser.error(f"target does not exist: {exc}")

    affected = 0
    errors = 0
    for path in files:
        try:
            original = path.read_bytes()
            updated, changed = remove_module_docstring(original, str(path))
            if not changed:
                continue
            affected += 1
            print(path)
            if args.write:
                path.write_bytes(updated)
        except (OSError, SyntaxError, UnicodeError) as exc:
            errors += 1
            print(f"{path}: {exc}", file=sys.stderr)

    action = "updated" if args.write else "would update"
    print(f"{action}: {affected}; scanned: {len(files)}; errors: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
