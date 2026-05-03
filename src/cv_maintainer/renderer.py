"""Rendu cv.yaml → cv.docx, en FR ou EN.

Approche v1 : on génère le document programmatiquement avec python-docx, sans
template externe. Avantages :
- pas de fichier .docx fragile à maintenir
- entièrement reproductible
- facile à tweaker (couleurs, polices, espacements)

Si tu veux un design plus fin (logos, colonnes, etc.) plus tard, on pourra
basculer sur docxtpl + un template Word visuel.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor

from .config import OUTPUT_DIR
from .store import load_cv, localized

# Palette : sobre, lisible, un seul accent.
ACCENT = RGBColor(0x2E, 0x5C, 0x8A)  # bleu profond
DARK = RGBColor(0x22, 0x22, 0x22)
GREY = RGBColor(0x55, 0x55, 0x55)


# Étiquettes traduites pour les en-têtes de section.
LABELS = {
    "fr": {
        "experience": "Expérience professionnelle",
        "projects": "Projets",
        "education": "Formation",
        "skills": "Compétences",
        "skills_languages": "Langues",
        "skills_soft": "Compétences transverses",
        "skills_technical": "Compétences techniques",
        "tech_languages": "Langages",
        "tech_frontend": "Frontend",
        "tech_backend": "Backend",
        "tech_cloud": "Cloud / DevOps",
        "tech_tools": "Outils",
        "present": "aujourd'hui",
    },
    "en": {
        "experience": "Professional Experience",
        "projects": "Projects",
        "education": "Education",
        "skills": "Skills",
        "skills_languages": "Languages",
        "skills_soft": "Soft skills",
        "skills_technical": "Technical skills",
        "tech_languages": "Languages",
        "tech_frontend": "Frontend",
        "tech_backend": "Backend",
        "tech_cloud": "Cloud / DevOps",
        "tech_tools": "Tools",
        "present": "Present",
    },
}


def _format_date(date_str: str | None, lang: str) -> str:
    """Convertit '2023-11' en 'Nov. 2023' / 'Nov 2023'. Renvoie 'aujourd'hui' si None."""
    if not date_str:
        return LABELS[lang]["present"]
    parts = date_str.split("-")
    months_fr = [
        "janv.", "févr.", "mars", "avril", "mai", "juin",
        "juil.", "août", "sept.", "oct.", "nov.", "déc.",
    ]
    months_en = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    if len(parts) == 2:
        year, month = parts
        idx = int(month) - 1
        m = months_fr[idx] if lang == "fr" else months_en[idx]
        return f"{m} {year}"
    return date_str


def _add_horizontal_line(paragraph) -> None:
    """Ajoute une ligne horizontale fine en bas du paragraphe."""
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "2E5C8A")
    pBdr.append(bottom)
    pPr.append(pBdr)


def _section_heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text.upper())
    run.bold = True
    run.font.name = "Calibri"
    run.font.size = Pt(11)
    run.font.color.rgb = ACCENT
    _add_horizontal_line(p)


def _normal_run(paragraph, text: str, *, bold: bool = False, size: int = 10, color: RGBColor = DARK) -> None:
    run = paragraph.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = color


