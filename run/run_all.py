#!/usr/bin/env python3
"""Execute every exported notebook stage in order.

The runner preserves notebook semantics by using one shared namespace. It compiles
stages with ``PyCF_ALLOW_TOP_LEVEL_AWAIT`` and awaits the benchmark stage when needed.

Workflow diagram (Mermaid)
--------------------------
```mermaid
flowchart TD
    A["Discover stage files"] --> B["Compile with top-level await"]
    B --> C["Execute in shared namespace"]
    C --> D{"Awaitable result?"}
    D -->|Yes| E["Await stage"]
    D -->|No| F["Continue"]
    E --> F
```
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import inspect
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STAGE_FILES = [
    "pipeline/01_environment_and_submission_mode.py",
    "pipeline/02_install_arc_runtime.py",
    "pipeline/03_locate_source_bundle.py",
    "pipeline/04_import_source_and_run_setup.py",
    "pipeline/05_load_benchmark.py",
    "pipeline/06a_validate_experiment_arm.py",
    "pipeline/06b_install_action7_patch.py",
    "pipeline/06c_install_phase_a_observer.py",
    "pipeline/07a_run_benchmark.py",
    "pipeline/07b_summarize_phase_a_diagnostics.py",
    "pipeline/08_show_diagnostics.py"
]


def compile_stage(path: Path):
    return compile(
        path.read_text(encoding="utf-8"),
        str(path),
        "exec",
        flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
        dont_inherit=True,
    )


async def run_pipeline() -> None:
    namespace = {
        "__name__": "__main__",
        "__package__": None,
    }
    for relative in STAGE_FILES:
        path = ROOT / relative
        print(f"[arc-apex] running {relative}", flush=True)
        namespace["__file__"] = str(path)
        result = eval(compile_stage(path), namespace, namespace)
        if inspect.isawaitable(result):
            await result


def validate() -> None:
    for relative in STAGE_FILES:
        compile_stage(ROOT / relative)
    print(f"Validated {len(STAGE_FILES)} pipeline stages.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compile stages without running Kaggle code.")
    parser.add_argument("--list", action="store_true", help="Print stages in execution order.")
    args = parser.parse_args()
    if args.list:
        print("\n".join(STAGE_FILES))
    elif args.check:
        validate()
    else:
        asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
