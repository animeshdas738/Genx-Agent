from typing import Optional
import json

from src.config import settings

try:
    import openai
except Exception:
    openai = None


def call_openai_for_summary(description: str, facts: Optional[list] = None, context: Optional[str] = None, prompt_template: Optional[str] = None) -> dict:
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

    if prompt_template:
        # if the database provides a prompt template, interpolate values
        prompt = prompt_template.replace("{description}", description or "")
        prompt = prompt.replace("{context}", context or "")
        prompt = prompt.replace("{facts}", "\n".join(facts or []))
    else:
        prompt = (
            "You are an assistant that extracts business information from the provided account description and returns a JSON object. The JSON must include:\n"
            "- summary: a short (1-3 sentence) account overview\n"
            "- suggested_solution: concise recommendation or action items\n"
            "- confidence: a float between 0 and 1 indicating confidence in the extracted fields\n"
            "- revenue: estimated annual revenue (string or number, nullable)\n"
            "- employees: estimated employee count (string or number, nullable)\n"
            "- parent_company: parent company name if applicable (nullable)\n"
            "- sentiment: short sentiment summary or recent news summary (nullable)\n\n"
            f"Description:\n{description}\n\n"
        )

        if context:
            prompt += f"Context from similar cases or notes:\n{context}\n\n"

        if facts:
            prompt += "Facts:\n" + "\n".join(facts) + "\n\n"

        prompt += "Return only valid JSON. Be conservative when guessing numeric estimates. If unknown, set fields to null."

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


def call_openai_for_sentiment(text: str, context: Optional[str] = None) -> dict:
    """Call OpenAI to classify the sentiment of the provided text.

    Returns a dict with:
      - sentiment: "positive" | "negative" | "neutral"
      - score: float 0..1 (strength of sentiment)
      - confidence: float 0..1
      - reasoning: short explanation (nullable)
      - tokens: total tokens used (nullable)
    """
    if openai is None or not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI not configured")

    openai.api_key = settings.OPENAI_API_KEY

    prompt = (
        "You are a sentiment analysis assistant. Analyze the sentiment of the provided text "
        "and return a JSON object with:\n"
        "- sentiment: one of 'positive', 'negative', or 'neutral'\n"
        "- score: a float between 0 and 1 representing the strength of the sentiment "
        "(0 = very weak, 1 = very strong)\n"
        "- confidence: a float between 0 and 1 indicating your confidence in the classification\n"
        "- reasoning: a short (1-2 sentence) explanation of the classification\n\n"
        f"Text:\n{text}\n\n"
    )

    if context:
        prompt += f"Additional context:\n{context}\n\n"

    prompt += "Return only valid JSON."

    text_resp = None
    tokens = None
    try:
        if hasattr(openai, "chat") and hasattr(openai.chat, "completions"):
            resp = openai.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=300,
            )
            text_resp = resp.choices[0].message.content.strip()
            try:
                tokens = resp.usage.total_tokens
            except Exception:
                tokens = None
        elif hasattr(openai, "ChatCompletion") and hasattr(openai.ChatCompletion, "create"):
            resp = openai.ChatCompletion.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=300,
            )
            text_resp = resp.choices[0].message.content.strip()
            try:
                tokens = resp.usage.total_tokens
            except Exception:
                tokens = None
        else:
            resp = openai.Completion.create(
                model=settings.OPENAI_MODEL,
                prompt=prompt,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=300,
            )
            text_resp = resp.choices[0].text.strip()
            try:
                tokens = resp.usage.total_tokens
            except Exception:
                tokens = None
    except Exception as e:
        raise RuntimeError(f"OpenAI request failed: {e}")

    if text_resp.startswith("```"):
        parts = text_resp.split("\n", 1)
        if len(parts) > 1:
            text_resp = parts[1]
        text_resp = text_resp.strip().strip("`\n ")

    try:
        data = json.loads(text_resp)
    except Exception as e:
        raise RuntimeError(f"Failed to parse OpenAI response as JSON: {e}\nResponse:\n{text_resp}")

    if tokens is not None:
        try:
            data["tokens"] = int(tokens)
        except Exception:
            data["tokens"] = None

    return data


def call_openai_for_resolution(subject: str, description: str, context: Optional[str] = None) -> dict:
    """Call OpenAI to generate a case resolution using vector DB context when available.

    Returns a dict with:
      - resolution: suggested resolution string
      - confidence: float 0..1
      - tokens: total tokens used (nullable)
    """
    if openai is None or not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI not configured")

    openai.api_key = settings.OPENAI_API_KEY

    prompt = (
        "You are a support agent assistant. Given a support case subject and description, "
        "generate a clear and actionable resolution.\n\n"
        "Return a JSON object with:\n"
        "- resolution: if the resolution has multiple steps or solutions, separate each step with a "
        "newline character (\\n). Each step should be a complete, actionable instruction.\n"
        "- confidence: a float between 0 and 1 indicating how confident you are in the resolution\n\n"
        f"Subject: {subject}\n\n"
        f"Description: {description}\n\n"
    )

    if context:
        prompt += (
            "The following similar resolved cases from our knowledge base may be relevant:\n"
            f"{context}\n\n"
        )

    prompt += (
        "Return only valid JSON. Separate multiple steps or solutions in the resolution field with \\n. "
        "If you cannot determine a resolution, set confidence below 0.4."
    )

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
            text = resp.choices[0].message.content.strip()
            try:
                tokens = resp.usage.total_tokens
            except Exception:
                tokens = None
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
                tokens = None
        else:
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
                tokens = None
    except Exception as e:
        raise RuntimeError(f"OpenAI request failed: {e}")

    if text.startswith("```"):
        parts = text.split("\n", 1)
        if len(parts) > 1:
            text = parts[1]
        text = text.strip().strip("`\n ")

    try:
        data = json.loads(text)
    except Exception as e:
        raise RuntimeError(f"Failed to parse OpenAI response as JSON: {e}\nResponse:\n{text}")

    if tokens is not None:
        try:
            data["tokens"] = int(tokens)
        except Exception:
            data["tokens"] = None

    return data
