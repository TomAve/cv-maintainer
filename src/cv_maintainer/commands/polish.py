"""Commande `cv polish` : l'agent relit les bullets et propose des reformulations.

Stub fonctionnel : on prend les bullets en bloc, on demande à l'agent ses
suggestions, on les présente une par une avec accept/skip/edit.
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ..llm import Message, build_client
from ..store import load_cv, save_cv

console = Console()


SYSTEM_PROMPT = """Tu relis les bullets d'un CV bilingue FR/EN pour les
améliorer. Pour chaque bullet, tu peux :
- proposer une reformulation plus percutante (verbe d'action fort, impact)
- corriger une faute, un anglicisme, une formulation lourde
- ne rien changer si c'est déjà bon

Renvoie un JSON unique au format :
{
  "suggestions": [
    {
      "bullet_id": "oqlf-1",
      "current_fr": "...",
      "current_en": "...",
      "suggested_fr": "...",
      "suggested_en": "...",
      "rationale": "Pourquoi cette suggestion (1 phrase courte)"
    }
  ]
}

Ne propose que des changements qui améliorent VRAIMENT — n'invente pas de
modifs cosmétiques juste pour en avoir. Mieux vaut 3 bonnes suggestions que 20
suggestions inutiles.
"""

REFINE_SYSTEM_PROMPT = """Tu affines la reformulation d'un bullet de CV bilingue FR/EN
en tenant compte du feedback de l'utilisateur.

Renvoie uniquement un objet JSON :
{
  "bullet_id": "...",
  "current_fr": "...",
  "current_en": "...",
  "suggested_fr": "...",
  "suggested_en": "...",
  "rationale": "Ce que tu as changé par rapport à la suggestion précédente (1 phrase)"
}
"""


def _gather_bullets(cv: dict[str, Any]) -> list[dict[str, Any]]:
    bullets = []
    for exp in cv.get("experiences", []) or []:
        for b in exp.get("bullets", []) or []:
            bullets.append({
                "bullet_id": b.get("id"),
                "context": exp.get("company"),
                "fr": b.get("fr", ""),
                "en": b.get("en", ""),
            })
    return bullets


def _refine_suggestion(client: Any, sug: dict[str, Any], feedback: str) -> dict[str, Any]:
    payload = {
        "bullet_id": sug.get("bullet_id"),
        "current_fr": sug.get("current_fr"),
        "current_en": sug.get("current_en"),
        "previous_suggested_fr": sug.get("suggested_fr"),
        "previous_suggested_en": sug.get("suggested_en"),
        "user_feedback": feedback,
    }
    result = client.complete_json(
        [Message(role="user", content=json.dumps(payload, ensure_ascii=False))],
        system=REFINE_SYSTEM_PROMPT,
        max_tokens=2048,
    )
    return result


def _apply_suggestion(cv: dict[str, Any], suggestion: dict[str, Any]) -> bool:
    target_id = suggestion.get("bullet_id")
    for exp in cv.get("experiences", []) or []:
        for b in exp.get("bullets", []) or []:
            if b.get("id") == target_id:
                b["fr"] = suggestion["suggested_fr"]
                b["en"] = suggestion["suggested_en"]
                return True
    return False


def run() -> int:
    cv = load_cv()
    client = build_client()
    bullets = _gather_bullets(cv)
    if not bullets:
        console.print("[yellow]Aucun bullet à relire.[/yellow]")
        return 0

    user_payload = json.dumps({"bullets": bullets}, ensure_ascii=False)
    with console.status("[dim]L'agent relit ton CV…[/dim]"):
        result = client.complete_json(
            [Message(role="user", content=user_payload)],
            system=SYSTEM_PROMPT,
            max_tokens=8192,
        )

    suggestions = result.get("suggestions", [])
    if not suggestions:
        console.print("[green]Aucune amélioration suggérée. Ton CV est déjà propre.[/green]")
        return 0

    applied = 0
    stopped = False
    for sug in suggestions:
        if stopped:
            break
        while True:
            console.print(
                Panel(
                    f"[bold]Bullet :[/bold] {sug.get('bullet_id')}\n"
                    f"[dim]Raison :[/dim] {sug.get('rationale', '')}\n\n"
                    f"[red]- FR :[/red] {sug.get('current_fr')}\n"
                    f"[green]+ FR :[/green] {sug.get('suggested_fr')}\n\n"
                    f"[red]- EN :[/red] {sug.get('current_en')}\n"
                    f"[green]+ EN :[/green] {sug.get('suggested_en')}",
                    border_style="cyan",
                )
            )
            choice = Prompt.ask("Appliquer ? [o/n/f/stop]", choices=["o", "n", "f", "stop"], default="n")
            if choice == "stop":
                stopped = True
                break
            if choice == "o":
                if _apply_suggestion(cv, sug):
                    applied += 1
                break
            if choice == "n":
                break
            if choice == "f":
                feedback = Prompt.ask("Ton feedback pour l'agent")
                with console.status("[dim]L'agent affine la suggestion…[/dim]"):
                    sug = _refine_suggestion(client, sug, feedback)

    if applied:
        save_cv(cv)
        console.print(
            f"[green]{applied} suggestion(s) applied.[/green] "
            "Lance `cv render` pour régénérer les .docx."
        )
    else:
        console.print("[yellow]Aucune modification appliquée.[/yellow]")
    return 0
