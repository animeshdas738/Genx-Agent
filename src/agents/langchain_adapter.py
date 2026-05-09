from typing import Optional

from src.config import settings

try:
    from langchain.chat_models import ChatOpenAI
    from langchain.schema import HumanMessage
except Exception:
    ChatOpenAI = None


def call_langchain_for_summary(description: str, facts: Optional[list] = None) -> dict:
    if ChatOpenAI is None or not settings.OPENAI_API_KEY:
        raise RuntimeError("LangChain or OpenAI not configured")

    # Initialize ChatOpenAI with the API key and model settings
    client = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=settings.OPENAI_TEMPERATURE, openai_api_key=settings.OPENAI_API_KEY)

    prompt = "You are an assistant that converts a case description into a JSON object with keys: summary, suggested_solution, confidence (0..1)."
    content = prompt + "\n\nDescription:\n" + description
    if facts:
        content += "\n\nFacts:\n" + "\n".join(facts)

    resp = client.generate([[HumanMessage(content=content)]])
    text = resp.generations[0][0].text

    # Try to parse JSON out of text
    import json

    if text.startswith("```"):
        # strip code fences
        import re

        text = re.sub(r"^```(?:json)?\n", "", text)
        text = re.sub(r"\n```$", "", text)

    data = json.loads(text)

    # Attempt to extract token usage from LangChain LLM output if present
    tokens = None
    try:
        # LangChain may include token usage in llm_output or generation_info
        llm_output = getattr(resp, "llm_output", None) or resp.generations[0][0].generation_info or {}
        # common place: llm_output["token_usage"]["total_tokens"] or generation_info["token_usage"]
        tu = None
        if isinstance(llm_output, dict):
            tu = llm_output.get("token_usage") or llm_output.get("token_count")
        if tu and isinstance(tu, dict):
            tokens = tu.get("total_tokens") or tu.get("total") or tu.get("tokens")
        if tokens is None:
            # try generation_info
            gi = resp.generations[0][0].generation_info or {}
            if isinstance(gi, dict):
                tokens = gi.get("token_usage") or gi.get("tokens")
    except Exception:
        tokens = None

    if tokens is not None:
        try:
            data["tokens"] = int(tokens)
        except Exception:
            data["tokens"] = None

    return data
