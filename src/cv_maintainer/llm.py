"""Adaptateur LLM provider-agnostic.

L'idée : tout le reste du code parle uniquement à `LLMClient`. Pour ajouter un
provider, on crée une nouvelle implémentation et on l'enregistre dans
`build_client()`. Le reste de l'app n'a rien à changer.

Choix de design :
- Interface volontairement minimaliste (chat + complete_json).
- On force les sorties structurées via JSON (portable, contrairement au tool
  calling natif qui diffère entre providers).
- Pas de streaming pour la v1 (à ajouter si tu veux le rendu progressif).
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .config import Settings


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatResponse:
    text: str
    raw: Any = field(default=None, repr=False)
    # Estimation grossière des coûts pour donner un repère à l'utilisateur.
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMClient(ABC):
    """Contrat minimal qu'un provider doit implémenter."""

    name: str = "unknown"

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ChatResponse:
        """Échange conversationnel classique."""

    def complete_json(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Demande une sortie JSON et la parse.

        Implémentation par défaut : on appelle `chat()` en injectant une
        instruction stricte sur le format. Les providers qui supportent un mode
        JSON natif peuvent override cette méthode.
        """
        json_instruction = (
            "IMPORTANT : ta réponse doit être un objet JSON valide et UNIQUEMENT "
            "ce JSON. Pas de texte avant, pas de texte après, pas de bloc ```."
        )
        merged_system = (system + "\n\n" + json_instruction) if system else json_instruction
        response = self.chat(
            messages,
            system=merged_system,
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return _parse_json_loose(response.text)


def _parse_json_loose(text: str) -> dict[str, Any]:
    """Extrait du JSON même s'il est entouré de fences markdown."""
    cleaned = text.strip()
    # Retirer un éventuel fence ```json ... ```
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, flags=re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback : trouver le premier { et le dernier } équilibré
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


# ---------------------------------------------------------------------------
# Implémentation Anthropic
# ---------------------------------------------------------------------------


class AnthropicClient(LLMClient):
    name = "anthropic"

    def __init__(self, model: str, api_key: str | None = None) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Le package `anthropic` est requis. Installe-le : pip install anthropic"
            ) from exc
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY manquante. Renseigne-la dans .env ou en variable d'env."
            )
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ChatResponse:
        # L'API Anthropic veut le system à part et le reste sous forme
        # [{role, content}]. On filtre les messages "system" éventuels.
        anthropic_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in {"user", "assistant"}
        ]
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages,
        }
        if system:
            kwargs["system"] = system

        resp = self._client.messages.create(**kwargs)
        # Concatène tous les blocs texte (l'API peut renvoyer plusieurs blocks).
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        usage = getattr(resp, "usage", None)
        return ChatResponse(
            text=text,
            raw=resp,
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
        )


# ---------------------------------------------------------------------------
# Squelettes pour Gemini / OpenAI — décommenter et installer le SDK pour activer
# ---------------------------------------------------------------------------


class GeminiClient(LLMClient):  # pragma: no cover - exemple
    name = "gemini"

    def __init__(self, model: str, api_key: str | None = None) -> None:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError(
                "Le package `google-genai` est requis pour utiliser Gemini."
            ) from exc
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY manquante.")
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ChatResponse:
        # Gemini attend un format différent : on aplatit en string.
        prompt_parts = []
        if system:
            prompt_parts.append(f"[Instructions système]\n{system}\n")
        for m in messages:
            if m.role == "user":
                prompt_parts.append(f"[Utilisateur]\n{m.content}\n")
            elif m.role == "assistant":
                prompt_parts.append(f"[Assistant]\n{m.content}\n")
        prompt = "\n".join(prompt_parts)
        resp = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config={"max_output_tokens": max_tokens, "temperature": temperature},
        )
        return ChatResponse(text=resp.text or "", raw=resp)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or Settings.load()
    if settings.provider == "anthropic":
        return AnthropicClient(settings.model, settings.api_key)
    if settings.provider == "gemini":
        return GeminiClient(settings.model, settings.api_key)
    raise RuntimeError(f"Provider non supporté : {settings.provider}")
