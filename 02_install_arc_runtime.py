"""Stage 02: Install the ARC runtime.

Purpose
-------
Install arc-agi from Kaggle's offline competition wheelhouse without contacting the internet.

Inputs
------
Python interpreter from stage 1 and the competition wheelhouse mounted under /kaggle/input.

Outputs
-------
An importable arc-agi runtime in the current notebook process.

Workflow diagram (Mermaid)
--------------------------
```mermaid
flowchart TD
    N1["Build pip command"]
    N2["Use offline wheelhouse"]
    N3["Install arc-agi"]
    N4["Surface failures"]
    N1 --> N2
    N2 --> N3
    N3 --> N4
```

Execution note
--------------
This is a notebook-derived pipeline stage. Run it through ``run_all.py`` so
every stage shares one namespace and notebook-style top-level ``await`` works.
"""

# Install the ARC runtime from the bundled competition wheels.
# Quiet: stdout is discarded; stderr (and a non-zero exit) still surface real failures.
subprocess.check_call(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--no-index",
        "--no-warn-conflicts",
        "--disable-pip-version-check",
        "--find-links",
        "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels",
        "arc-agi",
    ],
    stdout=subprocess.DEVNULL,
)
