from __future__ import annotations

from dataclasses import dataclass

from app.schemas.review_graph import ReviewGraphMapping


@dataclass
class ResolverResult:
    matched_object_ids: set[str]
    unresolved_refs: set[str]


class ReviewGraphResolver:
    def __init__(self, mapping: ReviewGraphMapping):
        self._mapping = mapping

    def resolve_refs(
        self,
        changed_files: set[str],
        linked_tests: set[str],
        changed_symbols: set[str],
    ) -> ResolverResult:
        tokens = set(changed_files) | set(linked_tests) | set(changed_symbols)
        matched_object_ids: set[str] = set()
        matched_refs: set[str] = set()

        for obj in self._mapping.objects:
            for ref in obj.refs:
                if ref.value in tokens:
                    matched_object_ids.add(obj.id)
                    matched_refs.add(ref.value)

        unresolved_refs = tokens - matched_refs
        return ResolverResult(matched_object_ids=matched_object_ids, unresolved_refs=unresolved_refs)

    def expand_related(self, object_ids: set[str], relation_types: set[str]) -> set[str]:
        related_object_ids = set(object_ids)
        frontier = set(object_ids)

        while frontier:
            next_frontier: set[str] = set()
            for relation in self._mapping.relations:
                if relation.type not in relation_types:
                    continue
                if relation.from_ in frontier and relation.to not in related_object_ids:
                    next_frontier.add(relation.to)
                if relation.to in frontier and relation.from_ not in related_object_ids:
                    next_frontier.add(relation.from_)
            related_object_ids.update(next_frontier)
            frontier = next_frontier

        return related_object_ids
