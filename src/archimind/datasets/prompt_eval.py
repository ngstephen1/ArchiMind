"""Record live chat-interpreter answers once, then re-score them offline.

A recording keeps the model's raw structured extraction (or its typed failure).
Replay sends that extraction through the current application rules
(``reconcile_catalog_extraction``), so rule changes can be re-scored for free and
without new model calls. Imported only by the ``prompt-eval`` command.
"""

import json

from archimind.datasets.prompt_suite import PromptCase, score_case, summarize


def turns_for(case: PromptCase):
    from archimind.agents.catalog_requirements import CatalogChatTurn

    return (CatalogChatTurn(id=1, role="user", content=case.prompt),)


def record_case(case: PromptCase, interpret) -> dict:
    """Run ``interpret(turns)`` once and keep what replay needs."""
    result = interpret(turns_for(case))
    return {
        "case_id": case.case_id,
        "status": result.status,
        "error": None if result.error is None else result.error.code,
        "extraction": None
        if result.extraction is None
        else result.extraction.model_dump(mode="json"),
        "model": result.model,
    }


def replay(case: PromptCase, record: dict):
    from archimind.agents.catalog_conversation import reconcile_catalog_extraction
    from archimind.agents.catalog_requirements import (
        CatalogConversationExtraction,
        CatalogConversationResult,
    )
    from archimind.agents.requirements_schemas import RequirementsError

    if record.get("extraction") is not None:
        extraction = CatalogConversationExtraction.model_validate_json(
            json.dumps(record["extraction"])
        )
        return reconcile_catalog_extraction(
            extraction, turns_for(case), mode="api_response", model=record.get("model")
        )
    return CatalogConversationResult(
        status=record["status"],
        error=RequirementsError(
            code=record.get("error") or "missing_output", message="Recorded failure."
        ),
    )


def evaluate_recordings(cases, recordings: dict) -> dict:
    rows, missing = [], []
    for case in cases:
        record = recordings.get(case.case_id)
        if record is None:
            missing.append(case.case_id)
            continue
        rows.append(score_case(case, replay(case, record)))
    return {"summary": summarize(rows), "rows": rows, "unrecorded": missing}
