import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.toml"


def load_config(path=CONFIG_PATH):
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise SystemExit(f"Configuration file not found: {path}")
    except tomllib.TOMLDecodeError as error:
        raise SystemExit(f"Invalid configuration file {path}: {error}")


CONFIG = load_config()
TIMEOUT = (CONFIG["ollama"]["connect_timeout"], CONFIG["ollama"]["read_timeout"])


def options(usage=None):
    """Ollama generation options for one usage: shared values, then the usage's overrides."""
    generation = CONFIG["generation"]
    merged = {key: value for key, value in generation.items() if not isinstance(value, dict)}
    merged.update(generation.get(usage, {}))
    return merged


def path(relative):
    return ROOT / relative
