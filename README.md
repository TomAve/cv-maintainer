# cv-maintainer

A small CLI tool for maintaining and evolving a bilingual (FR/EN) CV with an
LLM agent. The single source of truth is `data/cv.yaml`; `.docx` files are
generated on demand.

## Architecture

```
cv.yaml  (bilingual source)
   │
   ├── cv add        → agent gathers details and adds a new experience entry
   ├── cv polish     → agent reviews bullets and suggests reformulations
   ├── cv target X   → agent generates a tailored variant for a job posting
   └── cv render     → regenerates cv_master.fr.docx and cv_master.en.docx
```

The LLM is abstracted behind a provider interface ([src/cv_maintainer/llm.py](src/cv_maintainer/llm.py)).
Default backend: **Anthropic Claude**. To switch to Gemini or OpenAI, install
the corresponding SDK and set `LLM_PROVIDER` in `.env`.

## Installation

```bash
# Requires Python 3.10+
cd cv-maintainer

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

Get an API key at https://console.anthropic.com.

## Usage

### Add an experience or project

```bash
cv add
```

The agent asks a few questions, proposes a structured entry, and waits for
confirmation before updating `cv.yaml` (a timestamped backup is created).

### Regenerate .docx files

```bash
cv render
```

Produces `outputs/cv_master.fr.docx` and `outputs/cv_master.en.docx`.

### Review and improve style

```bash
cv polish
```

The agent reviews each bullet and proposes reformulations one at a time.

### Target a job posting

```bash
cv target posting.txt --lang fr
```

The agent reads `posting.txt`, selects relevant bullets, and generates
`outputs/cv_posting.fr.docx`.

## API costs

This tool calls the LLM API directly — there is no subscription. Costs are
billed per token by Anthropic (or whichever provider is configured).

Typical cost per session is well under $0.10 with Claude Sonnet, and
negligible with Claude Haiku. For reference pricing, see
https://www.anthropic.com/pricing.

## Project structure

```
cv-maintainer/
├── pyproject.toml
├── .env.example
├── data/
│   ├── cv.yaml          ← bilingual source of truth
│   └── style.md         ← agent style memory
├── outputs/             ← generated .docx files (gitignored)
├── templates/           ← reserved for future Word templates
└── src/cv_maintainer/
    ├── cli.py           ← entry point: `cv <command>`
    ├── config.py        ← .env loading, paths
    ├── llm.py           ← provider-agnostic LLM adapter
    ├── store.py         ← cv.yaml read/write
    ├── renderer.py      ← YAML → .docx
    └── commands/        ← one file per command
        ├── add.py
        ├── polish.py
        ├── render.py
        └── target.py
```

## Roadmap

- `cv chat` — free conversational mode beyond structured entry.
- Auto-inject `style.md` into all prompts.
- Preserve YAML comments (migrate to `ruamel.yaml`).
- Visual Word templates via `docxtpl`.
- PDF export alongside .docx.
- LinkedIn import (PDF export parsing).

## Switching LLM provider

Edit `.env`:

```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_key
```

Then install the SDK: `pip install google-genai`.

The `GeminiClient` class is already wired in [src/cv_maintainer/llm.py](src/cv_maintainer/llm.py);
additional providers can be added following the same pattern.
