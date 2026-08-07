# ============================================================
# ARC Runtime Installation & Dependency Configuration
# ============================================================

# Overview:
# This module installs the ARC runtime package required by ARC APEX.
# Since the Kaggle competition environment does not provide internet
# access during execution, all required dependencies are installed
# from the offline wheel packages supplied with the competition dataset.

# Purpose:
# Ensures that the ARC APEX framework has access to the official
# ARC runtime before loading datasets, initializing the solving
# pipeline, and executing reasoning tasks.

# Workflow:
#
#      Start Runtime Setup
#              |
#              v
#    Locate Offline Wheel Packages
#              |
#              v
#     Install ARC Runtime Package
#              |
#              v
#   Verify Successful Installation
#              |
#              v
#   Continue ARC APEX Initialization
#
# ============================================================


# Install the official ARC runtime package from the bundled offline wheel repository.
# Standard output is suppressed to keep execution logs clean, while installation
# errors remain visible if the process encounters any issues.
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
