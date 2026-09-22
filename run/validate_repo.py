#!/usr/bin/env python3
"""Validate the exported ARC APEX repository without executing Kaggle code.

Workflow diagram (Mermaid)
--------------------------
```mermaid
flowchart TD
    A["Load manifest"] --> B["Verify expected files"]
    B --> C["Compile every stage"]
    C --> D["Check diagrams and docs"]
    D --> E["Report success"]
```
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def without_leading_docstring(source: str) -> str:
    tree = ast.parse(source)
    if not tree.body:
        return source
    first = tree.body[0]
    if not (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return source
    return "".join(source.splitlines(keepends=True)[first.end_lineno:]).lstrip("\n")


def main() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    notebook_path = ROOT / "notebooks" / "arc-apex-4-18.ipynb"
    notebook_bytes = notebook_path.read_bytes()
    assert hashlib.sha256(notebook_bytes).hexdigest() == manifest["source_notebook_sha256"]
    notebook = json.loads(notebook_bytes)
    stages = manifest["stages"]
    assert len(stages) == 11, f"expected 11 stages, found {len(stages)}"
    for stage in stages:
        path = ROOT / stage["path"]
        assert path.is_file(), f"missing {path}"
        source = path.read_text(encoding="utf-8")
        original = "".join(notebook["cells"][stage["notebook_cell"]]["source"])
        assert hashlib.sha256(original.encode()).hexdigest() == stage["source_sha256"]
        assert without_leading_docstring(source).rstrip() == without_leading_docstring(original).rstrip(), (
            f"executable code drifted in {path}"
        )
        assert "Workflow diagram (Mermaid)" in source, f"missing workflow docs in {path}"
        assert "Purpose" in source and "Inputs" in source and "Outputs" in source
        compile(source, str(path), "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT, dont_inherit=True)
    print(f"Repository validation passed: {len(stages)} documented stages.")


if __name__ == "__main__":
    main()
