
from typing import Any, Dict, Optional
import asyncio

from src.agents.models import BaseToolInput, BaseToolOutput, CaseResolutionInput, CaseResolutionOutput, SentimentAnalysisInput, SentimentAnalysisOutput
from src.agents.service import summarize_case
from src.db import agents as db_agents
from src.vectordb import query_similar

try:
    from src.agents.llm import call_openai_for_resolution
except Exception:
    call_openai_for_resolution = None

try:
    from src.agents.llm import call_openai_for_sentiment
except Exception:
    call_openai_for_sentiment = None

try:
    # LangChain Tool class (v0.0x+)
    from langchain.tools import Tool as LangChainTool
except Exception:
    LangChainTool = None


class GenericAgentTool:
    """A small adapter base that normalizes inputs/outputs for agent tools.

    Subclasses should implement the `call` method which accepts a
    BaseToolInput (or subclass) and returns a BaseToolOutput (or subclass).
    This class also provides a `.run()` method kept for backward compatibility
    with existing code that expects a dict -> dict callable.
    """

    name: str = "generic_agent_tool"
    description: str = "Generic agent tool"

    def call(self, inp: BaseToolInput) -> BaseToolOutput:  # noqa: ARG002
        raise NotImplementedError()

    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibility wrapper: accept dicts (from controllers/tests) and
        return plain dicts. Internally uses Pydantic models for validation.
        """
        if isinstance(data, BaseToolInput):
            inp = data
        else:
            inp = BaseToolInput(**data)

        out = self.call(inp)
        # Convert Pydantic model to native dict for existing consumers
        return out.model_dump()

    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.run(data)


class SummarizeTool(GenericAgentTool):
    """Backward-compatible summarizer that uses the generic IO models.

    It preserves the `.run(dict)` API while internally validating inputs with
    `BaseToolInput` and producing a `BaseToolOutput`. The service layer still
    uses `CaseDetail`/`CaseSummary` but these are mapped to/from the generic
    IO models here to keep coupling low.
    """

    name = "case_summarizer"
    description = "Summarize a case description and suggest a solution with confidence score."

    def call(self, inp: BaseToolInput) -> BaseToolOutput:
        # Use BaseToolInput directly (service accepts it) and pass DB prompt template
        summary = summarize_case(inp, prompt_template=_PROMPT_TEMPLATE)

        # Map CaseSummary -> BaseToolOutput
        merged_extra: dict = {}
        # include similarity if present
        if getattr(summary, "similarity", None) is not None:
            merged_extra["similarity"] = getattr(summary, "similarity")
        # merge any extra returned by the service (revenue, employees, etc.)
        if getattr(summary, "extra", None):
            try:
                merged_extra.update(summary.extra)
            except Exception:
                # ignore if extra is not a mapping
                pass

        out = BaseToolOutput(
            summary=summary.summary,
            suggested_solution=summary.suggested_solution,
            confidence=summary.confidence,
            tokens=summary.tokens,
            extra=merged_extra or None,
        )
        return out



class AccountSummaryTool(GenericAgentTool):
    """Generate an account-level summary from a website URL or HTML snippet."""

    name = "account_summarizer"
    description = "Generate an account summary from a website URL or HTML/text input."

    def call(self, inp: BaseToolInput) -> BaseToolOutput:
        # Treat inp.description as the website URL or raw HTML/text
        # For now we reuse the same summarization pipeline — the LLM prompt
        # will be chosen from the DB if available, otherwise default.
        summary = summarize_case(inp, prompt_template=_PROMPT_TEMPLATE)
        merged_extra = {"source": "account"}
        if getattr(summary, "extra", None):
            try:
                merged_extra.update(summary.extra)
            except Exception:
                pass

        out = BaseToolOutput(
            summary=summary.summary,
            suggested_solution=summary.suggested_solution,
            confidence=summary.confidence,
            tokens=summary.tokens,
            extra=merged_extra or None,
        )
        return out


_UNRESOLVED_MSG = "AI agent is not able to resolve the issue, assign the case to support agent"


class CaseResolutionTool:
    """Look up case_vector table for a resolution. Returns stored solution or unresolved message."""

    name = "case_resolution"
    description = "Resolve a support case by matching subject and description against the case vector store."

    def resolve(self, inp: CaseResolutionInput) -> CaseResolutionOutput:
        query_text = f"{inp.subject}\n{inp.description}"

        # Step 1: query vector DB for similar resolved cases
        try:
            matches = query_similar(query_text, top_k=3)
        except Exception:
            matches = []

        # Step 2: build context and capture top similarity for the response
        context = None
        top_similarity = None
        if matches:
            lines = []
            for m in matches:
                title = m.get("title") or ""
                desc = m.get("description") or ""
                solution = m.get("solution") or ""
                lines.append(f"- Title: {title}\n  Description: {desc}\n  Resolution: {solution}")
            context = "\n".join(lines)
            try:
                top_similarity = float(matches[0].get("similarity")) if matches[0].get("similarity") is not None else None
            except Exception:
                top_similarity = None

        # Step 3: call OpenAI with context (if available) to generate resolution
        if call_openai_for_resolution is not None:
            try:
                data = call_openai_for_resolution(inp.subject, inp.description, context=context)
                resolution = str(data.get("resolution") or "").strip()
                confidence = data.get("confidence")
                tokens = data.get("tokens")
                try:
                    confidence = float(confidence) if confidence is not None else None
                except Exception:
                    confidence = None

                if resolution:
                    source = "vector_db" if context else "llm"
                    return CaseResolutionOutput(
                        resolution=resolution,
                        confidence=confidence,
                        source=source,
                        similarity=top_similarity,
                        tokens=tokens,
                    )
            except Exception as e:
                print(f"[CaseResolutionTool] OpenAI call failed: {e}")

        # Step 4: fallback — could not generate a resolution
        return CaseResolutionOutput(
            resolution=_UNRESOLVED_MSG,
            confidence=None,
            source="unresolved",
            similarity=top_similarity,
            tokens=None,
        )

    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(data, CaseResolutionInput):
            inp = data
        else:
            inp = CaseResolutionInput(**data)
        return self.resolve(inp).model_dump()

    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.run(data)


case_resolution_tool = CaseResolutionTool()


_UNCLASSIFIED_SENTIMENT = "neutral"


class SentimentAnalysisTool:
    """Classify the sentiment of text as positive, negative, or neutral."""

    name = "sentiment_analyzer"
    description = "Analyze the sentiment of the provided text and return a classification with confidence score."

    def analyze(self, inp: SentimentAnalysisInput) -> SentimentAnalysisOutput:
        if call_openai_for_sentiment is not None:
            try:
                data = call_openai_for_sentiment(inp.text, context=inp.context)
                sentiment = str(data.get("sentiment") or _UNCLASSIFIED_SENTIMENT).lower()
                if sentiment not in ("positive", "negative", "neutral"):
                    sentiment = _UNCLASSIFIED_SENTIMENT
                score = data.get("score")
                confidence = data.get("confidence")
                try:
                    score = float(score) if score is not None else 0.5
                    score = max(0.0, min(1.0, score))
                except Exception:
                    score = 0.5
                try:
                    confidence = float(confidence) if confidence is not None else 0.5
                    confidence = max(0.0, min(1.0, confidence))
                except Exception:
                    confidence = 0.5
                return SentimentAnalysisOutput(
                    sentiment=sentiment,
                    score=score,
                    confidence=confidence,
                    reasoning=data.get("reasoning"),
                    tokens=data.get("tokens"),
                )
            except Exception as e:
                print(f"[SentimentAnalysisTool] OpenAI call failed: {e}")

        # Fallback: keyword-based heuristic
        text_lower = inp.text.lower()
        positive_words = {"great", "good", "excellent", "happy", "love", "awesome", "fantastic", "wonderful", "best"}
        negative_words = {"bad", "terrible", "awful", "hate", "worst", "horrible", "poor", "disappointing", "broken"}
        pos_hits = sum(1 for w in positive_words if w in text_lower)
        neg_hits = sum(1 for w in negative_words if w in text_lower)
        if pos_hits > neg_hits:
            sentiment, score = "positive", min(0.5 + pos_hits * 0.1, 0.9)
        elif neg_hits > pos_hits:
            sentiment, score = "negative", min(0.5 + neg_hits * 0.1, 0.9)
        else:
            sentiment, score = "neutral", 0.5
        return SentimentAnalysisOutput(
            sentiment=sentiment,
            score=score,
            confidence=0.4,
            reasoning="Classified using keyword heuristic (OpenAI not available).",
            tokens=None,
        )

    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(data, SentimentAnalysisInput):
            inp = data
        else:
            inp = SentimentAnalysisInput(**data)
        return self.analyze(inp).model_dump()

    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.run(data)


sentiment_analysis_tool = SentimentAnalysisTool()

# account summarizer instance
account_summarizer = AccountSummaryTool()
if LangChainTool is not None and account_summarizer is not None:
    try:
        def _acc_fn(inp_text: str) -> Dict[str, Any]:
            return account_summarizer.run({"description": inp_text})

        try:
            _ = LangChainTool.from_function(func=_acc_fn, name=account_summarizer.name, description=account_summarizer.description)
        except Exception:
            _ = LangChainTool(func=_acc_fn, name=account_summarizer.name, description=account_summarizer.description)
    except Exception:
        pass


# Create a single shared instance and, if LangChain is present, expose a LangChain Tool
summarizer = SummarizeTool()

# Try to load a prompt template from DB for this tool. If DB isn't
# configured or fetch fails, fall back to the hard-coded behaviour.
_PROMPT_TEMPLATE: Optional[str] = None


def _load_prompt_from_db(tool_id: str) -> Optional[str]:
    """Sync helper to call the async fetcher during import time if possible.

    If an event loop is running this will schedule a task; otherwise it will
    run a short-lived loop to fetch the prompt. Errors are swallowed and
    None is returned on failure.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    coro = db_agents.fetch_prompt_for_tool(tool_id)
    try:
        if loop and loop.is_running():
            # schedule and wait briefly — best-effort
            fut = asyncio.run_coroutine_threadsafe(coro, loop)
            return fut.result(timeout=1)
        else:
            return asyncio.run(coro)
    except Exception:
        return None


# load prompt for the summarizer tool (tool_id = 'case_summarizer')
try:
    _PROMPT_TEMPLATE = _load_prompt_from_db('case_summarizer')
except Exception:
    _PROMPT_TEMPLATE = None


langchain_tool = None
if LangChainTool is not None:
    try:
        # LangChain Tool expects a function, name and description. Convert
        # incoming string to the generic input model so the underlying tool
        # receives the same validated input shape.
        def _lc_fn(inp_text: str) -> Dict[str, Any]:
            out = summarizer.run({"description": inp_text})
            return out

        # Use modern from_function where available
        try:
            langchain_tool = LangChainTool.from_function(
                func=_lc_fn,
                name=summarizer.name,
                description=summarizer.description,
            )
        except Exception:
            # Fallback construction for older LangChain versions
            langchain_tool = LangChainTool(func=_lc_fn, name=summarizer.name, description=summarizer.description)
    except Exception:
        langchain_tool = None

