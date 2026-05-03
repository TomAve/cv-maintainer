"""Commande `cv render` : régénère les fichiers .docx à partir du cv.yaml."""

from __future__ import annotations

from rich.console import Console

from ..renderer import render_all

console = Console()


def run() -> int:
    paths = render_all()
    for p in paths:
        console.print(f"[green]✔[/green] généré : {p}")
    return 0
