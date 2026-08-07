# ============================================================
# Solver Customization & Extension Configuration
# ============================================================

# Overview:
# This module provides a customization layer for ARC APEX before
# benchmark execution begins. It allows optional modifications to
# the benchmark, game configurations, or solver behavior without
# affecting the original deployment package. Additional reasoning
# components and analysis modules can be integrated at this stage
# to extend the solver's capabilities.

# Purpose:
# Creates a safe extension point where experimental features,
# optimization modules, or custom solver enhancements can be
# enabled prior to execution. If any customization fails, the
# framework automatically falls back to the default solver to
# maintain uninterrupted execution.

# Workflow:
#
#      Benchmark Initialized
#               |
#               v
#    Load Optional Extensions
#               |
#               v
#   Apply Solver Enhancements
#               |
#               v
#   Verify Successful Integration
#               |
#      +--------+--------+
#      |                 |
#      v                 v
#  Success          Restore Default Solver
#      |                 |
#      +--------+--------+
#               |
#               v
#      Continue Benchmark Execution
#
# ============================================================


# Apply optional modifications to the benchmark or solver before
# execution begins. This stage is intended for experimental
# features and custom solver enhancements while preserving the
# original deployment behavior if an error occurs.

# Example:
# bm.label = f"{bm.label}-debug"

# Import and install the optional solver enhancement modules.
# These extensions introduce additional analysis, execution
# safeguards, and optimization layers while keeping the default
# solver available as a fallback.
try:
    from taaf_grafts.composite import install

    install(
        bm,
        flags={
            "efficiency": True,
            "retry_guard": True,
            "shortcircuit": True,
            "recovery": True,
        },
    )

# If any customization fails, continue execution using the
# original solver configuration without interrupting the run.
except Exception as exc:  # noqa: BLE001
    print(
        f"[taaf_grafts] cell-12 graft failed, running stock: {type(exc).__name__}: {exc}"
    )
