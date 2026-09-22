"""Stage 08: Show diagnostics.

Purpose
-------
Document that HTML rendering is intentionally skipped because minimal diagnostics are enabled.

Inputs
------
The minimal-diagnostics policy established in stage 1.

Outputs
-------
No additional runtime output; existing JSON and audit artifacts remain the canonical diagnostics.

Workflow diagram (Mermaid)
--------------------------
```mermaid
flowchart TD
    N1["Confirm minimal mode"]
    N2["Skip HTML rendering"]
    N3["Keep audit artifacts"]
    N1 --> N2
    N2 --> N3
```

Execution note
--------------
This is a notebook-derived pipeline stage. Run it through ``run_all.py`` so
every stage shares one namespace and notebook-style top-level ``await`` works.
"""

# Minimal diagnostics are enabled; skip post-run HTML rendering.
