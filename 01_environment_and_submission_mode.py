"""Stage 01: Environment and submission mode.

Purpose
-------
Detect the Kaggle execution mode, select experiment arm A or B, configure vLLM tuning, set framework flags, and prepare CUDA and working-directory paths.

Inputs
------
Kaggle environment variables, mounted serving_setup.py, and the selected ARM constant.

Outputs
-------
TRUE_SUBMISSION, timing state, vLLM environment variables, and WORKING_DIR shared by later stages.

Workflow diagram (Mermaid)
--------------------------
```mermaid
flowchart TD
    N1["Read Kaggle mode"]
    N2["Validate ARM"]
    N3["Apply vLLM profile"]
    N4["Probe serving setup"]
    N5["Configure CUDA paths"]
    N1 --> N2
    N2 --> N3
    N3 --> N4
    N4 --> N5
```

Execution note
--------------
This is a notebook-derived pipeline stage. Run it through ``run_all.py`` so
every stage shares one namespace and notebook-style top-level ``await`` works.
"""

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

# ==========================================================================
# EXPERIMENT ARM -- this is the ONLY line you change between runs.
#   "A" = control. Identical serving config to the 6.16 baseline run.
#   "B" = MTP speculative decoding disabled.
ARM = "A"
# ==========================================================================

# True only inside a real competition rerun; switches diagnostics + soft deadline.
TRUE_SUBMISSION = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true"}
NOTEBOOK_START_EPOCH = time.time()

# Non-interactive matplotlib backend: diagnostics render plots with no display attached.
os.environ["MPLBACKEND"] = "Agg"
# Marks the run as a (real or emulated) submission so the framework + solver can adjust.
os.environ["TAAF_RUN_AS_SUBMISSION"] = "1" if TRUE_SUBMISSION else "0"
# Skip periodic JSON/HTML diagnostics and per-frame logging for every run.
os.environ["TAAF_MINIMAL_DIAGNOSTICS"] = "1"

if ARM not in {"A", "B"}:
    raise RuntimeError(f"ARM must be 'A' or 'B', got {ARM!r}")

_MTP_TOKENS = {"A": "3", "B": "0"}[ARM]

# Apply the measured vLLM winner before any serving setup command runs.
PUBLIC25_VLLM_PROFILE_NAME = {
    "A": "kv5-bf16-mtp3-c8-cg32",
    "B": "kv5-bf16-mtp0-c8-cg32",
}[ARM]
PUBLIC25_VLLM_PROFILE_ENV = {
    "TAAF_VLLM_ENABLE_PREFIX_CACHING": "0",
    "TAAF_VLLM_KV_CACHE_DTYPE": "auto",
    "TAAF_VLLM_KV_CACHE_MEMORY_BYTES": "5368709120",
    "TAAF_VLLM_MAX_CUDAGRAPH_CAPTURE_SIZE": "32",
    "TAAF_VLLM_MAX_NUM_BATCHED_TOKENS": "8192",
    "TAAF_VLLM_MAX_NUM_SEQS": "8",
    "TAAF_VLLM_MTP_TOKENS": _MTP_TOKENS,
    "TAAF_VLLM_OMP_THREADS": "1",
}
for key, value in PUBLIC25_VLLM_PROFILE_ENV.items():
    os.environ[key] = value

print(f"EXPERIMENT ARM={ARM}  requested MTP tokens={_MTP_TOKENS}", flush=True)
print(
    f'PUBLIC25_VLLM_PROFILE name={PUBLIC25_VLLM_PROFILE_NAME} '
    f'env={json.dumps(PUBLIC25_VLLM_PROFILE_ENV, sort_keys=True)}',
    flush=True,
)

# --- probe: show exactly how serving_setup.py reads TAAF_VLLM_MTP_TOKENS ---
# Read-only, costs a second, tells us whether "0" really means "off".
try:
    _setup_py = next(Path("/kaggle/input").rglob("serving_setup.py"))
    print(f"\nMTP_PROBE file={_setup_py}", flush=True)
    _hits = 0
    for _n, _line in enumerate(_setup_py.read_text(errors="replace").splitlines(), 1):
        if "MTP" in _line or "speculative" in _line.lower():
            print(f"  {_n:5}: {_line.strip()[:170]}")
            _hits += 1
    if _hits == 0:
        print("  (no MTP / speculative references found)")
except StopIteration:
    print("MTP_PROBE: serving_setup.py not found under /kaggle/input")
print("MTP_PROBE end\n", flush=True)
# ---------------------------------------------------------------------------

# Pin arc_agi's cached level_reset_only before its client is built (RESET keeps the level).
os.environ["ONLY_RESET_LEVELS"] = "true"

# Prepend the CUDA toolkit to the linker path (it is off it on Kaggle GPU images) so the
# solver's GPU libraries (e.g. vllm / torch) can link against libcuda.
cuda_library_path = "/usr/local/nvidia/lib64"
os.environ["LIBRARY_PATH"] = os.pathsep.join(
    entry for entry in [cuda_library_path, *os.environ.get("LIBRARY_PATH", "").split(os.pathsep)] if entry
)

# Everything the run produces is written here.
WORKING_DIR = Path("/kaggle/working")
WORKING_DIR.mkdir(parents=True, exist_ok=True)
print(f"taaf.kaggle: TRUE_SUBMISSION={TRUE_SUBMISSION}")
