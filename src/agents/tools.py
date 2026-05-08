from typing import Any, Dict

from src.agents.models import CaseDetail, CaseSummary
from src.agents.service import summarize_case


class SummarizeTool:
    """A small tool abstraction that wraps the summarization service.

    This provides a stable callable interface that can be passed to agent frameworks
    or invoked directly by controllers.
    """

    name = "case_summarizer"
    description = "Summarize a case description and suggest a solution with confidence score."

    def run(self, case_input: Dict[str, Any]) -> Dict[str, Any]:
        # Accept either a dict (from a request) or a CaseDetail instance
        if isinstance(case_input, CaseDetail):
            case = case_input
        else:
            case = CaseDetail(**case_input)

        summary = summarize_case(case)
        return summary.model_dump()

    # Compatibility: some frameworks expect a __call__ or invoke method
    def __call__(self, case_input: Dict[str, Any]) -> Dict[str, Any]:
        return self.run(case_input)
