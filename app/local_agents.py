"""Small local-agent layer backed entirely by Ollama on localhost.

Agents are roles, not separate cloud services.  They all use the same local
Ollama server and can receive OCR text and, for vision-capable models, the
original image.  This keeps the portable app offline-first while giving the
user explicit local AI roles for OCR structuring and study work.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import local_ai, prompts
from .config import cfg


@dataclass(frozen=True)
class LocalAgent:
    name: str
    description: str
    prompt_builder: callable
    vision: bool = True


AGENTS = {
    "OCR Structure": LocalAgent(
        "OCR Structure",
        "Reads the complete OCR plus the picture and identifies title, sections, columns and vocabulary pairs.",
        lambda text: prompts.ai_smart(text),
        True,
    ),
    "Vocabulary": LocalAgent(
        "Vocabulary",
        "Extracts every useful bilingual pair present in the supplied OCR without inventing entries.",
        lambda text: (
            f"The learner studies {cfg['lang']} and speaks {cfg['native']}. "
            "Extract EVERY vocabulary pair present in the source. Do not cap the number of entries and do not invent. "
            "Return one line per pair as: - **source** — translation.\n\nSOURCE:\n" + text
        ),
        True,
    ),
    "Study Tutor": LocalAgent(
        "Study Tutor",
        "Creates local explanations, examples and review material from the OCR result.",
        lambda text: (
            f"The learner studies {cfg['lang']} at {cfg['level']} level and speaks {cfg['native']}. "
            "Use only the supplied source. Explain and teach it concisely; never invent vocabulary.\n\nSOURCE:\n" + text
        ),
        False,
    ),
}


def names() -> list[str]:
    return list(AGENTS)


def describe() -> list[dict[str, object]]:
    return [{"name": a.name, "description": a.description, "vision": a.vision} for a in AGENTS.values()]


def run(name: str, text: str, image=None, timeout: int = 300) -> str:
    """Run one named local agent through Ollama."""
    try:
        agent = AGENTS[name]
    except KeyError:
        raise ValueError(f"Unknown local AI agent: {name}") from None
    prompt = agent.prompt_builder(str(text or ""))
    return local_ai.generate(
        cfg["ollama_url"], cfg["model"], prompt,
        image if agent.vision else None,
        timeout=timeout,
    )


def status() -> tuple[bool, list[str], str]:
    """Return the current local Ollama status for the UI."""
    return local_ai.status(cfg["ollama_url"])
