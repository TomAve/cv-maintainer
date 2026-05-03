# cv-maintainer

Petit outil CLI pour maintenir et faire évoluer ton CV bilingue (FR/EN) avec
un agent LLM. La source de vérité est un fichier `data/cv.yaml` ; les `.docx`
sont des livrables qu'on régénère à la volée.

## Architecture en bref

```
cv.yaml  (source bilingue)
   │
   ├── cv add        → l'agent dialogue avec toi pour ajouter une expérience
   ├── cv polish     → l'agent relit et propose des reformulations
   ├── cv target X   → l'agent génère une variante ciblée pour une offre
   └── cv render     → régénère cv_master.fr.docx et cv_master.en.docx
```

Le LLM est abstrait derrière une interface (`src/cv_maintainer/llm.py`).
Backend par défaut : **Anthropic Claude**. Pour brancher Gemini/OpenAI, il
suffit d'installer le SDK correspondant et de changer `LLM_PROVIDER` dans
`.env`.

## Installation (en local)

```bash
# Pré-requis : Python 3.10+
cd cv-maintainer

python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -e .

cp .env.example .env
# Édite .env et colle ta clé ANTHROPIC_API_KEY
```

Récupère une clé API Anthropic sur https://console.anthropic.com (premier
crédit offert pour tester).

## Utilisation

### Ajouter une expérience ou un projet

```bash
cv add
```

L'agent te pose des questions, propose une entrée structurée, tu valides ou
corriges. Le `cv.yaml` est mis à jour (un backup horodaté est créé).

### Régénérer les .docx

```bash
cv render
```

Génère `outputs/cv_master.fr.docx` et `outputs/cv_master.en.docx`.

### Relire et améliorer le style

```bash
cv polish
```

L'agent relit tes bullets et propose des reformulations, une par une,
acceptables ou non.

### Cibler une offre d'emploi

```bash
cv target offre.txt --lang fr
```

L'agent lit `offre.txt`, sélectionne les bullets pertinents, génère
`outputs/cv_offre.fr.docx`.

## Coûts

Tu paies les tokens consommés à l'API. Estimation par session :

| Modèle             | Coût typique  |
| ------------------ | ------------- |
| Claude Sonnet 4.6  | 0,05 – 0,15 € |
| Claude Haiku 4.5   | 0,01 – 0,03 € |

Sur un mois normal : **moins de 1 € au total**. Pas d'abonnement, pas de
minimum, tu paies à l'usage.

## Structure du projet

```
cv-maintainer/
├── pyproject.toml
├── .env.example
├── data/
│   ├── cv.yaml          ← source de vérité bilingue
│   └── style.md         ← mémoire de style de l'agent
├── outputs/             ← .docx générés (gitignore-ables)
├── templates/           ← réservé pour de futurs templates Word
└── src/cv_maintainer/
    ├── cli.py           ← point d'entrée `cv <commande>`
    ├── config.py        ← chargement .env, paths
    ├── llm.py           ← adaptateur provider-agnostic
    ├── store.py         ← lecture/écriture cv.yaml
    ├── renderer.py      ← YAML → .docx
    └── commands/        ← une commande par fichier
        ├── add.py
        ├── polish.py
        ├── render.py
        └── target.py
```

## Roadmap idées

- `cv chat` — mode conversationnel libre (au-delà de l'ajout).
- Lecture du `style.md` injectée automatiquement dans tous les prompts.
- Conservation des commentaires YAML (passage à `ruamel.yaml`).
- Templates Word visuels (via `docxtpl`) pour des designs custom.
- Export PDF en plus du .docx.
- Import depuis LinkedIn (parsing du PDF d'export).

## Changer de provider LLM

Édite `.env` :

```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=ta_clé
```

Puis installe le SDK : `pip install google-genai`.

Le code `GeminiClient` est déjà câblé dans `llm.py` ; tu peux ajouter
d'autres providers en suivant le même patron.
