"""
prompts.py - the instructions sent to the LOCAL AI model (Ollama).

ACTIONS maps a button label to (prompt builder, placement):
    "replace" -> the answer replaces the selected lines (or the whole editor)
    "append"  -> the answer is added at the end of the editor
Add an entry and the editor creates the button automatically.

ai_smart() builds the prompt of the third OCR mode, "AI Smart".

Rule used in every prompt: the AI must never invent text that is not in the picture / OCR text.
"""
from .config import cfg


def ctx() -> str:
    """One-sentence learner profile placed at the start of prompts."""
    return f"The learner is studying {cfg['lang']}, native language {cfg['native']}, level {cfg['level']}. "


NO_INVENT = "Do not invent words that are not in the text. If something is unclear, keep it as written. "
FMT = "Vocabulary lines must look exactly like: - **word** — meaning. "

ACTIONS = {
    "✨ Learn This": (lambda t: ctx() + NO_INVENT + "Turn this text into learning notes in Markdown: a # title, the cleaned "
                      "original, ## Translation, ## Vocabulary (useful words for this level, base forms), ## Grammar note. "
                      + FMT + "Return only Markdown.\n\n" + t, "append"),
    "Clean": (lambda t: ctx() + NO_INVENT + "Fix obvious OCR mistakes only, keep the original language, organise as Markdown "
              "with # / ## / ### headings and - bullets. " + FMT + "Return only Markdown.\n\n" + t, "replace"),
    "📊 Table": (lambda t: ctx() + NO_INVENT + f"Organise this text into a Markdown table with two columns: "
                 f"{cfg['lang']} | {cfg['native']}. Pair each phrase with its translation. Return only the table.\n\n" + t, "replace"),
    "Translate": (lambda t: f"Translate to {cfg['native']}. Return only the translation.\n\n" + t, "append"),
    "Explain": (lambda t: ctx() + "Explain this word/sentence: meaning, pronunciation, base form, part of speech, "
                "2 short example sentences with translations. Short Markdown.\n\n" + t, "append"),
    "Vocabulary": (lambda t: ctx() + NO_INVENT + "Extract the most useful vocabulary as bullets. " + FMT + "Only bullets.\n\n" + t, "append"),
    "Flashcards": (lambda t: ctx() + NO_INVENT + "Make flashcards. " + FMT + "Front = target language, back = meaning. Only bullets.\n\n" + t, "append"),
}


def ai_smart(hint: str) -> str:
    """Prompt for 'AI Smart' OCR: picture + OCR text in, structured study notes out."""
    return (ctx() + "You are given a picture (a language-learning poster, flashcard or screenshot) and the text an OCR "
            "program read from it. Write clean study notes in Markdown with EXACTLY this structure:\n"
            "# Main title (the title shown in the picture; if there is none, a short descriptive title)\n"
            "## Heading (one for each section or category in the picture; if there is only one, write 'Vocabulary')\n"
            "### Subheading (optional, for a sub-group)\n"
            f"- **{cfg['lang']} word or phrase** — {cfg['native']} translation (one bullet per item)\n"
            "Rules: include EVERY item that is visible in the picture or in the OCR text; copy each word exactly as written "
            "(fix only clear OCR mistakes such as missing letters or diacritics); never invent items; ignore app and "
            "social-media interface text (user names, likes, times, buttons); return ONLY the Markdown.\n\n"
            "OCR text:\n" + hint)
