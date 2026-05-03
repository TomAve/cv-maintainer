"""Configuration : variables d'env, chargement du .env, chemins du projet."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(env_path: Path) -> None:
    """Mini parseur .env, sans dépendance externe (python-dotenv)."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


# Racine du projet : src/cv_maintainer/config.py -> cv-maintainer/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
TEMPLATE_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

CV_PATH = DATA_DIR / "cv.yaml"
STYLE_PATH = DATA_DIR / "style.md"

_load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    api_key: str | None

    @classmethod
    def load(cls) -> "Settings":
        provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
        default_models = {
            "anthropic": "claude-sonnet-4-6",
            "gemini": "gemini-2.5-flash",
            "openai": "gpt-4o-mini",
        }
        model = os.environ.get("LLM_MODEL", default_models.get(provider, ""))
        key_env = {
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
        }.get(provider)
        api_key = os.environ.get(key_env) if key_env else None
        return cls(provider=provider, model=model, api_key=api_key)
