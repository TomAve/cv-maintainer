"""Lecture/écriture du cv.yaml + petits utilitaires de manipulation.

On réécrit le YAML à plat pour préserver la structure mais on perd les
commentaires (limitation connue de PyYAML). Si tu veux les conserver, on
pourra basculer sur ruamel.yaml plus tard.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .config import CV_PATH


def load_cv(path: Path | None = None) -> dict[str, Any]:
    path = path or CV_PATH
    if not path.exists():
        raise FileNotFoundError(f"cv.yaml introuvable à : {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_cv(data: dict[str, Any], path: Path | None = None, *, backup: bool = True) -> Path:
    """Sauvegarde le YAML. Crée un backup horodaté avant écrasement."""
    path = path or CV_PATH
    if backup and path.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = path.with_suffix(f".yaml.{ts}.bak")
        shutil.copy2(path, backup_path)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=100,
        )
    return path


def localized(value: Any, lang: str) -> str:
    """Récupère la version FR ou EN d'un champ.

    Accepte :
    - un dict {fr, en}            → renvoie la langue demandée
    - une string                  → renvoie tel quel (champs neutres)
    - None                        → renvoie ""
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if lang in value:
            return value[lang] or ""
        # Fallback sur l'autre langue si l'une des deux est vide.
        for fallback_lang in ("fr", "en"):
            if value.get(fallback_lang):
                return value[fallback_lang]
        return ""
    return str(value)
