from src.agents.models import CaseDetail, CaseSummary, BaseToolInput
from typing import List
from src.config import settings

try:
    from src.agents.llm import call_openai_for_summary
except Exception:
    call_openai_for_summary = None
#try:
#    from src.agents.langchain_adapter import call_langchain_for_summary
#except Exception:
#    call_langchain_for_summary = None


def summarize_case(case: BaseToolInput | CaseDetail, prompt_template: str | None = None) -> CaseSummary:
    # Accept either the legacy CaseDetail or the new BaseToolInput
    desc = (getattr(case, 'description', '') or '').strip()
    context = getattr(case, 'context', None)

    # Prefer LangChain adapter if available
    #if settings.OPENAI_API_KEY and call_langchain_for_summary is not None:
    #    try:
    #        data = call_langchain_for_summary(desc, facts=case.facts or [])
    #        summary = str(data.get("summary", ""))
    #        suggested_solution = str(data.get("suggested_solution", ""))
    #        confidence = float(data.get("confidence", 0.0))
    #        tokens = data.get("tokens")
    #        return CaseSummary(summary=summary, suggested_solution=suggested_solution, confidence=confidence, tokens=tokens)
    #    except Exception as e:
    #        print(f"LangChain summarization failed, falling back: {e}")

    # If LangChain unavailable, try direct OpenAI adapter
    if settings.OPENAI_API_KEY and call_openai_for_summary is not None:
        try:
            facts = getattr(case, 'facts', []) or []
            data = call_openai_for_summary(desc, facts=facts, context=context, prompt_template=prompt_template)
            print(f"OpenAI response data: {data}")
            # Validate basic shape and coerce types
            summary = str(data.get("summary", ""))
            suggested_solution = str(data.get("suggested_solution", ""))
            confidence = float(data.get("confidence", 0.0))
            tokens = data.get("tokens")
            extra = data.get("extra") or {
                "revenue": data.get("revenue"),
                "employees": data.get("employees"),
                "parent_company": data.get("parent_company"),
                "sentiment": data.get("sentiment"),
            }
            return CaseSummary(summary=summary, suggested_solution=suggested_solution, confidence=confidence, tokens=tokens, extra=extra)
        except Exception as e:
            # fallback to heuristic summarizer on any LLM error
            print(f"OpenAI summarization failed, falling back: {e}")

    # Fallback heuristic summarization
    summary = desc if len(desc) <= 200 else desc[:197] + "..."
    solution = "Further investigation required. Recommend gathering missing evidence and consulting subject-matter expert."
    confidence = min(0.95, max(0.2, len(desc) / 2000))
    return CaseSummary(summary=summary, suggested_solution=solution, confidence=round(confidence, 2), tokens=None)
