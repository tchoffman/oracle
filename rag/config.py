from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | Path | None = None) -> dict:
    """Read rag/config.yaml and resolve paths against the repo root."""
    cfg_path = Path(path) if path else REPO_ROOT / "rag" / "config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    for key in ("chroma_dir",):
        if key in cfg and not Path(cfg[key]).is_absolute():
            cfg[key] = str(REPO_ROOT / cfg[key])

    return cfg
