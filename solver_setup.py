# ============================================================
# Source Integration & Solver Setup Execution
# ============================================================

# Overview:
# This module integrates the bundled ARC APEX source repositories
# into the Python environment and executes the required setup
# procedures before the solver begins processing benchmark tasks.
# It prepares the execution environment by configuring import paths,
# exporting runtime variables, and running initialization commands
# such as dependency installation and model preparation.

# Purpose:
# Establishes a fully configured runtime by making all bundled
# project modules accessible, executing setup commands, and
# synchronizing environment variables required throughout the
# ARC APEX reasoning pipeline.

# Workflow:
#
#      Locate Source Repositories
#                |
#                v
#     Register Python Import Paths
#                |
#                v
#    Generate Runtime Environment
#                |
#                v
#     Execute Setup Commands
#                |
#                v
#   Update Environment Variables
#                |
#                v
#    Initialize ARC APEX Solver
#
# ============================================================


# Discover all available source directories contained within
# the bundled project repositories.
def _source_path_entries(bundle_dir: Path) -> list:
    entries = []
    for repo in sorted((bundle_dir / "src").iterdir(), reverse=True):
        for candidate in (repo / "src", repo):
            if candidate.is_dir():
                entries.append(candidate)
    return entries


# Build the runtime environment shared by every setup command.
# This includes execution paths, working directories, and any
# previously exported configuration values.
def _command_env() -> dict:
    env = os.environ.copy()

    # Use the current Python interpreter for all setup operations.
    env["PYTHON"] = sys.executable

    # Provide access to the mounted ARC APEX source bundle.
    env["TAAF_KAGGLE_BUNDLE_DIR"] = str(BUNDLE_DIR)

    # Define the writable workspace used during execution.
    env["TAAF_KAGGLE_WORKING_DIR"] = str(WORKING_DIR)

    # Store shared environment variables between setup stages.
    env["TAAF_KAGGLE_SETUP_ENV"] = str(SETUP_ENV_PATH)

    env.update(
        {
            str(k): str(v)
            for k, v in json.loads(
                SETUP_ENV_PATH.read_text()
            ).items()
        }
    )

    return env


# Register bundled repositories so they are available for import
# within the current process and any child processes.
source_entries = _source_path_entries(BUNDLE_DIR)

for entry in source_entries:
    sys.path.insert(0, str(entry))

pth_path = Path(sysconfig.get_paths()["purelib"]) / "taaf_kaggle_sources.pth"

pth_path.write_text(
    "".join(f"{entry}\n" for entry in source_entries)
)

print(
    f"taaf.kaggle: wrote {pth_path} ({len(source_entries)} source roots)"
)


# Execute every setup command required before loading the ARC
# benchmark. These commands may install dependencies, prepare
# AI models, or configure supporting services.
env = _command_env()

for command in json.loads(
    (BUNDLE_DIR / "setup_commands.json").read_text()
):
    print(f"taaf.kaggle: setup command: {command}", flush=True)

    subprocess.run(
        command,
        shell=True,
        check=True,
        cwd=WORKING_DIR,
        env=env,
    )

    # Reload the environment in case new variables were exported.
    env = _command_env()

os.environ.update(env)


# Include any additional Python paths exported during setup so
# they are immediately available to the current execution.
for entry in reversed(
    [
        e
        for e in os.environ.get("PYTHONPATH", "").split(os.pathsep)
        if e
    ]
):
    if entry not in sys.path:
        sys.path.insert(0, entry)
