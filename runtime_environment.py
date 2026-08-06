# ============================================================
# Runtime Environment Initialization & Submission Configuration
# ============================================================

# Overview:
# This module prepares the execution environment required for ARC APEX.
# It configures Kaggle execution settings, detects submission mode,
# enables GPU library access, manages diagnostics, and initializes
# the workspace required for storing outputs.

# Purpose:
# Acts as the foundation layer of ARC APEX by ensuring that the
# runtime environment is correctly configured before executing
# the reasoning and solving pipeline.

# Workflow:
#
#       Kaggle Execution Starts
#                |
#                v
#       Detect Submission Mode
#                |
#                v
#       Configure Runtime Flags
#                |
#                v
#       Enable CUDA/GPU Support
#                |
#                v
#       Initialize Workspace
#                |
#                v
#       Start ARC Reasoning Pipeline
#
# ============================================================


import json
import os
import pickle
import subprocess
import sys
import sysconfig
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen


# Check whether the current execution is running as an official Kaggle submission.
# Submission mode enables optimized execution settings.
TRUE_SUBMISSION = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true"}

# Record execution start time for runtime tracking.
NOTEBOOK_START_EPOCH = time.time()

# Configure matplotlib for non-interactive server execution.
os.environ["MPLBACKEND"] = "Agg"

# Set framework execution mode based on submission status.
os.environ["TAAF_RUN_AS_SUBMISSION"] = "1" if TRUE_SUBMISSION else "0"

# Reduce diagnostic generation during submission runs.
os.environ["TAAF_MINIMAL_DIAGNOSTICS"] = "1" if TRUE_SUBMISSION else "0"

# Configure ARC level reset behavior.
os.environ["ONLY_RESET_LEVELS"] = "true"

# Add CUDA libraries required for GPU-based AI dependencies.
cuda_library_path = "/usr/local/nvidia/lib64"

os.environ["LIBRARY_PATH"] = os.pathsep.join(
    entry for entry in [cuda_library_path, *os.environ.get("LIBRARY_PATH", "").split(os.pathsep)] if entry
)

# Create workspace directory for storing generated artifacts.
WORKING_DIR = Path("/kaggle/working")
WORKING_DIR.mkdir(parents=True, exist_ok=True)

# Display current execution mode.
print(f"taaf.kaggle: TRUE_SUBMISSION={TRUE_SUBMISSION}")
