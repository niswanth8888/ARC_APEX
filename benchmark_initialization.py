# ============================================================
# Benchmark & Deployment Target Initialization
# ============================================================

# Overview:
# This module restores the serialized deployment target and
# benchmark objects required for ARC APEX execution. It applies
# the current execution mode to the deployment target and
# configures the benchmark to store all generated outputs within
# the Kaggle working directory.

# Purpose:
# Initializes the benchmark environment by loading the prepared
# runtime objects, synchronizing submission settings, and
# preparing the benchmark workspace before the reasoning engine
# begins processing ARC tasks.

# Workflow:
#
#      Load Deployment Target
#                |
#                v
#     Apply Execution Settings
#                |
#                v
#       Restore Benchmark
#                |
#                v
#   Configure Output Directory
#                |
#                v
#     Benchmark Ready for Execution
#
# ============================================================


# Load the deployment target and update it with the current
# execution mode for the active runtime.
with open(BUNDLE_DIR / "deploy_target.pkl", "rb") as file:
    target = pickle.load(file)

target.actual_run_as_submission = TRUE_SUBMISSION
target.is_competition_rerun = TRUE_SUBMISSION


# Load the benchmark configuration and assign the working
# directory where all outputs and generated files will be stored.
with open(BUNDLE_DIR / "benchmark_initial.pkl", "rb") as file:
    bm = pickle.load(file)

bm.job_dir = WORKING_DIR
