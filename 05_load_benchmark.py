"""Stage 05: Load the benchmark.

Purpose
-------
Restore the serialized deployment target and benchmark, stamp the true submission state, and redirect output to Kaggle's writable directory.

Inputs
------
deploy_target.pkl, benchmark_initial.pkl, TRUE_SUBMISSION, and WORKING_DIR.

Outputs
-------
Configured target and bm objects for customization and execution.

Workflow diagram (Mermaid)
--------------------------
```mermaid
flowchart TD
    N1["Load deployment target"]
    N2["Set submission flags"]
    N3["Load benchmark"]
    N4["Set output directory"]
    N1 --> N2
    N2 --> N3
    N3 --> N4
```

Execution note
--------------
This is a notebook-derived pipeline stage. Run it through ``run_all.py`` so
every stage shares one namespace and notebook-style top-level ``await`` works.
"""

# Restore the deployment target and record the real submission state on it.
with open(BUNDLE_DIR / "deploy_target.pkl", "rb") as file:
    target = pickle.load(file)
target.actual_run_as_submission = TRUE_SUBMISSION
target.is_competition_rerun = TRUE_SUBMISSION

# Restore the benchmark and point its outputs at the Kaggle working dir.
with open(BUNDLE_DIR / "benchmark_initial.pkl", "rb") as file:
    bm = pickle.load(file)
bm.job_dir = WORKING_DIR
