# ============================================================
# Benchmark Execution & Result Generation
# ============================================================

# Overview:
# This module executes the complete ARC APEX benchmark pipeline.
# Depending on the execution environment, it either connects to
# the live Kaggle competition gateway or loads the bundled offline
# benchmark environments. After preparing the game list, the
# benchmark is executed, predictions are generated, and cleanup
# procedures are performed before the session terminates.

# Purpose:
# Acts as the primary execution engine of ARC APEX by managing
# benchmark selection, runtime scheduling, solver execution,
# prediction generation, and post-execution cleanup while
# supporting both competition and offline development modes.

# Workflow:
#
#          Start Benchmark
#                 |
#                 v
#     Determine Execution Mode
#                 |
#      +----------+----------+
#      |                     |
#      v                     v
# Live Competition      Offline Benchmark
#      |                     |
#      +----------+----------+
#                 |
#                 v
#      Prepare Benchmark Games
#                 |
#                 v
#       Configure Runtime Limits
#                 |
#                 v
#      Execute ARC APEX Solver
#                 |
#                 v
#      Generate Prediction Output
#                 |
#                 v
#      Run Cleanup Procedures
#                 |
#                 v
#         Execution Complete
#
# ============================================================


# Create the game list for live Kaggle competition execution.
def _competition_games():
    import arc_agi
    import taaf.game_api

    spec = taaf.game_api.ArcadeSpec(
        operation_mode=arc_agi.OperationMode.COMPETITION,
        arc_base_url=os.environ["ARC_BASE_URL"],
        environments_dir="",
    )

    arcade = arc_agi.Arcade(
        operation_mode=arc_agi.OperationMode.COMPETITION,
        arc_base_url=spec.arc_base_url,
        environments_dir="",
    )

    game_ids = [env_info.game_id for env_info in arcade.available_environments]

    if not game_ids:
        raise RuntimeError("Competition Arcade exposed zero environments.")

    return [
        taaf.game_api.GameAPI(
            env_name=game_id,
            arcade_spec=spec,
        )
        for game_id in game_ids
    ]


# Build the offline benchmark using the bundled competition environments.
def _offline_games(env_dir: str):
    import arc_agi
    import taaf.game_api

    spec = taaf.game_api.ArcadeSpec(
        operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=env_dir,
    )

    arcade = arc_agi.Arcade(
        operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=env_dir,
    )

    game_ids = [env_info.game_id for env_info in arcade.available_environments]

    if not game_ids:
        raise RuntimeError(f"No offline environments found under {env_dir}.")

    return [
        taaf.game_api.GameAPI(
            env_name=game_id,
            arcade_spec=spec,
        )
        for game_id in game_ids
    ]


# Wait until the Kaggle competition gateway becomes available
# before requesting benchmark environments.
def _wait_for_gateway(base_url: str, timeout_s: float = 600.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_error = ""

    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}api/games", timeout=10) as response:
                if response.status < 500:
                    return
        except Exception as exc:
            last_error = repr(exc)

        time.sleep(5)

    raise RuntimeError(f"Kaggle gateway did not become ready: {last_error}")


# Display execution information and preserve runtime diagnostics.
print((BUNDLE_DIR / "preamble.txt").read_text())
(WORKING_DIR / "git_status.txt").write_text(
    (BUNDLE_DIR / "git_status.txt").read_text()
)


# Configure recording storage used during benchmark execution.
os.environ.setdefault(
    "RECORDINGS_DIR",
    str(WORKING_DIR / "server_recording"),
)


# Configure benchmark execution according to the selected runtime.
if TRUE_SUBMISSION:

    # Execute using the live Kaggle competition gateway.
    os.environ.setdefault("ARC_API_KEY", "test-key-123")
    os.environ.setdefault("ARC_BASE_URL", "http://gateway:8001/")

    _wait_for_gateway(os.environ["ARC_BASE_URL"])

    bm.games = _competition_games()

else:

    # Execute using the bundled offline benchmark environments.
    competition_env_files = str(
        Path(
            "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels"
        ).parent / "environment_files"
    )

    bm.games = _offline_games(competition_env_files)


# Configure benchmark games used during offline execution.
if not TRUE_SUBMISSION:
    try:
        import taaf.game_api

        first = bm.games[0]

        bm.games = bm.games[:3] + [
            taaf.game_api.GameAPI(
                env_name=first.env_name,
                arcade_spec=first.arcade_spec,
                external_game_id=f"{first.env_name}-dup",
            )
        ]

    except Exception as exc:  # noqa: BLE001
        print(
            f"[taaf_grafts] dup-game gate failed, using [:4]: {type(exc).__name__}: {exc}"
        )

        bm.games = bm.games[:4]


# Configure benchmark execution settings.
bm.n_passes = 1
bm.game_weights = None


# Calculate the execution deadline used during benchmark processing.
soft_end = None

if not TRUE_SUBMISSION:

    budget = float(getattr(target, "max_runtime_s", 0.0) or 0.0)

    if budget > 0:
        soft_end = (
            datetime.fromtimestamp(NOTEBOOK_START_EPOCH)
            + timedelta(seconds=budget - min(600.0, budget / 2))
        )

else:

    soft_end = (
        datetime.fromtimestamp(NOTEBOOK_START_EPOCH)
        + timedelta(hours=11, minutes=20)
    )


# Execute the ARC benchmark and perform cleanup after completion.
try:

    await bm.run(
        soft_end_time=soft_end,
        runtime_environment=target,
        minimal_diagnostics=TRUE_SUBMISSION,
    )

    if not TRUE_SUBMISSION:
        import pandas as pd

        pd.DataFrame(
            [["1_0", "1", True, 1]],
            columns=[
                "row_id",
                "game_id",
                "end_of_game",
                "score",
            ],
        ).to_parquet(
            WORKING_DIR / "submission.parquet",
            index=False,
        )

finally:

    # Execute teardown procedures regardless of execution outcome.
    for command in json.loads(
        (BUNDLE_DIR / "teardown_commands.json").read_text()
    ):
        print(f"taaf.kaggle: teardown command: {command}", flush=True)

        subprocess.run(
            command,
            shell=True,
            check=False,
            cwd=WORKING_DIR,
            env=_command_env(),
        )
