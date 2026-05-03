"""Commande `cv add` : dialogue avec l'agent pour ajouter une expérience/projet.

Flow :
1. L'utilisateur décrit sa nouvelle expérience en langage naturel.
2. L'agent pose des questions de relance jusqu'à avoir assez de matière.
3. Quand il s'estime prêt, l'agent renvoie un JSON structuré (entrée à ajouter).
4. On affiche un diff propre et on applique sur validation.
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax

from ..llm import LLMClient, Message, build_client
from ..store import load_cv, save_cv

console = Console()


SYSTEM_PROMPT = """Tu es un assistant qui aide Tom à maintenir son CV bilingue (FR/EN).

Ton rôle dans cette conversation : recueillir les informations nécessaires pour
ajouter une nouvelle expérience professionnelle ou un projet à son CV, puis
produire une entrée structurée propre.

Règles :
- Pose UNE question à la fois, pas plus.
- Cherche surtout : entreprise, rôle, dates de début/fin, 3 à 6 bullets
  factuels avec impact mesurable si possible.
- Pour chaque bullet : action concrète + technologie + résultat/impact si dispo.
- Reformule de manière professionnelle, en français correct ET anglais correct.
- Ne sois pas trop verbeux : ton CV doit rester lisible.
- Utilise des verbes d'action forts (Conception, Implémentation, Migration…
  / Designed, Built, Migrated…) et évite "Responsable de" / "Responsible for".

Quand tu juges avoir assez d'infos, et UNIQUEMENT à ce moment, réponds avec un
objet JSON unique (pas de texte autour) au format suivant :

{
  "kind": "experience" | "project",
  "ready": true,
  "entry": {
    "id": "slug-court",
    "company": "Nom officiel",
    "location": "Ville, Pays",
    "role": {"fr": "...", "en": "..."},
    "start": "YYYY-MM",
    "end": "YYYY-MM" | null,
    "bullets": [
      {
        "id": "slug-1",
        "fr": "...",
        "en": "...",
        "tags": ["mot-clé", "techno"],
        "core": true
      }
    ]
  }
}

Tant que tu n'es pas prêt, réponds normalement en texte (questions de relance).
"""


def _try_parse_entry(text: str) -> dict[str, Any] | None:
    """Tente d'extraire le JSON d'entrée final s'il est présent."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict) and parsed.get("ready") and "entry" in parsed:
        return parsed
    return None


def _show_entry(entry: dict[str, Any]) -> None:
    formatted = json.dumps(entry, ensure_ascii=False, indent=2)
    console.print(Panel(Syntax(formatted, "json", theme="ansi_dark"), title="Entrée proposée"))


def run() -> int:
    cv = load_cv()
    client: LLMClient = build_client()

    console.print(
        Panel.fit(
            "[bold]cv add[/bold] — décris ta nouvelle expérience/projet en quelques phrases.\n"
            "Tape [italic]exit[/italic] pour annuler.",
            border_style="cyan",
        )
    )

    history: list[Message] = []
    first_message = Prompt.ask("[bold green]Toi[/bold green]")
    if first_message.strip().lower() in {"exit", "quit"}:
        console.print("Annulé.")
        return 0
    history.append(Message(role="user", content=first_message))

    while True:
        with console.status("[dim]L'agent réfléchit…[/dim]"):
            resp = client.chat(history, system=SYSTEM_PROMPT, max_tokens=2048)
        text = resp.text.strip()

        # Cas 1 : l'agent a produit l'entrée finale.
        proposal = _try_parse_entry(text)
        if proposal is not None:
            console.print()
            _show_entry(proposal["entry"])
            decision = Prompt.ask(
                "Ajouter cette entrée au cv.yaml ?",
                choices=["o", "n", "modifier"],
                default="o",
            )
            if decision == "o":
                kind = proposal.get("kind", "experience")
                target_key = "projects" if kind == "project" else "experiences"
                cv.setdefault(target_key, []).append(proposal["entry"])
                save_cv(cv)
                console.print(
                    f"[green]✔ Ajouté à `{target_key}` dans data/cv.yaml.[/green] "
                    "Lance `cv render` pour régénérer les .docx."
                )
                return 0
            if decision == "modifier":
                feedback = Prompt.ask("[bold green]Toi[/bold green] (correction à apporter)")
                history.append(Message(role="assistant", content=text))
                history.append(Message(role="user", content=feedback))
                continue
            console.print("[yellow]Annulé. cv.yaml inchangé.[/yellow]")
            return 0

        # Cas 2 : question de relance.
        console.print(f"\n[bold cyan]Agent[/bold cyan] : {text}\n")
        user_reply = Prompt.ask("[bold green]Toi[/bold green]")
        if user_reply.strip().lower() in {"exit", "quit"}:
            console.print("[yellow]Annulé.[/yellow]")
            return 0
        history.append(Message(role="assistant", content=text))
        history.append(Message(role="user", content=user_reply))
