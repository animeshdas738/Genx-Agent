from typing import Optional
import json

from src.config import settings

try:
    import openai
except Exception:
    openai = None


def call_openai_for_summary(description: str, facts: Optional[list] = None) -> dict:
    """Call OpenAI chat completion to generate a summary JSON.

    The function expects the model to return a JSON object with keys:
      - summary
      - suggested_solution
      - confidence (float 0..1)

    If OpenAI isn't configured (no API key or package), raises RuntimeError.
    """
    if openai is None or not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI not configured")

    openai.api_key = settings.OPENAI_API_KEY

    prompt = (
        "You are an assistant that converts a case description into a JSON object with keys:"
        " summary (short), suggested_solution (concise), confidence (float 0..1).\n\n"
        f"Description:\n{description}\n\n"
    )

    if facts:
        prompt += "Facts:\n" + "\n".join(facts) + "\n\n"

    # Try modern openai v1 chat API first (openai.chat.completions.create)
    text = None
    tokens = None
    try:
        if hasattr(openai, "chat") and hasattr(openai.chat, "completions"):
            resp = openai.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=500,
            )
            # resp.choices[0].message.content for older API; v1 returns resp.choices[0].message.content as well
            text = resp.choices[0].message.content.strip()
            try:
                tokens = resp.usage.total_tokens
            except Exception:
                tokens = getattr(resp, "usage", {}).get("total_tokens") if resp is not None else None
        elif hasattr(openai, "ChatCompletion") and hasattr(openai.ChatCompletion, "create"):
            resp = openai.ChatCompletion.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=500,
            )
            text = resp.choices[0].message.content.strip()
            try:
                tokens = resp.usage.total_tokens
            except Exception:
                tokens = getattr(resp, "usage", {}).get("total_tokens") if resp is not None else None
        else:
            # Fallback: try the legacy completions API
            resp = openai.Completion.create(
                model=settings.OPENAI_MODEL,
                prompt=prompt,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=500,
            )
            text = resp.choices[0].text.strip()
            try:
                tokens = resp.usage.total_tokens
            except Exception:
                tokens = getattr(resp, "usage", {}).get("total_tokens") if resp is not None else None
    except Exception as e:
        raise RuntimeError(
            "OpenAI request failed. Ensure OPENAI_API_KEY is set and the openai package is compatible. "
            f"Original error: {e}"
        )

    # Try to parse JSON from the response. We accept plain JSON or code fences.
    # Remove markdown fences if present.
    if text.startswith("```"):
        # remove triple backticks and possible "json"
        parts = text.split("\n", 1)
        if len(parts) > 1:
            text = parts[1]
        text = text.strip().strip("`\n ")

    try:
        data = json.loads(text)
    except Exception as e:
        raise RuntimeError(f"Failed to parse OpenAI response as JSON: {e}\nResponse:\n{text}")

    # Attach token usage if available
    if tokens is not None:
        try:
            data["tokens"] = int(tokens)
        except Exception:
            data["tokens"] = None

    return data
