"""Synchronous Gemini command-plan generation using google-generativeai."""
from __future__ import annotations

try:
    import google.generativeai as genai
except ImportError as exc:  # pragma: no cover - environment dependent
    raise RuntimeError("google-generativeai is not installed. Run: pip install -r requirements.txt") from exc

from ..config import GEMINI_API_KEY, GEMINI_MODEL, SAFETY_RULES_PATH


class GeminiClient:
    def __init__(self, model_name: str = GEMINI_MODEL) -> None:
        genai.configure(api_key=GEMINI_API_KEY)
        safety_rules = self._load_safety_rules()
        system_instruction = (
            safety_rules
            + "\n\nOUTPUT FORMAT (mandatory): output only a numbered list, one shell command per line, "
            "numbered 1., 2., 3., etc. No prose, heading, Markdown fence, explanation, or blank command. "
            "Commands must be simple, auditable, and scoped to the sandbox current directory. "
            "Do not include commands that use sudo or mutate the host system."
        )
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            generation_config={"temperature": 0.1, "max_output_tokens": 1200},
        )

    @staticmethod
    def _load_safety_rules() -> str:
        try:
            return SAFETY_RULES_PATH.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Could not read Gemini safety rules at {SAFETY_RULES_PATH}: {exc}") from exc

    @staticmethod
    def _context_text(context: list[dict]) -> str:
        if not context:
            return "No matching corpus chunks were retrieved."
        sections: list[str] = []
        for index, chunk in enumerate(context, start=1):
            sections.append(
                "[Context {0} | source={1} | score={2:.3f}]\n{3}".format(
                    index,
                    chunk.get("source", "unknown"),
                    float(chunk.get("score", 0.0)),
                    str(chunk.get("text", "")),
                )
            )
        return "\n\n".join(sections)

    def generate_command_plan(
        self, query: str, context: list[dict], repair_response: str | None = None
    ) -> str:
        prompt = (
            "User task:\n" + query.strip() + "\n\n"
            "Retrieved local context:\n" + self._context_text(context) + "\n\n"
            "Produce a safe, minimal command plan for this task. The commands will be shown to a human "
            "and executed individually only after approval inside a Bubblewrap sandbox whose current "
            "directory maps to ~/Games/cs16. Use relative paths. Do not assume host packages can be "
            "installed from inside the sandbox. Do not invent download URLs. If the task cannot be "
            "completed safely or accurately with available information, return a harmless inspection "
            "command or no commands only if truly necessary; do not explain in prose."
        )
        if repair_response is not None:
            prompt += (
                "\n\nYour previous response did not match the required format. Previous response:\n"
                + repair_response[:6000]
                + "\nRewrite it now as a numbered list with one shell command per line only. No prose or fences."
            )
        try:
            response = self.model.generate_content(prompt)
        except Exception as exc:
            message = str(exc)
            lowered = message.lower()
            if any(marker in lowered for marker in ("429", "quota", "rate limit", "resource_exhausted", "too many requests")):
                raise RuntimeError(
                    "Gemini API rate limit or quota reached. Wait for quota reset or review your Google AI Studio API limits."
                ) from exc
            if any(marker in lowered for marker in ("api key", "401", "403", "unauthorized", "permission denied")):
                raise RuntimeError(
                    "Gemini authentication failed. Check GEMINI_API_KEY in the project .env file and confirm API access."
                ) from exc
            raise RuntimeError(f"Gemini API request failed: {message}") from exc
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Gemini returned an empty response. Try again or choose another GEMINI_MODEL.")
        return text.strip()
