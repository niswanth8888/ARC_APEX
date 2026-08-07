# ============================================================
# Source Bundle Discovery & Dataset Path Configuration
# ============================================================

# Overview:
# This module locates the ARC APEX source bundle and identifies
# the mount locations of all datasets and supporting resources
# attached to the Kaggle notebook. The resolved paths are stored
# as environment variables so that every stage of the framework
# can access the required files consistently.

# Purpose:
# Establishes a centralized dataset discovery mechanism that
# dynamically resolves resource locations without relying on
# hardcoded paths. This improves portability and ensures the
# solver can locate datasets and utility resources across
# different Kaggle execution environments.

# Workflow:
#
#      Scan Kaggle Input Directory
#                |
#                v
#     Locate Source Bundle Marker
#                |
#                v
#   Resolve Dataset Mount Locations
#                |
#                v
#    Build Environment Configuration
#                |
#                v
#   Export Paths for ARC APEX Modules
#
# ============================================================


# Kaggle datasets attached to the notebook along with
# configuration files used throughout the execution pipeline.

DATASET_SOURCES = [
    "thtennant/taaf-kaggle-source-share-fork",
    "driessmit1/arc3-vllm-h100-wheelhouse-v3",
    "driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot",
]

KERNEL_SOURCES = []

DATASET_BUNDLE_MARKER = "taaf-kaggle-bundle.json"

SETUP_ENV_PATH = WORKING_DIR / "taaf_setup_env.json"


# Search the Kaggle input directory for the ARC APEX source bundle
# using its marker file instead of relying on a fixed directory path.
def _find_bundle_dir() -> Path:
    for marker in Path("/kaggle/input").rglob(DATASET_BUNDLE_MARKER):
        return marker.parent
    raise RuntimeError("TAAF source bundle not found under /kaggle/input.")


# Generate possible mount locations for attached datasets,
# allowing compatibility with different Kaggle mounting structures.
def _dataset_mount_candidates(ref: str) -> list[Path]:
    owner, slug = ref.split("/", 1)
    return [
        Path("/kaggle/input") / slug,
        Path("/kaggle/input/datasets") / owner / slug,
    ]


# Generate possible mount locations for utility scripts
# or notebook kernel resources.
def _kernel_mount_candidates(ref: str) -> list[Path]:
    owner, slug = ref.split("/", 1)
    return [Path("/kaggle/usr/lib/notebooks") / owner / slug]


# Return the first available path from the generated candidates.
def _first_existing(candidates: list[Path]) -> Path | None:
    return next((c for c in candidates if c.exists()), None)


BUNDLE_DIR = _find_bundle_dir()

print(f"taaf.kaggle: source bundle = {BUNDLE_DIR}")


# Resolve the actual mount location of every attached dataset.
# The first dataset always represents the primary ARC APEX source bundle.
kaggle_input_paths: dict[str, str] = {}

for i, ref in enumerate(DATASET_SOURCES):
    candidates = _dataset_mount_candidates(ref)
    resolved = BUNDLE_DIR if i == 0 else _first_existing(candidates)
    kaggle_input_paths[ref] = str(resolved or candidates[0])

for ref in KERNEL_SOURCES:
    candidates = _kernel_mount_candidates(ref)
    kaggle_input_paths[ref] = str(_first_existing(candidates) or candidates[0])


# Store the resolved dataset information so that subsequent
# setup routines and solver components can access it.
setup_env = {
    "TAAF_KAGGLE_INPUT_PATHS": json.dumps(kaggle_input_paths, sort_keys=True),
    "TAAF_KAGGLE_DATASET_SOURCES": json.dumps(DATASET_SOURCES),
    "TAAF_KAGGLE_KERNEL_SOURCES": json.dumps(KERNEL_SOURCES),
}

os.environ.update(setup_env)

SETUP_ENV_PATH.write_text(
    json.dumps(setup_env, indent=2, sort_keys=True) + "\n"
)

print(f"taaf.kaggle: input paths = {setup_env['TAAF_KAGGLE_INPUT_PATHS']}")
