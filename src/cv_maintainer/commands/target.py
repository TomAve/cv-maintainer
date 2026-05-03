"""Commande `cv target` : génère une variante du CV ciblée pour une offre.

Usage : `cv target chemin/vers/offre.txt --lang fr`
L'agent lit l'offre, choisit les bullets les plus pertinents (sans les
modifier), reformule éventuellement la headline, et écrit la variante en .docx.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

from ..config import OUTPUT_DIR
from ..llm import Message, build_client
from ..renderer import render
from ..store import load_cv

console = Console()


SYSTEM_PROMPT = """Tu reçois (1) le CV master de Tom au format JSON, et (2) le
texte d'une offre d'emploi. Ta tâche : produire une SÉLECTION ciblée des
bullets qui correspondent le mieux à l'offre.

Règles :
- Tu ne reformules PAS les bullets existants (sauf demande explicite).
- Tu sélectionnes les expériences ET les bullets pertinents (par leur id).
- L'ordre des expériences reste chronologique inversé.
- Tu peux suggérer une nouvelle headline ciblée pour l'offre.

Renvoie un JSON unique :
{
  "headline": {"fr": "...", "en": "..."},
  "selected": [
    {"experience_id": "oqlf", "bullet_ids": ["oqlf-1", "oqlf-3"]},
    {"experience_id": "k2geospatial", "bullet_ids": ["k2-2", "k2-3"]}
  ],
  "rationale": "Pourquoi cette sélection (2-3 phrases)"
}
"""


def _filter_cv(cv: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    """Construit une copie filtrée du CV selon la sélection de l'agent."""
    selected_map = {s["experience_id"]: set(s["bullet_ids"]) for s in selection.get("selected", [])}
    new_cv = json.loads(json.dumps(cv))  # deep copy
    if selection.get("headline"):
        new_cv.setdefault("profile", {})["headline"] = selection["headline"]

    filtered_exp = []
    for exp in new_cv.get("experiences", []) or []:
        if exp.get("id") not in selected_map:
            continue
        keep = selected_map[exp["id"]]
        exp["bullets"] = [b for b in (exp.get("bullets") or []) if b.get("id") in keep]
        if exp["bullets"]:
            filtered_exp.append(exp)
    new_cv["experiences"] = filtered_exp
    return new_cv


def run(offer_path: str, lang: str = "fr", out_name: str | None = None) -> int:
    offer_text = Path(offer_path).read_text(encoding="utf-8")
    cv = load_cv()
    client = build_client()

    user_payload = json.dumps({"cv": cv, "offer": offer_text}, ensure_ascii=False)
    with console.status("[dim]L'agent analyse l'offre…[/dim]"):
        selection = client.complete_json(
            [Message(role="user", content=user_payload)],
            system=SYSTEM_PROMPT,
            max_tokens=4096,
        )

    console.print(
        Panel(
            selection.get("rationale", ""),
            title="Logique de sélection",
            border_style="cyan",
        )
    )

    variant = _filter_cv(cv, selection)
    out_name = out_name or Path(offer_path).stem
    out_path = OUTPUT_DIR / f"cv_{out_name}.{lang}.docx"
    render(variant, lang, out_path)
    console.print(f"[green]✔ Variante générée :[/green] {out_path}")
    return 0