def _two_column_line(doc: Document, left: str, right: str, *, bold_left: bool = True) -> None:
    """Ligne avec texte à gauche et date à droite (via tab stop)."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(0)
    # Tab stop à droite à 16cm (largeur de page utile en A4 marges 2cm).
    p.paragraph_format.tab_stops.add_tab_stop(Cm(16), WD_PARAGRAPH_ALIGNMENT.RIGHT)
    _normal_run(p, left, bold=bold_left, size=10)
    p.add_run("\t")
    _normal_run(p, right, size=10, color=GREY)


def _bullet(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.left_indent = Cm(0.5)
    _normal_run(p, text, size=10)


def _setup_page(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)


def _render_header(doc: Document, profile: dict[str, Any], lang: str) -> None:
    name_p = doc.add_paragraph()
    name_p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    name_p.paragraph_format.space_after = Pt(2)
    _normal_run(name_p, profile.get("name", ""), bold=True, size=22, color=DARK)

    headline = localized(profile.get("headline"), lang)
    if headline:
        h_p = doc.add_paragraph()
        h_p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        h_p.paragraph_format.space_after = Pt(4)
        _normal_run(h_p, headline, size=12, color=ACCENT)

    contact_bits = []
    if profile.get("location"):
        contact_bits.append(profile["location"])
    if profile.get("phone"):
        contact_bits.append(profile["phone"])
    if profile.get("email"):
        contact_bits.append(profile["email"])
    for link in profile.get("links", []) or []:
        url = link.get("url", "")
        # On affiche l'URL "propre" sans https://
        clean = url.replace("https://", "").replace("http://", "")
        contact_bits.append(clean)

    if contact_bits:
        c_p = doc.add_paragraph()
        c_p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        c_p.paragraph_format.space_after = Pt(8)
        _normal_run(c_p, "  •  ".join(contact_bits), size=9, color=GREY)

    summary = localized(profile.get("summary"), lang)
    if summary:
        s_p = doc.add_paragraph()
        s_p.paragraph_format.space_after = Pt(6)
        _normal_run(s_p, summary, size=10)


def _render_experience(doc: Document, exp: dict[str, Any], lang: str) -> None:
    role = localized(exp.get("role"), lang)
    company = exp.get("company", "")
    location = exp.get("location", "")
    left_parts = [p for p in [role, company] if p]
    left = " — ".join(left_parts)
    if location:
        left += f" ({location})"
    right = f"{_format_date(exp.get('start'), lang)} – {_format_date(exp.get('end'), lang)}"
    _two_column_line(doc, left, right)

    for bullet in exp.get("bullets", []) or []:
        text = localized(bullet, lang)
        if text:
            _bullet(doc, text)


def _render_education(doc: Document, edu: dict[str, Any], lang: str) -> None:
    degree = localized(edu.get("degree"), lang)
    school = edu.get("school", "")
    location = edu.get("location", "")
    left = degree
    if school:
        left += f" — {school}"
    if location:
        left += f" ({location})"
    right = f"{_format_date(edu.get('start'), lang)} – {_format_date(edu.get('end'), lang)}"
    _two_column_line(doc, left, right)


def _render_skills(doc: Document, skills: dict[str, Any], lang: str) -> None:
    L = LABELS[lang]
    # Langues
    langs = skills.get("languages") or []
    if langs:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        _normal_run(p, f"{L['skills_languages']} : ", bold=True, size=10)
        formatted = []
        for entry in langs:
            name = localized(entry.get("name"), lang)
            level = localized(entry.get("level"), lang)
            formatted.append(f"{name} ({level})" if level else name)
        _normal_run(p, ", ".join(formatted), size=10)

    # Soft skills
    soft = skills.get("soft") or []
    if soft:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        _normal_run(p, f"{L['skills_soft']} : ", bold=True, size=10)
        _normal_run(p, ", ".join(localized(s, lang) for s in soft), size=10)

    # Technique : sous-catégories
    tech = skills.get("technical") or {}
    if isinstance(tech, dict):
        order = [
            ("languages", L["tech_languages"]),
            ("frontend", L["tech_frontend"]),
            ("backend", L["tech_backend"]),
            ("cloud", L["tech_cloud"]),
            ("tools", L["tech_tools"]),
        ]
        for key, label in order:
            items = tech.get(key) or []
            if not items:
                continue
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            _normal_run(p, f"{label} : ", bold=True, size=10)
            _normal_run(p, ", ".join(items), size=10)
    elif isinstance(tech, list):
        # fallback : liste à plat
        p = doc.add_paragraph()
        _normal_run(p, f"{L['skills_technical']} : ", bold=True, size=10)
        _normal_run(p, ", ".join(tech), size=10)


def render(cv: dict[str, Any], lang: str, output_path: Path) -> Path:
    """Génère un .docx depuis une structure cv (dict) pour la langue demandée."""
    if lang not in {"fr", "en"}:
        raise ValueError(f"Langue non supportée : {lang}")

    doc = Document()
    _setup_page(doc)

    # En-tête
    _render_header(doc, cv.get("profile", {}) or {}, lang)

    L = LABELS[lang]

    # Expériences
    experiences = cv.get("experiences") or []
    if experiences:
        _section_heading(doc, L["experience"])
        for exp in experiences:
            _render_experience(doc, exp, lang)

    # Projets
    projects = cv.get("projects") or []
    if projects:
        _section_heading(doc, L["projects"])
        for proj in projects:
            _render_experience(doc, proj, lang)  # même structure que expérience

    # Formation
    education = cv.get("education") or []
    if education:
        _section_heading(doc, L["education"])
        for edu in education:
            _render_education(doc, edu, lang)

    # Compétences
    skills = cv.get("skills") or {}
    if skills:
        _section_heading(doc, L["skills"])
        _render_skills(doc, skills, lang)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return output_path


def render_all(cv: dict[str, Any] | None = None, output_dir: Path | None = None) -> list[Path]:
    """Génère les deux versions (FR + EN) du CV master."""
    cv = cv if cv is not None else load_cv()
    output_dir = output_dir or OUTPUT_DIR
    paths = []
    for lang in ("fr", "en"):
        out = output_dir / f"cv_master.{lang}.docx"
        paths.append(render(cv, lang, out))
    return paths