# Pipeline workflow diagrams

These diagrams mirror the Mermaid definitions embedded in each Python stage.

## `01_environment_and_submission_mode.py` — Environment and submission mode

Detect the Kaggle execution mode, select experiment arm A or B, configure vLLM tuning, set framework flags, and prepare CUDA and working-directory paths.

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

## `02_install_arc_runtime.py` — Install the ARC runtime

Install arc-agi from Kaggle's offline competition wheelhouse without contacting the internet.

```mermaid
flowchart TD
    N1["Build pip command"]
    N2["Use offline wheelhouse"]
    N3["Install arc-agi"]
    N4["Surface failures"]
    N1 --> N2
    N2 --> N3
    N3 --> N4
```

## `03_locate_source_bundle.py` — Locate the source bundle

Find the TAAF source bundle by marker file and resolve every Kaggle dataset or utility-script mount used by setup.

```mermaid
flowchart TD
    N1["Scan for bundle marker"]
    N2["Generate mount candidates"]
    N3["Resolve existing mounts"]
    N4["Record bundle path"]
    N1 --> N2
    N2 --> N3
    N3 --> N4
```

## `04_import_source_and_run_setup.py` — Import source and run setup

Expose bundled repositories on Python's import path, build the setup environment, and execute the source bundle's declared setup commands.

```mermaid
flowchart TD
    N1["Find import roots"]
    N2["Update Python paths"]
    N3["Build command environment"]
    N4["Run setup commands"]
    N5["Persist setup state"]
    N1 --> N2
    N2 --> N3
    N3 --> N4
    N4 --> N5
```

## `05_load_benchmark.py` — Load the benchmark

Restore the serialized deployment target and benchmark, stamp the true submission state, and redirect output to Kaggle's writable directory.

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

## `06a_validate_experiment_arm.py` — Validate the experiment arm

Inspect the live vLLM command line and frozen analyzer settings, then fail fast if the running server does not match the requested A/B experiment arm.

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

## `06b_install_action7_patch.py` — Install the ACTION7 patch

Verify analyzer configuration and safely install the ACTION7 behavior patch with source fingerprints and repeat-install protection.

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

## `06c_install_phase_a_observer.py` — Install the Phase A observer

Attach non-invasive instrumentation to model requests, tool calls, solver decisions, and engine actions so the run can be audited afterward.

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

## `07a_run_benchmark.py` — Run the benchmark

Select live hidden games or the fixed public-25 offline set, enforce run gates, start the model-server watchdog, execute the benchmark, score public runs, and always tear down.

```mermaid
flowchart TD
    N1["Select game source"]
    N2["Validate game coverage"]
    N3["Compute soft deadline"]
    N4["Start watchdog"]
    N5["Await benchmark"]
    N6["Score and tear down"]
    N1 --> N2
    N2 --> N3
    N3 --> N4
    N4 --> N5
    N5 --> N6
```

## `07b_summarize_phase_a_diagnostics.py` — Summarize Phase A diagnostics

Read the observer event stream, correlate starts and ends, compute request/action/token metrics, and write machine-readable audit summaries.

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

## `08_show_diagnostics.py` — Show diagnostics

Document that HTML rendering is intentionally skipped because minimal diagnostics are enabled.

```mermaid
flowchart TD
    N1["Confirm minimal mode"]
    N2["Skip HTML rendering"]
    N3["Keep audit artifacts"]
    N1 --> N2
    N2 --> N3
```
