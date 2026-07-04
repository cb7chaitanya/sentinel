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

`is_grounded` is the one check both capabilities share: the reasoning
agent (`filter_grounded`, keeps whichever conclusions pass) and the
operations copilot (`ground_copilot_answer`, in `infra.copilot` swaps the
whole answer for a fixed decline if it doesn't) apply it to different
shapes of "known real ids," but the citation-matching rule itself -- at
least one citation, and every one of them real -- is identical.
"""

from agent.domain.analysis import AgentAnalysis
from agent.domain.citation import Citation, CitationKind
from agent.domain.context import AgentContext
from agent.domain.copilot import CopilotAnswerContent
from agent.domain.evidence import RetrievedEvidence


def is_grounded(citations: list[Citation], known: dict[CitationKind, set[str]]) -> bool:
    """Whether every citation has at least one entry and resolves to a real id.

    `known` need not have an entry for every `CitationKind` -- a kind with
    no known ids at all (e.g. the copilot has no inventory records) simply
    grounds nothing, rather than raising a `KeyError`.
    """
    if not citations:
        return False
    return all(citation.reference_id in known.get(citation.kind, set()) for citation in citations)


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
        insights=[i for i in analysis.insights if is_grounded(i.citations, known)],
        potential_issues=[
            i for i in analysis.potential_issues if is_grounded(i.citations, known)
        ],
        recommendations=[
            r for r in analysis.recommendations if is_grounded(r.citations, known)
        ],
    )


def _known_ids_from_evidence(evidence: RetrievedEvidence) -> dict[CitationKind, set[str]]:
    return {
        CitationKind.EVENT: {str(event.id) for event in evidence.events},
        CitationKind.ENTITY: {str(entity.entity_id) for entity in evidence.entities},
        CitationKind.ALERT: {str(alert.id) for alert in evidence.alerts},
    }


def ground_copilot_answer(
    content: CopilotAnswerContent, evidence: RetrievedEvidence
) -> CopilotAnswerContent | None:
    """`content` if every citation is real, `None` (fail closed) otherwise.

    Unlike `filter_grounded`, there is only one answer here, not a list of
    independent conclusions to prune -- so an ungrounded answer can't be
    partially salvaged. The caller (`infra.copilot.MemoryBackedCopilot`)
    treats `None` as "decline to answer" rather than returning free text
    no citation actually backs.
    """
    known = _known_ids_from_evidence(evidence)
    return content if is_grounded(content.citations, known) else None
