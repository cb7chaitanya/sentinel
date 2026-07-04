"""Loads and renders the agent's prompt templates.

Templates live as plain text in `agent/prompts/*.txt`, deliberately kept
out of this module and out of `infra/llm_client.py`: editing the wording
Claude sees should never require touching the code that calls the API, or
vice versa. Read via a path relative to this file (not `importlib.resources`)
so it works the same whether this package is run from source or installed,
without depending on packaging metadata correctly bundling non-Python files.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from string import Template

from agent.domain.context import AgentContext
from agent.domain.copilot import CopilotQuestion
from agent.domain.evidence import RetrievedEvidence

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text()


def system_prompt() -> str:
    return _load("system.txt")


def render_analysis_prompt(context: AgentContext) -> str:
    template = Template(_load("analysis_request.txt"))
    return template.substitute(
        warehouse_id=context.warehouse_state.warehouse_id,
        generated_at=context.warehouse_state.generated_at.isoformat(),
        warehouse_state_json=context.warehouse_state.model_dump_json(indent=2),
        recent_events_json=json.dumps(
            [event.model_dump(mode="json") for event in context.recent_events], indent=2
        ),
        inventory_records_json=json.dumps(
            [record.model_dump(mode="json") for record in context.inventory_records], indent=2
        ),
        safety_rules_json=json.dumps(
            [rule.model_dump(mode="json") for rule in context.safety_rules], indent=2
        ),
    )


def copilot_system_prompt() -> str:
    return _load("copilot_system.txt")


def render_copilot_prompt(question: CopilotQuestion, evidence: RetrievedEvidence) -> str:
    template = Template(_load("copilot_question.txt"))
    return template.substitute(
        question=question.question,
        warehouse_id=question.warehouse_id,
        generated_at=datetime.now(UTC).isoformat(),
        entities_json=json.dumps(
            [entity.model_dump(mode="json") for entity in evidence.entities], indent=2
        ),
        events_json=json.dumps(
            [event.model_dump(mode="json") for event in evidence.events], indent=2
        ),
        alerts_json=json.dumps(
            [alert.model_dump(mode="json") for alert in evidence.alerts], indent=2
        ),
    )
