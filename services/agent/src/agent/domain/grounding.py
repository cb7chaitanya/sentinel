"""Enforces 'never invent facts': every conclusion must cite something real.

Requiring citations in the schema only guarantees the model *attached*
some citations -- it can't guarantee they point at anything that was
actually in the `AgentContext` it was given. That's a semantic check, not
a structural one, so it can't live in a JSON schema at all: this module is
that second check, run after parsing, and it's where "never invent facts"
actually gets enforced, not the prompt.

Deliberately not split between schema and code: an earlier version of this
required `min_length=1` on `citations` in the schema and did the
real-id check separately here. That meant a model that produced a
correctly-shaped-but-hallucinated citation would fail differently (and at
a different layer) than one that produced zero citations, for what is
really the same underlying problem -- "this conclusion isn't grounded."
Both cases are handled identically here: the conclusion is dropped.
"""

from agent.domain.analysis import AgentAnalysis, Citation, CitationKind
from agent.domain.context import AgentContext


def _known_reference_ids(context: AgentContext) -> dict[CitationKind, set[str]]:
    """Every id the model could legitimately cite, grouped by kind."""
    return {
        CitationKind.EVENT: {str(event.id) for event in context.recent_events},
        CitationKind.ENTITY: {
            str(entity.entity_id) for entity in context.warehouse_state.entities
        },
        CitationKind.INVENTORY_RECORD: {record.sku for record in context.inventory_records},
        CitationKind.SAFETY_RULE: {rule.id for rule in context.safety_rules},
    }


def _is_grounded(citations: list[Citation], known: dict[CitationKind, set[str]]) -> bool:
    if not citations:
        return False
    return all(citation.reference_id in known[citation.kind] for citation in citations)


def filter_grounded(analysis: AgentAnalysis, context: AgentContext) -> AgentAnalysis:
    """Drop every conclusion in `analysis` that isn't fully grounded in `context`.

    A conclusion is grounded if it has at least one citation and every
    citation resolves to an id that was actually present in `context`.
    Anything else -- no citations, or a citation to an id the model made
    up -- is dropped rather than passed through: there's no reliable way
    to distinguish a genuine grounding mistake from a hallucination, so
    both are treated the same.
    """
    known = _known_reference_ids(context)

    return AgentAnalysis(
        warehouse_id=analysis.warehouse_id,
        generated_at=analysis.generated_at,
        insights=[i for i in analysis.insights if _is_grounded(i.citations, known)],
        potential_issues=[
            i for i in analysis.potential_issues if _is_grounded(i.citations, known)
        ],
        recommendations=[
            r for r in analysis.recommendations if _is_grounded(r.citations, known)
        ],
    )
