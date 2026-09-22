"""Stage 06b: Install the ACTION7 patch.

Purpose
-------
Verify analyzer configuration and safely install the ACTION7 behavior patch with source fingerprints and repeat-install protection.

Inputs
------
Analyzer environment variables and the bundled inference.agent implementation.

Outputs
-------
Validated ACTION7 configuration and patched analyzer behavior for the benchmark run.

Workflow diagram (Mermaid)
--------------------------
```mermaid
flowchart TD
    N1["Read typed settings"]
    N2["Import analyzer"]
    N3["Verify frozen values"]
    N4["Fingerprint target source"]
    N5["Install patch"]
    N1 --> N2
    N2 --> N3
    N3 --> N4
    N4 --> N5
```

Original notebook note
----------------------
Kaggle cell: validate analyzer configuration, then install ACTION7 safely.

Place this cell immediately after the notebook's complete ARM_GATE /
RESOLVED_KNOBS cell and before the Phase A observer cell.  The ARM_GATE may
already have imported ``inference.agent``; that is accepted only when the
frozen module constants exactly match the intended environment.

Execution note
--------------
This is a notebook-derived pipeline stage. Run it through ``run_all.py`` so
every stage shares one namespace and notebook-style top-level ``await`` works.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import os
import sys
from pathlib import Path


EXPECTED_HISTORICAL_ACTION_NAMES_SHA256 = (
    "d359c22dd9f3925ed54cb05a60640e8aa1121c226a068b4736e8dfad46d2d115"
)

EXPECTED_SOURCE_ROOT = Path(
    "/kaggle/input/duck-qwen38-nvfp4-mtp-vllm-smoke-v1/src/ARC3-Inference"
)


def _read_int(name: str) -> int:
    raw = os.environ.get(name)
    if raw is None:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer environment value: {name}={raw!r}") from exc


def _read_float(name: str) -> float:
    raw = os.environ.get(name)
    if raw is None:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid numeric environment value: {name}={raw!r}") from exc


def _read_bool(name: str) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"Invalid Boolean environment value: {name}={raw!r}")


def _read_seed(name: str) -> int:
    """Match tool_agent semantics: an unset seed resolves to -1 (no seed)."""
    raw = os.environ.get(name)
    if raw is None:
        return -1
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer environment value: {name}={raw!r}") from exc


expected_environment = {
    "LOCAL_ANALYZER_MAX_OUTPUT": (_read_int, 0),
    "LOCAL_ANALYZER_CONTEXT_WINDOW": (_read_int, 32768),
    "LOCAL_ANALYZER_TOOL_STEPS": (_read_int, 0),
    "LOCAL_ANALYZER_TOOL_TIMEOUT": (_read_int, 30),
    "LOCAL_ANALYZER_TOOL_OUTPUT_TOKENS": (_read_int, 1024),
    "LOCAL_ANALYZER_YIELD_SECONDS": (_read_float, 60.0),
    "LOCAL_ANALYZER_ENABLE_THINKING": (_read_bool, True),
    "LOCAL_ANALYZER_TEMPERATURE": (_read_float, 0.6),
    "LOCAL_ANALYZER_TOP_P": (_read_float, 0.95),
    "LOCAL_ANALYZER_TOP_K": (_read_int, 20),
    "LOCAL_ANALYZER_SEED": (_read_seed, -1),
}

observed_environment = {}
for variable_name, (reader, expected_value) in expected_environment.items():
    observed_value = reader(variable_name)
    observed_environment[variable_name] = observed_value
    if observed_value != expected_value:
        raise RuntimeError(
            "ACTION7 CONFIGURATION GUARD STOPPED: environment mismatch: "
            f"{variable_name}={observed_value!r}, expected={expected_value!r}"
        )

if EXPECTED_SOURCE_ROOT.is_dir():
    source_root = EXPECTED_SOURCE_ROOT
else:
    candidates = sorted(
        path.resolve()
        for path in Path("/kaggle/input").glob("*/src/ARC3-Inference")
        if (path / "inference/agent/action_names.py").is_file()
    )
    if len(candidates) != 1:
        raise RuntimeError(
            "ACTION7 CONFIGURATION GUARD STOPPED: expected exactly one Duck "
            f"source root, found {len(candidates)}: {candidates!r}"
        )
    source_root = candidates[0]

source_root_text = str(source_root)
if source_root_text not in sys.path:
    sys.path.insert(0, source_root_text)
importlib.invalidate_caches()

# The ARM_GATE may already have imported this module.  We deliberately reuse
# that exact module, then verify its frozen analyzer constants below.  A stale
# or early import therefore still stops the run, but a correctly configured
# ARM_GATE import does not cause a false failure.
action_names = importlib.import_module("inference.agent.action_names")

source_path = Path(inspect.getsourcefile(action_names) or "").resolve()
if not source_path.is_file():
    raise RuntimeError(f"Could not locate loaded action_names.py: {source_path}")

source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
already_safe = (
    action_names.to_model_action("ACTION7") == "UNDO"
    and action_names.to_engine_action("UNDO") == "ACTION7"
    and action_names.to_engine_action("ACTION7") == "ACTION7"
)
if source_sha256 != EXPECTED_HISTORICAL_ACTION_NAMES_SHA256 and not already_safe:
    raise RuntimeError(
        "ACTION7 CONFIGURATION GUARD STOPPED: unexpected action_names.py: "
        f"path={source_path}, sha256={source_sha256}"
    )

action_names.ENGINE_TO_MODEL_ACTION["ACTION7"] = "UNDO"
action_names.MODEL_TO_ENGINE_ACTION["UNDO"] = "ACTION7"
action_names.MODEL_TO_ENGINE_ACTION["ACTION7"] = "ACTION7"

tool_agent = importlib.import_module("inference.agent.tool_agent")

module_expectations = {
    "_LOCAL_ANALYZER_MAX_OUTPUT": 0,
    "_LOCAL_ANALYZER_CONTEXT_WINDOW": 32768,
    "_LOCAL_ANALYZER_TOOL_STEPS": 0,
    "_LOCAL_ANALYZER_TOOL_TIMEOUT": 30,
    "_LOCAL_ANALYZER_TOOL_OUTPUT_TOKENS": 1024,
    "_LOCAL_ANALYZER_YIELD_SECONDS": 60.0,
    "_LOCAL_ANALYZER_ENABLE_THINKING": True,
    "_LOCAL_ANALYZER_TEMPERATURE": 0.6,
    "_LOCAL_ANALYZER_TOP_P": 0.95,
    "_LOCAL_ANALYZER_TOP_K": 20,
    "_LOCAL_ANALYZER_SEED": -1,
}

observed_module_settings = {
    name: getattr(tool_agent, name, None) for name in module_expectations
}
if observed_module_settings != module_expectations:
    raise RuntimeError(
        "ACTION7 CONFIGURATION GUARD STOPPED: imported analyzer settings do "
        "not match the intended configuration: "
        f"observed={observed_module_settings!r}, "
        f"expected={module_expectations!r}"
    )

mapping_checks = {
    "engine_ACTION7_to_model": tool_agent.to_model_action("ACTION7"),
    "model_UNDO_to_engine": tool_agent.to_engine_action("UNDO"),
    "native_ACTION7_to_engine": tool_agent.to_engine_action("ACTION7"),
    "lowercase_undo_to_engine": tool_agent.to_engine_action("  undo  "),
    "lowercase_action7_to_engine": tool_agent.to_engine_action(" action7 "),
    "invalid_action_rejected": tool_agent.to_engine_action("__INVALID_ACTION__"),
}
expected_mapping_checks = {
    "engine_ACTION7_to_model": "UNDO",
    "model_UNDO_to_engine": "ACTION7",
    "native_ACTION7_to_engine": "ACTION7",
    "lowercase_undo_to_engine": "ACTION7",
    "lowercase_action7_to_engine": "ACTION7",
    "invalid_action_rejected": None,
}
if mapping_checks != expected_mapping_checks:
    raise RuntimeError(
        "ACTION7 CONFIGURATION GUARD STOPPED: mapping checks failed: "
        f"observed={mapping_checks!r}, expected={expected_mapping_checks!r}"
    )

for engine_action in action_names.ENGINE_TO_MODEL_ACTION:
    model_action = tool_agent.to_model_action(engine_action)
    round_trip = tool_agent.to_engine_action(model_action)
    if round_trip != engine_action:
        raise RuntimeError(
            "ACTION7 CONFIGURATION GUARD STOPPED: action round trip failed: "
            f"{engine_action!r} -> {model_action!r} -> {round_trip!r}"
        )

print("ACTION7 POST-ENVIRONMENT GUARD PASSED")
print(f"source_root={source_root}")
print(f"loaded_source={source_path}")
print(f"loaded_source_sha256={source_sha256}")
print(f"effective_settings={observed_module_settings}")
print(f"mapping_checks={mapping_checks}")
