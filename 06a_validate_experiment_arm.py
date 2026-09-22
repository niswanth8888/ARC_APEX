"""Stage 06a: Validate the experiment arm.

Purpose
-------
Inspect the live vLLM command line and frozen analyzer settings, then fail fast if the running server does not match the requested A/B experiment arm.

Inputs
------
ARM, the running /proc process table, vLLM environment configuration, and analyzer module constants.

Outputs
-------
A validated serving configuration or an immediate RuntimeError before benchmark actions begin.

Workflow diagram (Mermaid)
--------------------------
```mermaid
flowchart TD
    N1["Find vLLM process"]
    N2["Detect speculative mode"]
    N3["Compare requested arm"]
    N4["Validate analyzer constants"]
    N5["Approve run"]
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

# ===================== ARM GATE =====================
def _running_vllm_cmdline() -> str:
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            raw = (proc / "cmdline").read_bytes().decode("utf-8", "replace")
        except Exception:
            continue
        cmdline = raw.replace("\x00", " ")
        if "vllm.entrypoints" in cmdline and " serve " in f" {cmdline} ":
            return cmdline
    return ""

_cmdline = _running_vllm_cmdline()
if not _cmdline:
    raise RuntimeError("ARM GATE: no running vLLM server found; cannot verify the arm.")
_speculative_on = "--speculative-config" in _cmdline
print(f"ARM_GATE arm={ARM} speculative_config_present={_speculative_on}", flush=True)
if ARM == "A" and not _speculative_on:
    raise RuntimeError("ARM GATE: arm A must run WITH speculative decoding.")
if ARM == "B" and _speculative_on:
    raise RuntimeError("ARM GATE: arm B must run WITHOUT speculative decoding.")

# ============ KNOB BANNER (no patching; stock config) ============
import inference.agent.tool_agent as TA
if TA._LOCAL_ANALYZER_SEED != -1:
    raise RuntimeError(f"KNOB GATE: seed should be the shipped -1, found {TA._LOCAL_ANALYZER_SEED!r}.")
print("RESOLVED_KNOBS " + json.dumps({
    "seed": TA._LOCAL_ANALYZER_SEED,
    "temperature": TA._LOCAL_ANALYZER_TEMPERATURE,
    "top_p": TA._LOCAL_ANALYZER_TOP_P,
    "top_k": TA._LOCAL_ANALYZER_TOP_K,
    "thinking": TA._LOCAL_ANALYZER_ENABLE_THINKING,
    "max_output": TA._LOCAL_ANALYZER_MAX_OUTPUT,
    "tool_steps": TA._LOCAL_ANALYZER_TOOL_STEPS,
    "tool_output_tokens": TA._LOCAL_ANALYZER_TOOL_OUTPUT_TOKENS,
    "context_window": TA._LOCAL_ANALYZER_CONTEXT_WINDOW,
    "yield_seconds": TA._LOCAL_ANALYZER_YIELD_SECONDS,
    "multimodal_context": os.environ.get("MULTIMODAL_CONTEXT"),
    "multimodal_upscale": os.environ.get("MULTIMODAL_UPSCALE"),
}, sort_keys=True), flush=True)
# =================================================================

bm.solver.max_runtime_s_per_game = 7600.0
bm.solver.analyzer_timeout = 900.0
bm.solver.concurrency = 28
bm.solver.max_actions_per_game = None
bm.solver.save_request_logs = False
if float(getattr(target, 'max_runtime_s', 0.0) or 0.0) != 32400.0:
    raise RuntimeError(
        f'Expected the 32400-second notebook budget, got {target.max_runtime_s!r}.'
    )
print(
    f'PUBLIC25_SETTINGS budget_s={bm.solver.max_runtime_s_per_game} '
    f'concurrency={bm.solver.concurrency} analyzer_timeout={bm.solver.analyzer_timeout} '
    f'action_cap={bm.solver.max_actions_per_game} request_logs={bm.solver.save_request_logs}',
    flush=True,
)
