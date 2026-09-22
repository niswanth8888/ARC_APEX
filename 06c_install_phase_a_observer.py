"""Stage 06c: Install the Phase A observer.

Purpose
-------
Attach non-invasive instrumentation to model requests, tool calls, solver decisions, and engine actions so the run can be audited afterward.

Inputs
------
ToolAgent, solver, game API classes, ARM, and /kaggle/working.

Outputs
-------
Thread-safe JSONL audit events plus a registered observer available to the diagnostics stage.

Workflow diagram (Mermaid)
--------------------------
```mermaid
flowchart TD
    N1["Fingerprint hook targets"]
    N2["Create audit writer"]
    N3["Wrap request and tool paths"]
    N4["Wrap engine actions"]
    N5["Register shutdown flush"]
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

# Paste this ENTIRE file into ONE Kaggle cell, after Duck's imports/setup and
# BEFORE starting the benchmark. Run in a fresh kernel for every lab run.
# No installation, network access, model requests, or /kaggle/input writes.
import ast as _da_ast
import atexit as _da_atexit
import functools as _da_functools
import hashlib as _da_hashlib
import inspect as _da_inspect
import json as _da_json
import os as _da_os
from pathlib import Path as _da_Path
import queue as _da_queue
import textwrap as _da_textwrap
import threading as _da_threading
import time as _da_time
import uuid as _da_uuid
import inference.agent.tool_agent as _da_ta
import inference.framework.solver as _da_solver

print("PHASE_A_OBSERVER v1 — cell is running", flush=True)


def _da_fingerprint(function):
    tree = _da_ast.parse(_da_textwrap.dedent(_da_inspect.getsource(function)))
    normalized = _da_ast.dump(tree.body[0], include_attributes=False)
    normalized = normalized.replace(", type_params=[]", "")
    return _da_hashlib.sha256(normalized.encode()).hexdigest()


_da_expected = [
    (_da_ta.ToolAgent, "analyze", "86165aa0d10fc2ed02f66f20a2d0fdc8dc14920b4e0f48681528161079bb7c9d", "decision"),
    (_da_ta.ToolAgent, "_chat_completion", "529df36ef20ec204b30c3fb7789a1970e1985d8296aa094808ebf24fac18be84", "request"),
    (_da_ta.ToolAgent, "_dispatch_tool", "b65872d40f499929f3c0a58c63e749ddf44a23764c879c2c1167053abd1f0ad0", "tool"),
    (_da_solver._HarnessGameSession, "step_env", "03dd8dfc996c6a3f1420a8bd0f26c0fdb0597c6e2d5b451ef92d012bb5286a75", "batch"),
    (_da_solver._HarnessGameSession, "_execute_action", "f4a556fd16637a3647cc4254352bae35c00352df682f1df0044e2a3310f79e22", "action"),
]


class _DuckAudit:
    def __init__(self):
        self.run_id = _da_uuid.uuid4().hex
        self.arm = "A"
        self.directory = _da_Path("/kaggle/working/duck_audit") / self.run_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.path = self.directory / ("events_pid_%s.jsonl" % _da_os.getpid())
        # Open BEFORE installing wrappers: unwritable output is a cheap preflight failure.
        self.stream = self.path.open("x", encoding="utf-8", buffering=1)
        self.queue = _da_queue.Queue(maxsize=8192)
        self.errors = 0
        self.dropped = 0
        self.calls = 0
        self.closed = False
        self.bytes_written = 0
        self.contexts = {}
        self.lock = _da_threading.RLock()
        self.originals = []
        self.writer = _da_threading.Thread(target=self._write, daemon=True, name="duck-audit-writer")
        self.writer.start()

    def _write(self):
        while True:
            row = self.queue.get()
            try:
                if row is None:
                    return
                line = _da_json.dumps(row, ensure_ascii=True, allow_nan=False) + "\n"
                if self.bytes_written + len(line) > 128 * 1024 * 1024:
                    self.dropped += 1
                    continue
                self.stream.write(line)
                self.bytes_written += len(line)
            except Exception:
                self.errors += 1
            finally:
                self.queue.task_done()

    def emit(self, **row):
        # All normal logging failures are isolated from the original agent.
        try:
            if self.closed or not self.writer.is_alive():
                self.dropped += 1
                return
            row.update(run_id=self.run_id, arm=self.arm, pid=_da_os.getpid(),
                       thread=_da_threading.get_ident(), mono_s=_da_time.monotonic(),
                       unix_s=_da_time.time())
            self.queue.put_nowait(row)
        except Exception:
            self.dropped += 1

    def health(self):
        return dict(errors=self.errors, dropped=self.dropped, calls=self.calls,
                    queued=self.queue.qsize(), writer_alive=self.writer.is_alive(),
                    closed=self.closed, bytes_written=self.bytes_written)

    def flush(self):
        # Bounded wait, used only by the post-run summary and interpreter shutdown.
        until = _da_time.monotonic() + 3.0
        while self.queue.unfinished_tasks and _da_time.monotonic() < until:
            _da_time.sleep(0.01)
        return self.health()

    def context_for(self, kind, owner):
        agent = owner.analyzer if kind in ("action", "batch") else owner
        with self.lock:
            context = self.contexts.get(id(agent))
        if context is not None:
            return context
        # Includes automatic RESETs outside analyze(), rather than misassigning
        # their cost to the preceding model request.
        return dict(decision_id=None, request_id=None,
                    game_key=str(getattr(owner, "state_path", "unknown")))

    def begin(self, kind, owner, args, kwargs):
        context = self.context_for(kind, owner)
        previous = None
        if kind == "decision":
            state_path = args[0] if args else kwargs.get("state_path")
            context = dict(decision_id=_da_uuid.uuid4().hex, request_id=None,
                           game_key=str(state_path))
            with self.lock:
                previous = self.contexts.get(id(owner))
                self.contexts[id(owner)] = context
        event_id = _da_uuid.uuid4().hex
        if kind == "decision":
            context["decision_id"] = event_id
        if kind == "request":
            context["request_id"] = event_id
        ticket = dict(kind=kind, event_id=event_id, decision_id=context["decision_id"],
                      request_id=context["request_id"], game_key=context["game_key"],
                      started=_da_time.monotonic(), previous=previous)
        details = {}
        if kind == "decision":
            details["action_num_before"] = args[1] if len(args) > 1 else kwargs.get("action_num")
        elif kind == "tool":
            details["tool_name"] = args[1] if len(args) > 1 else kwargs.get("name")
            arguments = args[2] if len(args) > 2 else kwargs.get("arguments")
            if isinstance(arguments, dict) and isinstance(arguments.get("code"), str):
                code = arguments["code"]
                details["code_sha256"] = _da_hashlib.sha256(code.encode()).hexdigest()
                details["code_chars"] = len(code)
        elif kind == "request":
            details["requested_timeout_s"] = kwargs.get("request_timeout_seconds", getattr(owner, "_timeout", None))
        elif kind == "batch":
            arguments = args[0] if args else kwargs.get("arguments")
            if isinstance(arguments, dict):
                actions = arguments.get("actions")
                details["requested_count"] = len(actions) if isinstance(actions, list) else None
        elif kind == "action":
            details["number_of_levels"] = getattr(getattr(owner, "game", None), "number_of_levels", None)
            details["game_budget_s"] = getattr(getattr(owner, "solver", None), "max_runtime_s_per_game", None)
        self.calls += 1
        self.emit(event=kind + "_start", **self.ids(ticket), **details)
        return ticket

    @staticmethod
    def ids(ticket):
        return {key: ticket[key] for key in ("event_id", "decision_id", "request_id", "game_key")}

    @staticmethod
    def scalar_fields(value, names):
        return {key: value[key] for key in names
                if key in value and (value[key] is None or isinstance(value[key], (str, int, float, bool)))}

    def end(self, ticket, result, error):
        details = dict(duration_s=_da_time.monotonic() - ticket["started"],
                       ok=error is None)
        kind = ticket["kind"]
        if error is not None:
            chain = []
            current = error
            for _ in range(5):
                if current is None:
                    break
                chain.append(type(current).__name__)
                current = current.__cause__ or current.__context__
            details.update(exception_types=chain,
                           timeout=any("timeout" in name.lower() for name in chain))
        elif kind == "request":
            usage = getattr(result, "usage", None)
            details["finish_reason"] = getattr(result, "finish_reason", None)
            details["usage"] = self.scalar_fields(usage, (
                "prompt_tokens", "completion_tokens", "total_tokens", "input_tokens",
                "output_tokens", "generated_tokens")) if isinstance(usage, dict) else None
            # Missing is NULL, never an invented zero. Store both aliases, but
            # choose only ONE output field for arithmetic.
            details["generated_tokens"] = None
            if isinstance(usage, dict):
                for key in ("completion_tokens", "output_tokens", "generated_tokens"):
                    if type(usage.get(key)) is int and usage[key] >= 0:
                        details["generated_tokens"] = usage[key]
                        break
            message = getattr(result, "message", None)
            if isinstance(message, dict):
                tool_calls = message.get("tool_calls")
                details["declared_tool_calls"] = len(tool_calls) if isinstance(tool_calls, list) else 0
        elif kind in ("action", "batch") and isinstance(result, dict):
            details.update(self.scalar_fields(result, (
                "executed", "executed_count", "requested_count", "action_num", "level",
                "score", "reward", "state", "board_changed", "done", "level_completed",
                "game_over", "run_complete", "stopped_early", "stop_reason", "error",
                "action_name", "action_display", "batch_index", "batch_size",
                "run_elapsed_seconds", "time_remaining_seconds")))
            if kind == "action":
                details["automatic_outside_decision"] = ticket["decision_id"] is None
        elif kind == "decision":
            details["returned_none"] = result is None
            for key in ("step_executed", "retryable_failure", "yielded_control"):
                details[key] = getattr(result, key, None)
            details["stop_category"] = (
                "returned_none" if result is None else
                "retryable_failure" if getattr(result, "retryable_failure", False) else
                "action_executed" if getattr(result, "step_executed", False) else
                "yielded_control" if getattr(result, "yielded_control", False) else "no_action")
        elif kind == "tool":
            details["step_executed"] = getattr(result, "step_executed", None)
            content = getattr(result, "content", None)
            if isinstance(content, str):
                details["result_chars"] = len(content)
                try:
                    parsed = _da_json.loads(content)
                    if isinstance(parsed, dict):
                        details["reported_tool_error"] = bool(parsed.get("error"))
                except (ValueError, TypeError):
                    details["reported_tool_error"] = None
        self.emit(event=kind + "_end", **self.ids(ticket), **details)

    def wrap(self, kind, original):
        audit = self

        @_da_functools.wraps(original)
        def wrapped(owner, *args, **kwargs):
            ticket = None
            try:
                ticket = audit.begin(kind, owner, args, kwargs)
            except Exception:
                audit.errors += 1
            # The original method is invoked EXACTLY ONCE. Its errors, including
            # cancellation and KeyboardInterrupt, are NEVER converted to success.
            result = None
            error = None
            try:
                result = original(owner, *args, **kwargs)
                return result
            except BaseException as exc:
                error = exc
                raise
            finally:
                try:
                    if ticket is not None:
                        audit.end(ticket, result, error)
                except Exception:
                    audit.errors += 1
                finally:
                    if kind == "decision":
                        try:
                            with audit.lock:
                                if ticket is not None and ticket["previous"] is not None:
                                    audit.contexts[id(owner)] = ticket["previous"]
                                else:
                                    audit.contexts.pop(id(owner), None)
                        except Exception:
                            audit.errors += 1
        return wrapped


def _da_install():
    existing = getattr(_da_ta, "_duck_audit_v1", None)
    if existing is not None:
        print("OBSERVER ALREADY INSTALLED; wrappers NOT stacked.", existing.path)
        return existing
    mismatches = []
    for owner, name, expected, kind in _da_expected:
        actual = _da_fingerprint(getattr(owner, name))
        if actual != expected:
            mismatches.append(owner.__name__ + "." + name + "=" + actual)
    if mismatches:
        raise RuntimeError("PRE-RUN STOP: this Duck fork differs from the inspected source. "
                           "Do NOT bypass this guard. Send this output back. " + "; ".join(mismatches))
    audit = _DuckAudit()
    try:
        for owner, name, expected, kind in _da_expected:
            original = getattr(owner, name)
            audit.originals.append((owner, name, original))
            setattr(owner, name, audit.wrap(kind, original))
        _da_ta._duck_audit_v1 = audit
    except BaseException:
        for owner, name, original in reversed(audit.originals):
            setattr(owner, name, original)
        raise
    audit.emit(event="installed", source_files={
        module.__name__: dict(path=module.__file__, sha256=_da_hashlib.sha256(
            _da_Path(module.__file__).read_bytes()).hexdigest())
        for module in (_da_ta, _da_solver)}, settings={
            key: value for key, value in vars(_da_ta).items()
            if key in ("_LOCAL_ANALYZER_SEED", "_LOCAL_ANALYZER_MAX_OUTPUT", "_LOCAL_ANALYZER_TOOL_STEPS",
                       "_LOCAL_ANALYZER_ENABLE_THINKING", "_LOCAL_ANALYZER_TEMPERATURE",
                       "_LOCAL_ANALYZER_TOP_P", "_LOCAL_ANALYZER_TOP_K")
            and (value is None or isinstance(value, (str, int, float, bool)))})
    _da_atexit.register(audit.flush)
    print("OBSERVER INSTALLED — arm %s. Start your EXISTING benchmark cell unchanged." % audit.arm)
    print("Log:", audit.path)
    print("Use a fresh kernel for each run. Save the entire duck_audit output folder.")
    return audit


DUCK_AUDIT = _da_install()
