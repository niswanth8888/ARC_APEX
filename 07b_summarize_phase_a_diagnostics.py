"""Stage 07b: Summarize Phase A diagnostics.

Purpose
-------
Read the observer event stream, correlate starts and ends, compute request/action/token metrics, and write machine-readable audit summaries.

Inputs
------
The in-process Phase A observer and its JSONL event file.

Outputs
-------
summary.json, requests.jsonl, console metrics, and integrity warnings.

Workflow diagram (Mermaid)
--------------------------
```mermaid
flowchart TD
    N1["Flush observer"]
    N2["Parse JSONL events"]
    N3["Correlate event pairs"]
    N4["Aggregate run metrics"]
    N5["Write audit files"]
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

# Paste this ENTIRE file into ONE cell AFTER the existing benchmark returns.
# Run even if the existing teardown cell reports an error, once games stop.
# This reports observed usage, never invents tokens for missing responses.
import collections as _ds_collections
import json as _ds_json
import inference.agent.tool_agent as _ds_ta

print("PHASE_A_SUMMARY v1 — cell is running", flush=True)

_ds_audit = getattr(_ds_ta, "_duck_audit_v1", None)
if _ds_audit is None:
    raise RuntimeError("No observer in this kernel. No instrumentation result is available.")
_ds_audit.emit(event="health", health=_ds_audit.health())
_ds_health = _ds_audit.flush()
_ds_rows = []
_ds_bad_lines = 0
with _ds_audit.path.open(encoding="utf-8") as _ds_file:
    for _ds_line in _ds_file:
        try:
            _ds_rows.append(_ds_json.loads(_ds_line))
        except ValueError:
            _ds_bad_lines += 1


def _ds_summarize(rows):
    starts = {r["event_id"]: r for r in rows if r["event"].endswith("_start")}
    ends = {r["event_id"]: {**starts.get(r["event_id"], {}), **r}
            for r in rows if r["event"].endswith("_end")}
    requests = [r for r in ends.values() if r["event"] == "request_end"]
    tools = [r for r in ends.values() if r["event"] == "tool_end"]
    actions = [r for r in ends.values() if r["event"] == "action_end" and r.get("executed") is True]
    nonreset_actions = [r for r in actions if r.get("action_name") not in (None, "RESET")]
    decisions = [r for r in ends.values() if r["event"] == "decision_end"]
    batches = [r for r in ends.values() if r["event"] == "batch_end"]
    action_counts = _ds_collections.Counter(r.get("request_id") for r in actions if r.get("request_id"))
    decision_actions = _ds_collections.Counter(r.get("decision_id") for r in actions if r.get("decision_id"))
    tool_counts = _ds_collections.Counter(r.get("request_id") for r in tools if r.get("request_id"))
    request_rows = []
    known_tokens = sum(r["generated_tokens"] for r in requests if r.get("generated_tokens") is not None)
    for request in requests:
        n = action_counts[request["event_id"]]
        request_rows.append(dict(request_id=request["event_id"], game_key=request["game_key"],
            generated_tokens=request.get("generated_tokens"), tool_steps=tool_counts[request["event_id"]],
            actions=n, action_bucket="0" if n == 0 else "1" if n == 1 else "2+",
            ok=request["ok"], timeout=request.get("timeout", False),
            finish_reason=request.get("finish_reason"), duration_s=request["duration_s"]))
    buckets = dict(_ds_collections.Counter(r["action_bucket"] for r in request_rows))
    decision_hist = dict(_ds_collections.Counter(
        "0" if decision_actions[r["event_id"]] == 0 else "1" if decision_actions[r["event_id"]] == 1 else "2+"
        for r in decisions))
    unknown = sum(r.get("generated_tokens") is None for r in requests)
    pending = _ds_collections.Counter(r["event"] for key, r in starts.items() if key not in ends)
    summary = dict(games_observed=len({r["game_key"] for r in decisions}), requests_finished=len(requests),
        requests_failed=sum(not r["ok"] for r in requests), request_timeouts=sum(r.get("timeout", False) for r in requests),
        requests_with_unknown_output_tokens=unknown, observed_generated_tokens=known_tokens,
        request_action_histogram=buckets, decision_action_histogram=decision_hist,
        decisions_finished=len(decisions), tool_steps_finished=len(tools), engine_actions_observed=len(actions),
        nonreset_engine_actions=len(nonreset_actions), reset_actions=sum(r.get("action_name") == "RESET" for r in actions),
        nonreset_no_board_change_fraction=(sum(r.get("board_changed") is False for r in nonreset_actions) / len(nonreset_actions)
                                          if nonreset_actions else None),
        automatic_actions_outside_decisions=sum(r.get("automatic_outside_decision", False) for r in actions),
        actions_per_finished_decision=(sum(decision_actions.values()) / len(decisions) if decisions else None),
        observed_tokens_per_engine_action=(known_tokens / len(actions) if actions else None),
        observed_tokens_per_nonreset_action=(known_tokens / len(nonreset_actions) if nonreset_actions else None),
        token_rate_is_incomplete=bool(unknown or pending.get("request_start", 0)),
        batch_calls=len(batches), multi_action_batches=sum((r.get("executed_count") or 0) >= 2 for r in batches),
        batch_errors=sum(bool(r.get("error")) or r.get("stop_reason") in ("invalid_action", "action_error") for r in batches),
        level_completion_events=sum(bool(r.get("level_completed")) or bool(r.get("run_complete")) for r in actions),
        starts_without_ends=dict(pending))
    return summary, request_rows


_ds_summary, _ds_requests = _ds_summarize(_ds_rows)
_ds_summary.update(health=_ds_health, malformed_log_lines=_ds_bad_lines,
                   arm=_ds_audit.arm, run_id=_ds_audit.run_id,
                   note="Token totals exclude unobserved server work. Match engine action counts to the official trace before using ratios.")
_ds_summary["per_game"] = {}
for _ds_game in sorted({r.get("game_key") for r in _ds_rows if r.get("game_key")}):
    _ds_summary["per_game"][_ds_game] = _ds_summarize([r for r in _ds_rows if r.get("game_key") == _ds_game])[0]
_ds_action_starts = {r["event_id"]: r for r in _ds_rows if r["event"] == "action_start"}
_ds_completion = {}
for _ds_row in _ds_rows:
    if _ds_row["event"] == "action_end" and _ds_row.get("executed") is True:
        _ds_level_count = _ds_action_starts.get(_ds_row["event_id"], {}).get("number_of_levels")
        _ds_completed = _ds_row.get("score")
        if type(_ds_level_count) is int and _ds_level_count > 0 and type(_ds_completed) is int:
            _ds_ceiling = 100 * _ds_completed * (_ds_completed + 1) / (_ds_level_count * (_ds_level_count + 1))
            _ds_game = _ds_row["game_key"]
            _ds_completion[_ds_game] = max(_ds_completion.get(_ds_game, 0), _ds_ceiling)
_ds_summary["observed_completion_ceiling_by_game"] = _ds_completion
_ds_summary["mean_completion_ceiling_public25"] = sum(_ds_completion.values()) / 25 if _ds_completion else None
(_ds_audit.directory / "summary.json").write_text(_ds_json.dumps(_ds_summary, indent=2), encoding="utf-8")
with (_ds_audit.directory / "requests.jsonl").open("w", encoding="utf-8") as _ds_file:
    for _ds_row in _ds_requests:
        _ds_file.write(_ds_json.dumps(_ds_row) + "\n")
print(_ds_json.dumps({k: v for k, v in _ds_summary.items() if k != "per_game"}, indent=2))
print("SAVE THIS WHOLE OUTPUT FOLDER:", _ds_audit.directory)
if _ds_health["errors"] or _ds_health["dropped"] or _ds_bad_lines or _ds_summary["starts_without_ends"]:
    print("INTEGRITY WARNING: incomplete instrumentation. Do not silently promote this run.")
if _ds_summary["games_observed"] != 25:
    print("INTEGRITY WARNING: not exactly 25 observed game paths. Verify process coverage and game selection.")
