"""Point d'entrée CLI. `cv <commande>` une fois le package installé."""

from __future__ import annotations

import sys

import click

from .commands import add as add_cmd
from .commands import polish as polish_cmd
from .commands import render as render_cmd
from .commands import target as target_cmd


@click.group(help="Outil de maintenance bilingue de CV via un agent LLM.")
def main() -> None:
    pass


@main.command("add", help="Dialogue interactif pour ajouter une expérience ou un projet.")
def cmd_add() -> None:
    sys.exit(add_cmd.run())


@main.command("render", help="Régénère cv_master.fr.docx et cv_master.en.docx.")
def cmd_render() -> None:
    sys.exit(render_cmd.run())


@main.command("polish", help="L'agent relit ton CV et propose des reformulations.")
def cmd_polish() -> None:
    sys.exit(polish_cmd.run())


@main.command("target", help="Génère une variante ciblée pour une offre d'emploi.")
@click.argument("offer_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--lang", type=click.Choice(["fr", "en"]), default="fr", show_default=True)
@click.option("--name", "out_name", default=None, help="Suffixe du fichier de sortie.")
def cmd_target(offer_path: str, lang: str, out_name: str | None) -> None:
    sys.exit(target_cmd.run(offer_path, lang=lang, out_name=out_name))


if __name__ == "__main__":
    main()
